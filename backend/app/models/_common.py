"""Shared helpers used across the models package."""
import uuid
from datetime import datetime, timezone


def _uuid() -> str:
    return str(uuid.uuid4())


def _now():
    return datetime.now(timezone.utc)
