"""Timing helpers used by the human behavior engine.

Phase 3 scope:
- jitter(): small randomized variation around a base value
- random_interval(): random float between min/max
- reading_time(): estimate reading time from content length

All functions have safe fallbacks and do not require Playwright.
"""

from __future__ import annotations

import random


def jitter(base_time: float, jitter_ratio: float = 0.25) -> float:
    """Return base_time with +/- jitter_ratio randomness."""
    try:
        base = float(base_time)
    except Exception:
        return 0.0

    jitter_amount = base * float(jitter_ratio)
    return max(0.0, random.uniform(base - jitter_amount, base + jitter_amount))


def reading_time(text_length: int, wpm: int = 180, min_sec: float = 1.5, max_sec: float = 25.0) -> float:
    """Estimate how long a human would read based on text_length.

    text_length approximates characters; convert to words conservatively.
    """
    try:
        length = int(text_length)
    except Exception:
        length = 0

    # Rough char->word estimate: 1 word ~ 5 chars
    words = max(1, length // 5)
    minutes = words / max(1, wpm)
    sec = minutes * 60
    sec = max(min_sec, sec)
    return min(max_sec, sec)


def random_interval(min_sec: float, max_sec: float) -> float:
    """Random float between min_sec and max_sec."""
    a = float(min_sec)
    b = float(max_sec)
    if b < a:
        a, b = b, a
    return random.uniform(a, b)


