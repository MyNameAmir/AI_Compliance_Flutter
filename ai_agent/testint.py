# agent/policy_agent_file_search.py
# - Uses OpenAI vector stores search
# - No manual embeddings
# - No keyword bias
# - Clean chunk display
# - Multi-violation structured evaluation
# - Cached vector store by SHA256
#   - forces "one unique quote per violation"
#   - forces each quote to be a real rule sentence (not definitions/examples/background)
#   - forces using incident facts (short copied phrases) so it can’t drift
#   - forbids inventing duties (e.g., notification) unless explicitly stated
#   - prevents duplicates / near-duplicates
#   - allows “Not enough policy evidence” for parts that aren’t proven

import os
import json
import hashlib
import re
import math
from typing import List, Tuple, Dict

import nltk
from dotenv import load_dotenv
from openai import OpenAI
from PyPDF2 import PdfReader


MAX_QUERY_CHARS = 4096

# --------------------------------------------------
# Setup
# --------------------------------------------------

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

MODEL = "gpt-4o"

CACHE_DIR = "cache"
CACHE_FILE = os.path.join(CACHE_DIR, "vector_store_cache.json")

# --------------------------------------------------
# Utilities
# --------------------------------------------------


def ensure_nltk_punkt():
    """
    Ensure all required NLTK sentence tokenizer resources are installed.
    Required for nltk>=3.8 which separates punkt and punkt_tab.
    """
    resources = [
        "tokenizers/punkt",
        "tokenizers/punkt_tab/english",
    ]

    for resource in resources:
        try:
            nltk.data.find(resource)
        except LookupError:
            if "punkt_tab" in resource:
                nltk.download("punkt_tab", quiet=True)
            else:
                nltk.download("punkt", quiet=True)


def normalize_text(text: str) -> str:
    # Fix Windows line breaks and PDF artifacts
    text = text.replace("\r", " ")
    text = text.replace("\n", " ")
    text = text.replace("\xa0", " ")
    text = re.sub(r"\(cid:\d+\)", " ", text)
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip()


def read_pdf_text(path: str) -> str:
    parts = []
    with open(path, "rb") as f:
        reader = PdfReader(f)
        for page in reader.pages:
            t = page.extract_text() or ""
            if t.strip():
                parts.append(t)
    return "\n".join(parts)


def sentence_chunks_adaptive(
    text: str,
    target_queries: int = 8,
    min_sentences: int = 4,
    max_sentences_cap: int = 14,
    overlap_ratio: float = 0.25,  # 25% overlap (in sentences)
    max_query_chars: int = MAX_QUERY_CHARS,
) -> List[str]:
    """
    Stable adaptive sentence chunking (no skipped sentences):

    1) Split incident into sentences.
    2) Choose chunk size (max_sentences) to target ~ target_queries chunks.
    3) Use overlap (1–4 sentences) for continuity between chunks.
    4) Enforce max_query_chars WITHOUT skipping sentences:
       - If a chunk is too long, shrink it by dropping end sentences.
       - Then advance by the number of sentences actually used (minus overlap).
    """

    if not text:
        return []

    ensure_nltk_punkt()
    text = normalize_text(text)

    from nltk.tokenize import sent_tokenize

    sents = [s.strip() for s in sent_tokenize(text) if s.strip()]
    if not sents:
        return [text[:max_query_chars].strip()] if text.strip() else []

    n = len(sents)

    # -----------------------------
    # Step 1: Choose chunk size to get ~target_queries chunks
    # -----------------------------
    # Aim for step_target sentences per chunk "advance"
    step_target = math.ceil(n / target_queries)

    # Convert step_target into a chunk size given overlap_ratio:
    # step ≈ (1 - overlap_ratio) * max_sentences
    max_sentences = int(round(step_target / (1 - overlap_ratio)))

    # Clamp to your intended design range
    max_sentences = max(min_sentences, min(max_sentences, max_sentences_cap))

    # -----------------------------
    # Step 2: Choose overlap in sentences (bounded modestly)
    # -----------------------------
    overlap = int(round(max_sentences * overlap_ratio))
    overlap = max(1, min(overlap, 4))

    chunks: List[str] = []
    i = 0

    # -----------------------------
    # Step 3: Sliding window with safe char enforcement
    # -----------------------------
    while i < n:
        # Take a window of sentences up to max_sentences
        window = sents[i : i + max_sentences]
        used = len(window)

        # Build chunk text
        chunk = " ".join(window).strip()

        # If chunk is too long, shrink by dropping sentences from the end.
        # IMPORTANT: we track 'used' so we can advance safely without skipping.
        if len(chunk) > max_query_chars:
            while used > 1:
                used -= 1
                chunk = " ".join(window[:used]).strip()
                if len(chunk) <= max_query_chars:
                    break

            # Last-resort: hard truncate characters.
            # We keep 'used' as whatever it ended up being.
            if len(chunk) > max_query_chars:
                chunk = chunk[:max_query_chars].strip()

        if chunk:
            chunks.append(chunk)

        # -----------------------------
        # Step 4: Advance WITHOUT skipping sentences
        # -----------------------------
        # We want overlap, but overlap cannot be >= used (or we'd stall).
        overlap_used = min(overlap, used - 1) if used > 1 else 0
        step_used = max(1, used - overlap_used)

        i += step_used

    return chunks


