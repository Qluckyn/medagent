"""Redis connection helpers for MedAgent."""

from __future__ import annotations

import os
from functools import lru_cache
from urllib.parse import urlparse

from dotenv import load_dotenv

load_dotenv()


def _redis_url() -> str:
    url = os.getenv("REDIS_URL")
    if not url:
        raise RuntimeError("Redis is not configured")
    return url


def _redis_kwargs_from_url() -> dict:
    parsed = urlparse(_redis_url())
    if parsed.scheme not in {"redis", "rediss"}:
        raise RuntimeError(f"Unsupported Redis URL scheme: {parsed.scheme}")

    db = 0
    if parsed.path and parsed.path != "/":
        try:
            db = int(parsed.path.lstrip("/"))
        except ValueError as exc:
            raise RuntimeError(f"Invalid Redis database path: {parsed.path}") from exc

    kwargs = {
        "host": parsed.hostname or "localhost",
        "port": parsed.port or 6379,
        "db": db,
        "password": parsed.password,
        "ssl": parsed.scheme == "rediss",
        "decode_responses": True,
        "protocol": 2,
    }

    # Older Redis deployments often use password-only auth and do not support HELLO/ACL username auth.
    # Only pass username when it is explicitly present and non-empty.
    if parsed.username:
        kwargs["username"] = parsed.username

    return kwargs


@lru_cache(maxsize=1)
def get_redis():
    """Return a cached Redis client."""
    try:
        from redis import Redis
        from redis.exceptions import RedisError
    except ImportError as exc:
        raise RuntimeError("Redis dependency is not installed") from exc

    try:
        client = Redis(**_redis_kwargs_from_url())
        client.ping()
        return client
    except RedisError as exc:
        raise RuntimeError(f"Redis connection failed: {exc}") from exc


def clear_redis_cache() -> None:
    get_redis.cache_clear()
