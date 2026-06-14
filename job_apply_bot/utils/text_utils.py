"""Text normalization helpers (stub)."""

from typing import Optional


def normalize_ws(s: Optional[str]) -> str:
    if not s:
        return ""
    return " ".join(s.split())

