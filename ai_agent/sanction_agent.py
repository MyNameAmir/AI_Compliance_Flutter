# agent/sanction_agent.py

from typing import Dict, Any
from openai import OpenAI
from dotenv import load_dotenv
import os
import json
import re

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

LLM_MODEL = "gpt-4o-mini"


def _extract_json(text: str) -> Dict[str, Any] | None:
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        return None

    try:
        return json.loads(match.group(0))
    except Exception:
        return None


def _clean_value(value: str, allowed: set[str], default: str) -> str:
    value = (value or "").strip().lower()
    if value not in allowed:
        return default
    return value


def recommend_sanction(
    incident_text: str,
    violation_result_text: str,
    severity_result: Dict[str, Any],
    previous_violation_count: int,
) -> Dict[str, Any]:
    """
    LLM-based sanction recommendation using:
    - current incident
    - violation result
    - structured severity factors
    - previous violation count
    """
    incident_text = (incident_text or "").strip()
    violation_result_text = (violation_result_text or "").strip()

    if not incident_text:
        return {
            "sanction_level": "none",
            "recommended_action": "No action recommended.",
            "reason": "Incident text is empty."
        }

    severity = str(severity_result.get("severity", "none")).strip().lower()
    harm_level = str(severity_result.get("harm_level", "none")).strip().lower()
    exposure_level = str(severity_result.get("exposure_level", "none")).strip().lower()
    intent_level = str(severity_result.get("intent_level", "accidental_or_unclear")).strip().lower()
    safety_impact = str(severity_result.get("safety_impact", "none")).strip().lower()
    severity_reason = str(severity_result.get("reason", "")).strip()

    prompt = f"""
You are a hospital compliance sanction recommendation agent.

Your task is to recommend a disciplinary response for the CURRENT incident.

Inputs:

Incident text:
{incident_text}

Violation detection result:
{violation_result_text}

Severity assessment:
- severity: {severity}
- harm_level: {harm_level}
- exposure_level: {exposure_level}
- intent_level: {intent_level}
- safety_impact: {safety_impact}
- severity_reason: {severity_reason}

Previous confirmed violations for this same person:
{previous_violation_count}

CRITICAL RULES:
1) Use only the provided inputs.
2) Do NOT invent legal frameworks, laws, or policy names that are not explicitly mentioned.
3) Do NOT mention HIPAA, PHIPA, or any other law unless it is explicitly in the inputs.
4) Keep the recommended action simple, realistic, and easy to understand.
5) The recommendation should become stronger when the severity is higher or the previous count is higher.
6) If there is no confirmed violation, the sanction level must be "none".

Sanction levels:
- none
- low
- medium
- high
- critical

Examples of clean recommended actions:
- No action recommended
- Verbal warning
- Written warning and mandatory retraining
- Temporary suspension and mandatory retraining
- Immediate suspension and executive review

Return ONLY valid JSON in exactly this format:
{{
  "sanction_level": "none|low|medium|high|critical",
  "recommended_action": "short clean action",
  "reason": "short explanation"
}}
""".strip()

    response = client.responses.create(
        model=LLM_MODEL,
        temperature=0,
        input=prompt,
    )

    raw = (response.output_text or "").strip()
    data = _extract_json(raw)

    if not data:
        return {
            "sanction_level": "none",
            "recommended_action": "Manual review required.",
            "reason": "Could not parse model output."
        }

    sanction_level = _clean_value(
        str(data.get("sanction_level", "none")),
        {"none", "low", "medium", "high", "critical"},
        "none"
    )

    recommended_action = str(data.get("recommended_action", "")).strip()
    if not recommended_action:
        recommended_action = "Manual review required."
    reason = str(data.get("reason", "")).strip()
    if not reason:
        reason = "No reason provided."

    return {
        "sanction_level": sanction_level,
        "recommended_action": recommended_action,
        "reason": reason,
    }


def build_user_friendly_sanction_text(
    person_id: str,
    decision: str,
    sanction_result: Dict[str, Any]
) -> str:
    """
    Build a simple, clean final message for the user.
    Internal labels like medium/high stay in the DB, not in the final text.
    """
    decision = (decision or "").strip().lower()

    if decision != "violation":
        return (
            f"Final result for {person_id}: no confirmed policy violation was found. "
            f"No disciplinary action is recommended."
        )

    recommended_action = sanction_result.get("recommended_action", "Manual review required.")
    reason = sanction_result.get("reason", "No reason provided.")

    return (
        f"Final result for {person_id}: a policy violation was confirmed. "
        f"Recommended action: {recommended_action}. "
        f"Reason: {reason}"
    )