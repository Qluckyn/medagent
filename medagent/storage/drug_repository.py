"""MySQL-backed drug knowledge repository."""

from __future__ import annotations

from sqlalchemy import text

from medagent.storage.database import get_engine


class DrugRepositoryError(RuntimeError):
    """Base repository error."""


class DrugNotFoundError(DrugRepositoryError):
    """Raised when a drug record does not exist."""


class DrugConflictError(DrugRepositoryError):
    """Raised when a drug record conflicts with an existing one."""


def _row_to_dict(row) -> dict:
    return dict(row._mapping)


def _fetch_child_values(conn, table: str, column: str, drug_id: int) -> list[str]:
    rows = conn.execute(
        text(f"SELECT {column} FROM {table} WHERE drug_id = :drug_id ORDER BY id"),
        {"drug_id": drug_id},
    ).fetchall()
    return [row._mapping[column] for row in rows]


def _clean_text(value: str | None) -> str:
    return (value or "").strip()


def _clean_list(values: list[str] | None) -> list[str]:
    if not values:
        return []
    cleaned: list[str] = []
    seen: set[str] = set()
    for item in values:
        value = _clean_text(item)
        if not value:
            continue
        if value in seen:
            continue
        seen.add(value)
        cleaned.append(value)
    return cleaned


def _clean_contraindications(values: dict[str, str] | None) -> dict[str, str]:
    if not values:
        return {}
    cleaned: dict[str, str] = {}
    for key, description in values.items():
        rule_key = _clean_text(key)
        text_value = _clean_text(description)
        if not rule_key or not text_value:
            continue
        cleaned[rule_key] = text_value
    return cleaned


def _fetch_contraindications(conn, drug_id: int) -> dict[str, str]:
    rows = conn.execute(
        text(
            "SELECT rule_key, description FROM drug_contraindications "
            "WHERE drug_id = :drug_id ORDER BY id"
        ),
        {"drug_id": drug_id},
    ).fetchall()
    return {row._mapping["rule_key"]: row._mapping["description"] for row in rows}


def _hydrate_drug(conn, row) -> tuple[str, dict]:
    data = _row_to_dict(row)
    drug_id = data["id"]
    return data["name"], {
        "id": drug_id,
        "name": data["name"],
        "category": data.get("category") or "",
        "aliases": _fetch_child_values(conn, "drug_aliases", "alias", drug_id),
        "indications": _fetch_child_values(conn, "drug_indications", "indication", drug_id),
        "contraindications": _fetch_contraindications(conn, drug_id),
        "dose_range": data.get("dose_range") or "",
        "side_effects": _fetch_child_values(conn, "drug_side_effects", "side_effect", drug_id),
        "notes": data.get("notes") or "",
    }


def find_drug_by_name(drug_name: str) -> tuple[str, dict] | None:
    """Find a drug by exact name, alias, or fuzzy match."""
    if not drug_name or not drug_name.strip():
        return None

    name = drug_name.strip()
    engine = get_engine()
    with engine.connect() as conn:
        exact = conn.execute(
            text(
                "SELECT DISTINCT d.* FROM drugs d "
                "LEFT JOIN drug_aliases a ON a.drug_id = d.id "
                "WHERE d.name = :name OR a.alias = :name "
                "LIMIT 1"
            ),
            {"name": name},
        ).fetchone()
        if exact:
            return _hydrate_drug(conn, exact)

        fuzzy = conn.execute(
            text(
                "SELECT DISTINCT d.* FROM drugs d "
                "LEFT JOIN drug_aliases a ON a.drug_id = d.id "
                "WHERE d.name LIKE :like OR a.alias LIKE :like OR :name LIKE CONCAT('%', d.name, '%') "
                "LIMIT 1"
            ),
            {"name": name, "like": f"%{name}%"},
        ).fetchone()
        if fuzzy:
            return _hydrate_drug(conn, fuzzy)

    return None


def get_drug_by_id(drug_id: int) -> dict:
    """Return a full drug record by ID."""
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT * FROM drugs WHERE id = :drug_id LIMIT 1"),
            {"drug_id": drug_id},
        ).fetchone()
        if not row:
            raise DrugNotFoundError(f"Drug {drug_id} not found")
        _, data = _hydrate_drug(conn, row)
    return data


def list_drugs() -> list[dict]:
    """Return all drug records."""
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT * FROM drugs ORDER BY name, id")).fetchall()
        return [_hydrate_drug(conn, row)[1] for row in rows]


def _ensure_unique_name(conn, name: str, exclude_id: int | None = None) -> None:
    sql = "SELECT id FROM drugs WHERE name = :name"
    params: dict[str, object] = {"name": name}
    if exclude_id is not None:
        sql += " AND id <> :exclude_id"
        params["exclude_id"] = exclude_id
    row = conn.execute(text(sql + " LIMIT 1"), params).fetchone()
    if row:
        raise DrugConflictError(f"Drug name already exists: {name}")


