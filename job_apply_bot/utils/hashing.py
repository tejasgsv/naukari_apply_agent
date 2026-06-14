"""Hashing helpers (stub)."""

import hashlib


def sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