def ensure_cache_dir():
    os.makedirs(CACHE_DIR, exist_ok=True)


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def load_cache():
    if not os.path.exists(CACHE_FILE):
        return {}
    with open(CACHE_FILE, "r") as f:
        return json.load(f)


def save_cache(data):
    ensure_cache_dir()
    with open(CACHE_FILE, "w") as f:
        json.dump(data, f, indent=2)


# --------------------------------------------------
# Vector Store
# --------------------------------------------------


def get_or_create_vector_store(policy_pdf_path: str) -> str:
    file_hash = sha256_file(policy_pdf_path)
    cache = load_cache()

    if file_hash in cache:
        cached_value = cache[file_hash]
        # (Kept as requested) supports older cache formats where value was a dict
        if isinstance(cached_value, dict):
            return cached_value.get("vector_store_id")
        return cached_value

    vs = client.vector_stores.create(
        name=f"policy-{file_hash[:10]}"
    )

    with open(policy_pdf_path, "rb") as f:
        client.vector_stores.files.upload_and_poll(
            vector_store_id=vs.id,
            file=f,
        )

    cache[file_hash] = vs.id
    save_cache(cache)

    return vs.id


# --------------------------------------------------
# Retrieval (Pure semantic, no keywords)
# --------------------------------------------------


def retrieve_top_chunks(
    vector_store_id: str,
    incident_text: str,
    top_k: int = 8,
    target_queries: int = 8,
    per_query_k: int = 6,
) -> List[Tuple[float, str]]:
    # 1) Make multiple sentence-based queries (adaptive, bounded)
    queries = sentence_chunks_adaptive(
        incident_text,
        target_queries=target_queries,
        max_query_chars=MAX_QUERY_CHARS,
    )

    print(f"[retrieve_top_chunks] Generated {len(queries)} query chunks from incident.")
    if not queries:
        return []

    # 2) Run vector search per query and merge results
    best = {}  # normalized_text -> (best_score, original_text)

    for q in queries:
        q = q[:MAX_QUERY_CHARS].strip()
        if not q:
            continue

        results = client.vector_stores.search(
            vector_store_id=vector_store_id,
            query=q,
            max_num_results=per_query_k,
        )

        for item in results.data:
            if not item.content:
                continue

            score = float(item.score)
            text = normalize_text(item.content[0].text)

            # normalize for dedupe key (simplified: reuse normalized text)
            key = text.lower()

            prev = best.get(key)
            if prev is None or score > prev[0]:
                best[key] = (score, text)

    merged = list(best.values())
    merged.sort(key=lambda x: x[0], reverse=True)

    # 4) Return top_k overall
    return merged[:top_k]


