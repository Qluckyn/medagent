"""Redis-backed chat session storage."""

from __future__ import annotations

import json
import os

from medagent.models.schemas import GraphState
from medagent.storage.redis_client import get_redis


def _ttl_seconds() -> int:
    return int(os.getenv("REDIS_CHAT_TTL_SECONDS", "86400"))


def _session_key(session_id: str) -> str:
    return f"medagent:chat:{session_id}"


def get_chat_session(session_id: str) -> GraphState | None:
    client = get_redis()
    key = _session_key(session_id)
    raw = client.get(key)
    if raw is None:
        return None
    client.expire(key, _ttl_seconds())
    data = json.loads(raw)
    return GraphState(**data)


def save_chat_session(session_id: str, state: GraphState) -> None:
    client = get_redis()
    client.setex(
        _session_key(session_id),
        _ttl_seconds(),
        json.dumps(state.model_dump(mode="json"), ensure_ascii=False),
    )


def delete_chat_session(session_id: str) -> None:
    client = get_redis()
    client.delete(_session_key(session_id))

