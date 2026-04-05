
# agent/severity_agent.py

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


def assess_severity(incident_text: str, violation_result_text: str) -> Dict[str, Any]:
    """
    Use an LLM to classify severity of the current incident.

    Returns:
    {
        "severity": "none|low|medium|high|critical",
        "harm_level": "none|limited|meaningful|major|extreme",
        "exposure_level": "none|limited|meaningful|broad",
        "intent_level": "accidental_or_unclear|reckless|intentional",
        "safety_impact": "none|low|meaningful|severe",
        "reason": "short explanation"
    }
    """
    incident_text = (incident_text or "").strip()
    violation_result_text = (violation_result_text or "").strip()

    if not incident_text:
        return {
            "severity": "none",
            "harm_level": "none",
            "exposure_level": "none",
            "intent_level": "accidental_or_unclear",
            "safety_impact": "none",
            "reason": "Incident text is empty."
        }

    prompt = f"""
You are a hospital compliance severity assessment agent.

Your task is to assess the severity of the CURRENT incident.

Inputs:
1. Incident text
2. Violation detection result

Incident text:
{incident_text}

Violation detection result:
{violation_result_text}

You must first assess these general factors:
- harm_level: none | limited | meaningful | major | extreme
- exposure_level: none | limited | meaningful | broad
- intent_level: accidental_or_unclear | reckless | intentional
- safety_impact: none | low | meaningful | severe

Then choose final severity using these principles:
- none: no confirmed violation
- low: limited harm, limited exposure, no meaningful safety impact
- medium: meaningful policy violation, but without major harm, severe safety impact, or extreme misconduct
- high: major harm, broad exposure, strong abuse of authority/access, or meaningful safety consequences
- critical: extreme misconduct, intentional severe harm, severe injury/death, criminal conduct, or immediate emergency/legal escalation

IMPORTANT RULES:
1) Base severity only on the current incident and current violation result.
2) Do NOT use past history here.
3) Do NOT invent facts that are not stated.
4) If no confirmed violation exists, severity must be "none".
5) Do NOT jump to "high" or "critical" unless the incident clearly supports major harm, severe consequences, intentional misconduct, or extreme escalation.
6) If the case is a clear violation but the described harm/exposure is meaningful rather than major, prefer "medium".
7) Return ONLY valid JSON.

Return exactly this format:
{{
  "harm_level": "none|limited|meaningful|major|extreme",
  "exposure_level": "none|limited|meaningful|broad",
  "intent_level": "accidental_or_unclear|reckless|intentional",
  "safety_impact": "none|low|meaningful|severe",
  "severity": "none|low|medium|high|critical",
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
            "severity": "none",
            "harm_level": "none",
            "exposure_level": "none",
            "intent_level": "accidental_or_unclear",
            "safety_impact": "none",
            "reason": "Could not parse model output."
        }


    severity = _clean_value(
        str(data.get("severity", "none")),
        {"none", "low", "medium", "high", "critical"},
        "none"
    )

    harm_level = _clean_value(
        str(data.get("harm_level", "none")),
        {"none", "limited", "meaningful", "major", "extreme"},
        "none"
    )

    exposure_level = _clean_value(
        str(data.get("exposure_level", "none")),
        {"none", "limited", "meaningful", "broad"},
        "none"
    )

    intent_level = _clean_value(
        str(data.get("intent_level", "accidental_or_unclear")),
        {"accidental_or_unclear", "reckless", "intentional"},
        "accidental_or_unclear"
    )

    safety_impact = _clean_value(
        str(data.get("safety_impact", "none")),
        {"none", "low", "meaningful", "severe"},
        "none"
    )

    reason = str(data.get("reason", "")).strip()
    if not reason:
        reason = "No reason provided."

    return {
        "severity": severity,
        "harm_level": harm_level,
        "exposure_level": exposure_level,
        "intent_level": intent_level,
        "safety_impact": safety_impact,
        "reason": reason,
    }