# --------------------------------------------------
# Evaluation (Prompt ONLY improved)
# --------------------------------------------------


def evaluate_incident(
    top_chunks: List[Tuple[float, str]],
    incident_text: str
) -> str:
    """
    Evaluator with chunk-aware evidence citations.
    - Adds chunk number(s) for each Evidence / Additional evidence sentence.
    - Still: pure semantic (no keyword heuristics), minimal parent grouping, full action coverage.
    """

    if not top_chunks:
        return "Decision: Not enough policy evidence\nReason: No policy excerpts retrieved."

    policy_text = "\n\n".join(
        f"[Chunk {i+1}]\n{chunk}"
        for i, (_, chunk) in enumerate(top_chunks)
    )

    prompt = f"""
You are evaluating an incident against policy text.

Incident:
{incident_text}

Policy Excerpts (ONLY evidence source):
{policy_text}

CORE CONSTRAINTS (do not violate):
1) Use ONLY the Policy Excerpts above. No outside knowledge. No assumptions.

2) FIRST extract ALL distinct incident actions from the Incident text.
   An incident action is any separate act involving access, use, disclosure,
   copying, transmission, storage, or notification involving personal health information.

3) You MUST account for EVERY incident action extracted in step (2).
   Each action must be either:
   (a) included as a Child under a Violation, OR
   (b) listed under a section titled "Unmapped incident actions" with reason:
       "Not enough policy evidence."

4) You are NOT allowed to omit any incident action.

5) List EVERY DISTINCT violation separately (do NOT merge unrelated violations).

6) Each violation must include exactly ONE quoted policy sentence as Evidence.

7) The Evidence sentence must be copied EXACTLY from the excerpts (verbatim).

8) Do NOT reuse the same Evidence sentence for multiple violations unless it genuinely applies.

9) Evidence must be a RULE sentence (requirement, prohibition, or safeguard obligation).
   Do NOT use definitions, examples, explanations, or headings.

10) Your "Why" must reference concrete incident facts by copying 3–12 words from the incident.

11) If policy evidence is broad (e.g., safeguard requirement), you MUST still include the child action under that violation rather than omitting it.

MANDATORY:
- For EACH evidence sentence you cite, you MUST also cite the chunk number it came from.
- If the exact sentence appears in multiple chunks, pick the SINGLE best chunk number and cite only that.

OUTPUT FORMAT (exact):

Decision: <Violation | No violation | Not enough policy evidence>

If Violation:
A) <Parent short title (max 8 words)>
- Evidence:
  - [Chunk <#>] "<one exact policy sentence>"
- Additional evidence: (optional; include ONLY if needed; otherwise omit)
  - [Chunk <#>] "<one exact policy sentence>"
  - [Chunk <#>] "<one exact policy sentence>"
- Children:
  - A1) Incident fact: "<copy 3–12 words verbatim from incident>"
       Why: <1 sentence linking that fact to Evidence or Additional evidence>
  - A2) ...

B) <Next parent (ONLY if truly distinct from A)>
- Evidence:
  - [Chunk <#>] "<one exact policy sentence>"
- Children:
  - B1) ...

If No violation:
- Why: <1–2 sentences>
- Evidence:
  - [Chunk <#>] "<one exact RULE sentence that explicitly permits it>"
- Incident fact:
  - "<copy 3–12 words verbatim from incident>"

If Not enough policy evidence:
- Reason: <1–2 sentences explaining what is missing from excerpts>

SELF-CHECK:
- Chunk citation: every quoted evidence line has exactly one [Chunk #].
- Coverage: every distinct incident action appears as a child.
- Redundancy: merge duplicate parents.
""".strip()

    response = client.responses.create(
        model=MODEL,
        input=prompt,
        temperature=0,
    )

    return response.output_text.strip()


# --------------------------------------------------
# Post-processing
# --------------------------------------------------


