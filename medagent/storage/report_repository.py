"""Redis-backed report storage."""

from __future__ import annotations

import json
import os

from medagent.storage.redis_client import get_redis


def _ttl_seconds() -> int:
    return int(os.getenv("REDIS_REPORT_TTL_SECONDS", "86400"))


def _report_key(report_id: str) -> str:
    return f"medagent:report:{report_id}"


def get_report(report_id: str) -> dict | None:
    client = get_redis()
    key = _report_key(report_id)
    raw = client.get(key)
    if raw is None:
        return None
    client.expire(key, _ttl_seconds())
    return json.loads(raw)


def save_report(report_id: str, report: dict) -> None:
    client = get_redis()
    client.setex(
        _report_key(report_id),
        _ttl_seconds(),
        json.dumps(report, ensure_ascii=False),
    )


def delete_report(report_id: str) -> None:
    client = get_redis()
    client.delete(_report_key(report_id))

