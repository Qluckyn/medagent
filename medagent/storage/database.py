"""Database connection helpers."""

from __future__ import annotations

import os
from functools import lru_cache
from urllib.parse import quote_plus

from dotenv import load_dotenv

load_dotenv()


def _env_bool(name: str, default: bool = True) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _mysql_url() -> str | None:
    explicit_url = os.getenv("MYSQL_URL")
    if explicit_url:
        return explicit_url

    host = os.getenv("MYSQL_HOST")
    user = os.getenv("MYSQL_USER")
    database = os.getenv("MYSQL_DATABASE")
    if not host or not user or not database:
        return None

    port = os.getenv("MYSQL_PORT", "3306")
    password = quote_plus(os.getenv("MYSQL_PASSWORD", ""))
    charset = os.getenv("MYSQL_CHARSET", "utf8mb4")
    return f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}?charset={charset}"


@lru_cache(maxsize=1)
def get_engine():
    """Return a cached SQLAlchemy engine for the configured MySQL database."""
    if not _env_bool("MYSQL_DRUG_DB_ENABLED", True):
        raise RuntimeError("MySQL drug database is disabled")

    url = _mysql_url()
    if not url:
        raise RuntimeError("MySQL database is not configured")

    try:
        from sqlalchemy import create_engine
    except ImportError as exc:
        raise RuntimeError("SQLAlchemy/PyMySQL dependencies are not installed") from exc

    return create_engine(
        url,
        pool_pre_ping=True,
        pool_recycle=int(os.getenv("MYSQL_POOL_RECYCLE", "1800")),
    )


def clear_engine_cache() -> None:
    get_engine.cache_clear()