def polish_and_group_violations(final_eval_text: str) -> str:
    """
    Post-processor agent (chunk-aware):
    - Groups duplicates under minimal parents
    - NEVER drops or edits chunk citations like [Chunk 3]
    - Evidence lines must remain verbatim INCLUDING chunk tags
    """

    prompt = f"""
You are a *polishing / structuring agent*.

You will be given an evaluation text that includes Evidence lines formatted like:
  - [Chunk <#>] "..."

CRITICAL IMMUTABLE RULE:
- The substring [Chunk <#>] is REQUIRED metadata and MUST be preserved EXACTLY.
- You must copy Evidence lines verbatim INCLUDING the [Chunk <#>] prefix and the quoted sentence.
- Do not remove it. Do not move it outside the Evidence bullet. Do not renumber it.

ABSOLUTE REQUIREMENTS:
1) DO NOT remove any incidents. Ever.
2) Minimize the number of parent groups by merging semantically equivalent parents.
3) Duplicates MUST be grouped:
   - If Evidence sentence meaning is the same, merge.
4) When merging parents:
   - Choose ONE best parent title (≤ 8 words).
   - Choose ONE primary Evidence line EXACTLY as written, including its [Chunk #].
   - Combine all children under that parent and renumber A1, A2, ...
   - If the other parent has a truly distinct rule, include it under:
     - Additional evidence:
       - [Chunk #] "..."
     again copied verbatim INCLUDING chunk tags.
5) Do NOT invent new evidence or new chunk numbers.
6) Do NOT rewrite quoted policy sentences.
7) Keep each child’s Incident fact verbatim.
8) Keep Why to 1 sentence (may shorten but not change meaning).

OUTPUT FORMAT (exact):

Decision: <Violation | No violation | Not enough policy evidence>

If Violation:
A) <Parent short title (max 8 words)>
- Evidence:
  - [Chunk <#>] "<one exact policy sentence>"
- Additional evidence: (optional; only if truly distinct)
  - [Chunk <#>] "<one exact policy sentence>"
- Children:
  - A1) Incident fact: "<...>"
       Why: <...>
  - A2) ...

B) ... (only if truly distinct)

If No violation:
- Why: <1–2 sentences>
- Evidence:
  - [Chunk <#>] "<one exact sentence that permits it>"
- Incident fact:
  - "<copy 3–12 words from incident>"

If Not enough policy evidence:
- Reason: <1–2 sentences>

FINAL MERGE CHECK:
- If any two parents can be merged without losing meaning, merge them.

HERE IS THE TEXT TO POLISH:
{final_eval_text}
""".strip()

    response = client.responses.create(
        model=MODEL,
        input=prompt,
        temperature=0,
    )

    return response.output_text.strip()


# --------------------------------------------------
# Main Runner
# --------------------------------------------------


def run_analysis(policy_pdf: str, incident_pdf: str):

    incident_raw = read_pdf_text(incident_pdf)
    incident_text = normalize_text(incident_raw)

    # Remove template boilerplate if exists
    incident_text = re.sub(
        r"Purpose of Evaluation:.*",
        "",
        incident_text,
        flags=re.IGNORECASE
    ).strip()

    print("\n" + "=" * 90)
    print("INCIDENT")
    print("=" * 90)
    print(incident_text)

    vs_id = get_or_create_vector_store(policy_pdf)
    print(f"\nUsing vector store: {vs_id}")

    top_chunks = retrieve_top_chunks(vs_id, incident_text, top_k=8)

    print("\n" + "=" * 90)
    print("TOP MATCHED POLICY CHUNKS")
    print("=" * 90)

    for i, (score, text) in enumerate(top_chunks, 1):
        print(f"\nRank {i} | Score: {round(score, 4)}")
        print("-" * 90)
        print(text)

    result = evaluate_incident(top_chunks, incident_text)
    result = polish_and_group_violations(result)

    print("\n" + "=" * 90)
    print("FINAL INCIDENT EVALUATION")
    print("=" * 90)
    print(result)
    print("=" * 90)


# test:
# from embedding_store import run_analysis
# POLICY_PDF = "files/policy3.pdf"
# INCIDENT_PDF = "files/incident13.pdf"
# run_analysis(POLICY_PDF, INCIDENT_PDF)