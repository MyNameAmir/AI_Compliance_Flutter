# agent/person_agent.py

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


def extract_person_id(incident_text: str) -> Dict[str, Any]:
    """
    Extract the main person involved in the incident.

    Returns:
    {
        "person_id": "...",
        "person_role": "...",
        "reason": "..."
    }

    person_id should be a stable identifier if possible.
    If no clear person is found, return "unknown".
    """
    incident_text = (incident_text or "").strip()

    if not incident_text:
        return {
            "person_id": "unknown",
            "person_role": "unknown",
            "reason": "Incident text is empty."
        }

    prompt = f"""
You are a hospital incident person extraction agent.

Your task is to identify the MAIN staff member or person whose conduct is being evaluated in the incident.

Incident text:
{incident_text}

Instructions:
1) Extract the primary person involved in the incident.
2) If a full name is present, use it as person_id.
3) If only a partial role/name is present (for example "Nurse C" or "Dr. A"), use that as person_id.
4) If no clear person is identifiable, return "unknown".
5) Also return the role if it is clearly stated (for example nurse, doctor, resident, employee, staff member).
6) Return ONLY valid JSON.

Return exactly this format:
{{
  "person_id": "string",
  "person_role": "string",
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
            "person_id": "unknown",
            "person_role": "unknown",
            "reason": "Could not parse model output."
        }

    person_id = str(data.get("person_id", "unknown")).strip()
    person_role = str(data.get("person_role", "unknown")).strip().lower()
    reason = str(data.get("reason", "")).strip()

    if not person_id:
        person_id = "unknown"
    if not person_role:
        person_role = "unknown"
    if not reason:
        reason = "No reason provided."

    return {
        "person_id": person_id,
        "person_role": person_role,
        "reason": reason,
    }