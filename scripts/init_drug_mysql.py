"""Initialize MySQL drug tables from the built-in drug knowledge base.

Usage:
    python scripts/init_drug_mysql.py

The script reads MYSQL_* variables from .env and is idempotent for the built-in data.
"""

from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import text

from medagent.storage.database import get_engine
from medagent.tools.drug_db import DRUG_DATABASE, DRUG_INTERACTIONS


def _split_sql(sql: str) -> list[str]:
    return [stmt.strip() for stmt in sql.split(";") if stmt.strip()]


def create_schema() -> None:
    schema_path = Path(__file__).with_name("schema_mysql.sql")
    engine = get_engine()
    with engine.begin() as conn:
        for statement in _split_sql(schema_path.read_text(encoding="utf-8")):
            conn.execute(text(statement))


def _upsert_drug(conn, name: str, info: dict) -> int:
    conn.execute(
        text(
            "INSERT INTO drugs (name, category, dose_range, notes) "
            "VALUES (:name, :category, :dose_range, :notes) "
            "ON DUPLICATE KEY UPDATE "
            "category = VALUES(category), dose_range = VALUES(dose_range), notes = VALUES(notes)"
        ),
        {
            "name": name,
            "category": info.get("category"),
            "dose_range": info.get("dose_range"),
            "notes": info.get("notes"),
        },
    )
    row = conn.execute(text("SELECT id FROM drugs WHERE name = :name"), {"name": name}).fetchone()
    return int(row._mapping["id"])


def seed_drugs() -> None:
    engine = get_engine()
    with engine.begin() as conn:
        for name, info in DRUG_DATABASE.items():
            drug_id = _upsert_drug(conn, name, info)
            for table in ["drug_aliases", "drug_indications", "drug_contraindications", "drug_side_effects"]:
                conn.execute(text(f"DELETE FROM {table} WHERE drug_id = :drug_id"), {"drug_id": drug_id})

            for indication in info.get("indications", []):
                conn.execute(
                    text("INSERT INTO drug_indications (drug_id, indication) VALUES (:drug_id, :value)"),
                    {"drug_id": drug_id, "value": indication},
                )
            for rule_key, description in info.get("contraindications", {}).items():
                conn.execute(
                    text(
                        "INSERT INTO drug_contraindications (drug_id, rule_key, description) "
                        "VALUES (:drug_id, :rule_key, :description)"
                    ),
                    {"drug_id": drug_id, "rule_key": rule_key, "description": description},
                )
            for side_effect in info.get("side_effects", []):
                conn.execute(
                    text("INSERT INTO drug_side_effects (drug_id, side_effect) VALUES (:drug_id, :value)"),
                    {"drug_id": drug_id, "value": side_effect},
                )

        conn.execute(text("DELETE FROM drug_interactions"))
        for item in DRUG_INTERACTIONS:
            drugs = item.get("drugs", [])
            if len(drugs) < 2:
                continue
            conn.execute(
                text(
                    "INSERT INTO drug_interactions (drug_a, drug_b, interaction) "
                    "VALUES (:drug_a, :drug_b, :interaction)"
                ),
                {"drug_a": drugs[0], "drug_b": drugs[1], "interaction": item.get("interaction", "")},
            )


def main() -> None:
    create_schema()
    seed_drugs()
    print(f"Imported {len(DRUG_DATABASE)} drugs and {len(DRUG_INTERACTIONS)} interactions into MySQL.")


if __name__ == "__main__":
    main()
