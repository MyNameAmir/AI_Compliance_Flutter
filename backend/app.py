"""
FastAPI backend that wraps the ai_agent pipeline.
Runs the full 10-step analysis without modifying any agent code.
"""

import os
import re
import sys
import uuid

from fastapi import FastAPI, UploadFile
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# ── Add ai_agent to the Python path so we can import its modules ──
AI_AGENT_DIR = os.path.join(os.path.dirname(__file__), "..", "ai_agent")
sys.path.insert(0, os.path.abspath(AI_AGENT_DIR))

from testint import (                       # noqa: E402
    read_pdf_text,
    normalize_text,
    get_or_create_vector_store,
    retrieve_top_chunks,
    evaluate_incident,
)
from person_agent import extract_person_id   # noqa: E402
from severity_agent import assess_severity   # noqa: E402
from sanction_agent import (                 # noqa: E402
    recommend_sanction,
    build_user_friendly_sanction_text,
)
from violation_store import (                # noqa: E402
    initialize_database,
    count_violations_by_person,
    insert_case_result,
    get_all_violations,
)

# ── FastAPI app ──────────────────────────────────────────────────────
app = FastAPI(title="Hospital Policy Compliance API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Ensure the MySQL database itself exists before the agent's initialize_database()
# creates its table.  Uses the same credentials from violation_store.
from violation_store import MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASS, MYSQL_DB  # noqa: E402
from sqlalchemy import create_engine as _ce, text as _txt  # noqa: E402
try:
    _tmp = _ce(
        f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASS}@{MYSQL_HOST}:{MYSQL_PORT}/",
        isolation_level="AUTOCOMMIT",
    )
    with _tmp.connect() as _conn:
        _conn.execute(_txt(f"CREATE DATABASE IF NOT EXISTS `{MYSQL_DB}`"))
    _tmp.dispose()
except Exception as _e:
    print(f"Warning: could not ensure database exists: {_e}")

# Ensure DB table exists on startup
initialize_database()


# ── Helpers ──────────────────────────────────────────────────────────
def _save_upload(upload_file: UploadFile) -> str:
    safe = f"{uuid.uuid4().hex}_{upload_file.filename}".replace(" ", "_")
    path = os.path.join(UPLOAD_DIR, safe)
    with open(path, "wb") as f:
        f.write(upload_file.file.read())
    return path


def _extract_decision_label(violation_result_text: str) -> str:
    text = (violation_result_text or "").strip()
    m = re.search(
        r"Decision:\s*(Violation|No violation|Not enough policy evidence)",
        text,
        flags=re.IGNORECASE,
    )
    if m:
        label = m.group(1).strip().lower()
        return "Violation" if label == "violation" else "No Violation"
    m2 = re.search(r"Violations Found:\s*(Yes|No)", text, flags=re.IGNORECASE)
    if m2:
        return "Violation" if m2.group(1).lower() == "yes" else "No Violation"
    return "No Violation"


# ── Endpoints ────────────────────────────────────────────────────────
@app.post("/analyze")
async def analyze(policy: UploadFile, incident: UploadFile):
    """Run the full 10-step agent pipeline on uploaded PDFs."""
    try:
        policy_path = _save_upload(policy)
        incident_path = _save_upload(incident)

        # Step 1 — Read & normalise incident
        incident_text = normalize_text(read_pdf_text(incident_path))

        # Step 2 — Person extraction
        person_result = extract_person_id(incident_text)
        person_id = person_result.get("person_id", "unknown")
        person_role = person_result.get("person_role", "unknown")

        # Step 3 — Vector store for the policy
        vs_id = get_or_create_vector_store(policy_path)

        # Step 4 — Retrieve top policy chunks
        top_chunks = retrieve_top_chunks(vs_id, incident_text, top_k=10)

        # Step 5 — Violation detection
        violation_result = evaluate_incident(top_chunks, incident_text)
        decision_label = _extract_decision_label(violation_result)

        # Step 6 — Severity assessment
        severity_result = assess_severity(incident_text, violation_result)

        # Step 7 — Violation history
        previous_count = count_violations_by_person(person_id)

        # Step 8 — Sanction recommendation
        sanction_result = recommend_sanction(
            incident_text, violation_result, severity_result, previous_count
        )

        # Step 9 — Persist to DB
        insert_case_result(
            person_id=person_id,
            person_role=person_role,
            incident_file=os.path.basename(incident_path),
            decision=decision_label,
            violation_result_text=violation_result,
            severity=severity_result.get("severity"),
            severity_reason=severity_result.get("reason"),
            sanction_level=sanction_result.get("sanction_level"),
            recommended_action=sanction_result.get("recommended_action"),
            sanction_reason=sanction_result.get("reason"),
        )

        # Step 10 — Build user-friendly text
        final_text = build_user_friendly_sanction_text(
            person_id=person_id,
            decision=decision_label,
            sanction_result=sanction_result,
        )

        return JSONResponse(content={
            "decision": decision_label,
            "person_id": person_id,
            "person_role": person_role,
            "report": violation_result,
            "severity": severity_result,
            "sanction": sanction_result,
            "previous_violations": previous_count,
            "final_text": final_text,
            "top_chunks": [
                {"score": round(float(s), 4), "chunk": c}
                for s, c in top_chunks[:10]
            ],
        })

    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.get("/violations")
async def list_violations():
    """Return all stored violation records."""
    try:
        rows = get_all_violations()
        for row in rows:
            for k, v in row.items():
                if hasattr(v, "isoformat"):
                    row[k] = v.isoformat()
        return JSONResponse(content=rows)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
