"""Aadhaar at-rest protection.

The raw 12-digit number is never persisted. Each farmer stores three derived values:

  aadhaar_last4  plaintext last 4 digits — the only part ever shown to an admin
  aadhaar_hash   HMAC-SHA256 blind index — preserves the "Aadhaar already registered"
                 duplicate check without storing anything an attacker could read back
  aadhaar_enc    AES-256-GCM ciphertext — reversible, and decrypted in exactly one
                 place: the farmer's own `GET /farmers/me`

Neither `aadhaar_hash` nor `aadhaar_enc` may ever leave the server — the ciphertext is
self-explanatory, and the blind index is brute-forceable offline over a 12-digit space
by anyone holding the key. `services/farmer_reports.public_farmer_dict()` is the choke
point that strips both.

Both subkeys are derived from one AADHAAR_SECRET_KEY under distinct labels, so the same
key material is never reused across two primitives.

WARNING: losing or rotating AADHAAR_SECRET_KEY makes every stored ciphertext permanently
undecryptable AND changes every blind index, silently breaking duplicate detection. Back
it up; it cannot be rotated without a dedicated re-encryption migration.
"""
import base64
import hashlib
import hmac
import os
import re
from typing import Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from .config import settings

_MIN_KEY_LEN = 32
_NONCE_BYTES = 12
_DIGITS_RE = re.compile(r"^\d{12}$")
_SEPARATORS_RE = re.compile(r"[\s\-]")

if len(settings.AADHAAR_SECRET_KEY) < _MIN_KEY_LEN:
    raise RuntimeError(
        f"AADHAAR_SECRET_KEY must be at least {_MIN_KEY_LEN} characters — "
        "generate one with `openssl rand -hex 32`"
    )

_master = settings.AADHAAR_SECRET_KEY.encode()
_HMAC_KEY = hmac.new(_master, b"aadhaar-blind-index-v1", hashlib.sha256).digest()
_ENC_KEY = hmac.new(_master, b"aadhaar-encryption-v1", hashlib.sha256).digest()  # 32 bytes -> AES-256


def normalize_aadhaar(raw: str) -> str:
    """Strip the spaces/hyphens Aadhaar is commonly written with ("1234 5678 9012"),
    then require exactly 12 digits. Single source of truth for the validation rule, so
    create and update surface an identical error message."""
    digits = _SEPARATORS_RE.sub("", (raw or "").strip())
    if not _DIGITS_RE.match(digits):
        raise ValueError("Aadhaar must be exactly 12 digits")
    return digits


def aadhaar_hash(digits: str) -> str:
    """Deterministic blind index — what the duplicate check queries on."""
    return hmac.new(_HMAC_KEY, digits.encode(), hashlib.sha256).hexdigest()


def aadhaar_encrypt(digits: str) -> str:
    """base64(nonce || ciphertext+tag). Fresh random nonce per call."""
    nonce = os.urandom(_NONCE_BYTES)
    return base64.b64encode(nonce + AESGCM(_ENC_KEY).encrypt(nonce, digits.encode(), None)).decode()


def aadhaar_decrypt(blob: str) -> str:
    raw = base64.b64decode(blob)
    return AESGCM(_ENC_KEY).decrypt(raw[:_NONCE_BYTES], raw[_NONCE_BYTES:], None).decode()


def aadhaar_fields(digits: str) -> dict:
    """The three stored column values for an already-normalized 12-digit number.
    One definition, shared by create/update, the backfill migration, and the seeder."""
    return {
        "aadhaar_last4": digits[-4:],
        "aadhaar_hash": aadhaar_hash(digits),
        "aadhaar_enc": aadhaar_encrypt(digits),
    }


def mask_aadhaar(last4: Optional[str]) -> Optional[str]:
    """Display form for every role except the farmer viewing their own record."""
    return f"{'*' * 8}{last4}" if last4 else None
