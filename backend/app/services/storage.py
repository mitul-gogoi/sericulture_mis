"""Local filesystem object storage under settings.UPLOAD_ROOT."""
import re
from typing import Tuple
from app.core.config import settings

_UNSAFE = re.compile(r'[\\/:*?"<>|\x00-\x1f]')


def _safe_segment(name: str) -> str:
    cleaned = _UNSAFE.sub("", name).strip()
    return re.sub(r"\s+", " ", cleaned) or "Unknown"


def put_object(path: str, data: bytes, content_type: str) -> dict:
    full = settings.UPLOAD_ROOT / path
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_bytes(data)
    return {"path": path, "size": len(data)}


def get_object(path: str) -> Tuple[bytes, str]:
    full = settings.UPLOAD_ROOT / path
    if not full.is_file():
        raise RuntimeError("File not found")
    return full.read_bytes(), "application/octet-stream"
