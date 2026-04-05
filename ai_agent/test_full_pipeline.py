# test_full_pipeline.py

import os
import re

from testint import (
    read_pdf_text,
    normalize_text,
    get_or_create_vector_store,
    retrieve_top_chunks,
    evaluate_incident,
)

from person_agent import extract_person_id
from severity_agent import assess_severity
from sanction_agent import (
    recommend_sanction,
    build_user_friendly_sanction_text,
)
from violation_store import (
    initialize_database,
    count_violations_by_person,
    insert_case_result,
)


POLICY_PDF = "files/policy2.pdf"
INCIDENT_PDF = "files/incident6.pdf"


def extract_decision_label(violation_result_text: str) -> str:
    text = (violation_result_text or "").strip()

    match = re.search(
        r"Decision:\s*(Violation|No violation|Not enough policy evidence)",
        text,
        flags=re.IGNORECASE
    )
    if match:
        label = match.group(1).strip().lower()
        if label == "violation":
            return "Violation"
        return "No Violation"

    match2 = re.search(r"Violations Found:\s*(Yes|No)", text, flags=re.IGNORECASE)
    if match2:
        return "Violation" if match2.group(1).lower() == "yes" else "No Violation"

    return "No Violation"


# --------------------------------------------------
# Step 0 — Ensure DB exists
# --------------------------------------------------
initialize_database()


# --------------------------------------------------
# Step 1 — Read incident
# --------------------------------------------------
incident_raw = read_pdf_text(INCIDENT_PDF)
incident_text = normalize_text(incident_raw)

print("\n" + "=" * 90)
print("STEP 1 — INCIDENT TEXT")
print("=" * 90)
print(incident_text)


# --------------------------------------------------
# Step 2 — Extract person
# --------------------------------------------------
person_result = extract_person_id(incident_text)
person_id = person_result.get("person_id", "unknown")
person_role = person_result.get("person_role", "unknown")

print("\n" + "=" * 90)
print("STEP 2 — PERSON EXTRACTION")
print("=" * 90)
print(person_result)


# --------------------------------------------------
# Step 3 — Vector store
# --------------------------------------------------
vs_id = get_or_create_vector_store(POLICY_PDF)

print("\n" + "=" * 90)
print("STEP 3 — VECTOR STORE")
print("=" * 90)
print(vs_id)


# --------------------------------------------------
# Step 4 — Retrieve policy chunks
# --------------------------------------------------
top_chunks = retrieve_top_chunks(
    vs_id,
    incident_text,
    top_k=8
)

print("\n" + "=" * 90)
print("STEP 4 — TOP POLICY CHUNKS")
print("=" * 90)

for i, (score, text) in enumerate(top_chunks, 1):
    print(f"\nRank {i} | Score: {round(score, 4)}")
    print("-" * 80)
    print(text)


# --------------------------------------------------
# Step 5 — Violation detection
# --------------------------------------------------
violation_result = evaluate_incident(
    top_chunks,
    incident_text
)

print("\n" + "=" * 90)
print("STEP 5 — VIOLATION RESULT")
print("=" * 90)
print(violation_result)

decision_label = extract_decision_label(violation_result)

print("\n" + "=" * 90)
print("STEP 5.1 — DECISION LABEL")
print("=" * 90)
print(decision_label)


# --------------------------------------------------
# Step 6 — Severity
# --------------------------------------------------
severity_result = assess_severity(
    incident_text,
    violation_result
)

print("\n" + "=" * 90)
print("STEP 6 — SEVERITY RESULT")
print("=" * 90)
print(severity_result)


# --------------------------------------------------
# Step 7 — History
# --------------------------------------------------
previous_count = count_violations_by_person(person_id)

print("\n" + "=" * 90)
print("STEP 7 — HISTORY")
print("=" * 90)
print("Person:", person_id)
print("Role:", person_role)
print("Previous violations:", previous_count)
# --------------------------------------------------
# Step 8 — Sanction
# --------------------------------------------------
sanction_result = recommend_sanction(
    incident_text,
    violation_result,
    severity_result,
    previous_count
)

print("\n" + "=" * 90)
print("STEP 8 — SANCTION RESULT (INTERNAL)")
print("=" * 90)
print(sanction_result)


# --------------------------------------------------
# Step 9 — Save current case result
# --------------------------------------------------
insert_case_result(
    person_id=person_id,
    person_role=person_role,
    incident_file=os.path.basename(INCIDENT_PDF),
    decision=decision_label,
    violation_result_text=violation_result,
    severity=severity_result.get("severity"),
    severity_reason=severity_result.get("reason"),
    sanction_level=sanction_result.get("sanction_level"),
    recommended_action=sanction_result.get("recommended_action"),
    sanction_reason=sanction_result.get("reason"),
)

print("\n" + "=" * 90)
print("STEP 9 — CASE SAVED TO SQLITE")
print("=" * 90)
print("Saved successfully.")


# --------------------------------------------------
# Step 10 — Final clean user-facing result
# --------------------------------------------------
final_text = build_user_friendly_sanction_text(
    person_id=person_id,
    decision=decision_label,
    sanction_result=sanction_result,
)

print("\n" + "=" * 90)
print("FINAL USER-FRIENDLY RESULT")
print("=" * 90)
print(final_text)