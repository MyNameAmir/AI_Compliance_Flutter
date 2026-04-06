import os
from typing import Optional, List, Dict, Any
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

# -----------------------------
# 🔐 AWS MYSQL CREDENTIALS
# Must be set via environment variables
# -----------------------------
MYSQL_HOST = os.getenv("MYSQL_HOST")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER")
MYSQL_PASS = os.getenv("MYSQL_PASS")
MYSQL_DB   = os.getenv("MYSQL_DB")

# -----------------------------
# 🔌 SQLAlchemy Engine
# -----------------------------
engine = create_engine(
    f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASS}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}",
    pool_pre_ping=True,
    future=True
)


def initialize_database() -> None:
    """
    Creates the violations table if it does not exist.
    Equivalent to the SQLite version.
    """
    create_table_sql = """
        CREATE TABLE IF NOT EXISTS PRD01.violations (
            id INT AUTO_INCREMENT PRIMARY KEY,
            person_id VARCHAR(255),
            person_role VARCHAR(255),
            incident_file VARCHAR(255),
            decision VARCHAR(255) NOT NULL,
            violation_result_text TEXT,
            severity VARCHAR(255),
            severity_reason TEXT,
            sanction_level VARCHAR(255),
            recommended_action TEXT,
            sanction_reason TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """

    try:
        with engine.connect() as conn:
            conn.execute(text(create_table_sql))
            conn.commit()
    except SQLAlchemyError as e:
        print("Error initializing MySQL violations table:", e)


def insert_case_result(
    person_id: Optional[str],
    person_role: Optional[str],
    incident_file: str,
    decision: str,
    violation_result_text: Optional[str] = None,
    severity: Optional[str] = None,
    severity_reason: Optional[str] = None,
    sanction_level: Optional[str] = None,
    recommended_action: Optional[str] = None,
    sanction_reason: Optional[str] = None,
) -> None:

    sql = """
        INSERT INTO PRD01.violations (
            person_id,
            person_role,
            incident_file,
            decision,
            violation_result_text,
            severity,
            severity_reason,
            sanction_level,
            recommended_action,
            sanction_reason
        )
        VALUES (
            :person_id, :person_role, :incident_file, :decision,
            :violation_result_text, :severity, :severity_reason,
            :sanction_level, :recommended_action, :sanction_reason
        );
    """

    params = {
        "person_id": person_id,
        "person_role": person_role,
        "incident_file": incident_file,
        "decision": decision,
        "violation_result_text": violation_result_text,
        "severity": severity,
        "severity_reason": severity_reason,
        "sanction_level": sanction_level,
        "recommended_action": recommended_action,
        "sanction_reason": sanction_reason,
    }

    try:
        with engine.connect() as conn:
            conn.execute(text(sql), params)
            conn.commit()
    except SQLAlchemyError as e:
        print("Error inserting case result:", e)


def get_all_violations() -> List[Dict[str, Any]]:
    sql = "SELECT * FROM PRD01.violations ORDER BY id ASC"

    try:
        with engine.connect() as conn:
            result = conn.execute(text(sql)).mappings().all()
            return [dict(row) for row in result]

    except SQLAlchemyError as e:
        print("Error fetching violations:", e)
        return []


def get_violations_by_person(person_id: str) -> List[Dict[str, Any]]:
    sql = """
        SELECT *
        FROM PRD01.violations
        WHERE person_id = :person_id
        ORDER BY id ASC
    """

    try:
        with engine.connect() as conn:
            result = conn.execute(text(sql), {"person_id": person_id}).mappings().all()
            return [dict(row) for row in result]

    except SQLAlchemyError as e:
        print("Error fetching person violations:", e)
        return []


def count_violations_by_person(person_id: str) -> int:
    sql = """
        SELECT COUNT(*) AS count
        FROM PRD01.violations
        WHERE person_id = :person_id
          AND LOWER(decision) = 'violation'
    """

    try:
        with engine.connect() as conn:
            row = conn.execute(text(sql), {"person_id": person_id}).mappings().first()
            return int(row["count"]) if row else 0

    except SQLAlchemyError as e:
        print("Error counting violations:", e)
        return 0