def _replace_children(conn, drug_id: int, payload: dict) -> None:
    conn.execute(text("DELETE FROM drug_aliases WHERE drug_id = :drug_id"), {"drug_id": drug_id})
    conn.execute(text("DELETE FROM drug_indications WHERE drug_id = :drug_id"), {"drug_id": drug_id})
    conn.execute(
        text("DELETE FROM drug_contraindications WHERE drug_id = :drug_id"),
        {"drug_id": drug_id},
    )
    conn.execute(
        text("DELETE FROM drug_side_effects WHERE drug_id = :drug_id"),
        {"drug_id": drug_id},
    )

    for alias in _clean_list(payload.get("aliases")):
        conn.execute(
            text("INSERT INTO drug_aliases (drug_id, alias) VALUES (:drug_id, :alias)"),
            {"drug_id": drug_id, "alias": alias},
        )

    for indication in _clean_list(payload.get("indications")):
        conn.execute(
            text("INSERT INTO drug_indications (drug_id, indication) VALUES (:drug_id, :value)"),
            {"drug_id": drug_id, "value": indication},
        )

    for rule_key, description in _clean_contraindications(
        payload.get("contraindications")
    ).items():
        conn.execute(
            text(
                "INSERT INTO drug_contraindications (drug_id, rule_key, description) "
                "VALUES (:drug_id, :rule_key, :description)"
            ),
            {"drug_id": drug_id, "rule_key": rule_key, "description": description},
        )

    for side_effect in _clean_list(payload.get("side_effects")):
        conn.execute(
            text("INSERT INTO drug_side_effects (drug_id, side_effect) VALUES (:drug_id, :value)"),
            {"drug_id": drug_id, "value": side_effect},
        )


def create_drug(payload: dict) -> dict:
    """Create a drug record and return the stored object."""
    name = _clean_text(payload.get("name"))
    if not name:
        raise DrugConflictError("Drug name is required")

    engine = get_engine()
    with engine.begin() as conn:
        _ensure_unique_name(conn, name)
        result = conn.execute(
            text(
                "INSERT INTO drugs (name, category, dose_range, notes) "
                "VALUES (:name, :category, :dose_range, :notes)"
            ),
            {
                "name": name,
                "category": _clean_text(payload.get("category")),
                "dose_range": _clean_text(payload.get("dose_range")),
                "notes": _clean_text(payload.get("notes")),
            },
        )
        drug_id = int(result.lastrowid)
        _replace_children(conn, drug_id, payload)

    return get_drug_by_id(drug_id)


def update_drug(drug_id: int, payload: dict) -> dict:
    """Replace a drug record and return the stored object."""
    name = _clean_text(payload.get("name"))
    if not name:
        raise DrugConflictError("Drug name is required")

    engine = get_engine()
    with engine.begin() as conn:
        current = conn.execute(
            text("SELECT id, name FROM drugs WHERE id = :drug_id LIMIT 1"),
            {"drug_id": drug_id},
        ).fetchone()
        if not current:
            raise DrugNotFoundError(f"Drug {drug_id} not found")

        old_name = current._mapping["name"]
        _ensure_unique_name(conn, name, exclude_id=drug_id)

        conn.execute(
            text(
                "UPDATE drugs SET name = :name, category = :category, dose_range = :dose_range, notes = :notes "
                "WHERE id = :drug_id"
            ),
            {
                "drug_id": drug_id,
                "name": name,
                "category": _clean_text(payload.get("category")),
                "dose_range": _clean_text(payload.get("dose_range")),
                "notes": _clean_text(payload.get("notes")),
            },
        )
        _replace_children(conn, drug_id, payload)
        if old_name != name:
            conn.execute(
                text("UPDATE drug_interactions SET drug_a = :new_name WHERE drug_a = :old_name"),
                {"old_name": old_name, "new_name": name},
            )
            conn.execute(
                text("UPDATE drug_interactions SET drug_b = :new_name WHERE drug_b = :old_name"),
                {"old_name": old_name, "new_name": name},
            )

    return get_drug_by_id(drug_id)


def delete_drug(drug_id: int) -> None:
    """Delete a drug record."""
    engine = get_engine()
    with engine.begin() as conn:
        current = conn.execute(
            text("SELECT id, name FROM drugs WHERE id = :drug_id LIMIT 1"),
            {"drug_id": drug_id},
        ).fetchone()
        if not current:
            raise DrugNotFoundError(f"Drug {drug_id} not found")

        drug_name = current._mapping["name"]
        conn.execute(
            text("DELETE FROM drug_interactions WHERE drug_a = :name OR drug_b = :name"),
            {"name": drug_name},
        )
        conn.execute(text("DELETE FROM drugs WHERE id = :drug_id"), {"drug_id": drug_id})


def list_drug_names() -> list[str]:
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT name FROM drugs ORDER BY name")).fetchall()
    return [row._mapping["name"] for row in rows]


def find_interactions(drug_list: list[str]) -> list[dict]:
    """Return matched interactions. Raises if the database is unavailable."""
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT drug_a, drug_b, interaction FROM drug_interactions ORDER BY id")
        ).fetchall()

    found = []
    for row in rows:
        item = row._mapping
        required = [item["drug_a"], item["drug_b"]]
        match_count = 0
        for drug in required:
            for patient_drug in drug_list:
                if drug in patient_drug or patient_drug in drug:
                    match_count += 1
                    break
        if match_count >= 2:
            found.append({"drugs": required, "interaction": item["interaction"]})
    return found
