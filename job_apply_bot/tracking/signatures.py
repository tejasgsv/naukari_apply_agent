"""Duplicate prevention signatures.

We need deterministic signatures across runs.

Strategy:
1) If platform_job_id is available, signature = sha256(platform + ":" + platform_job_id)
2) Else, fallback to sha256(platform + normalized(title) + normalized(company) + normalized(url)).

Normalization is important to reduce accidental duplicates.
"""

from __future__ import annotations

import hashlib
from typing import Optional


def normalize(s: Optional[str]) -> str:
    if not s:
        return ""
    # whitespace normalization + lowercasing
    return " ".join(s.casefold().split())


def compute_job_signature(
    platform: str,
    platform_job_id: Optional[str],
    title: str,
    company: str,
    url: str,
) -> str:
    platform = (platform or "").strip().casefold()

    if platform_job_id:
        base = f"{platform}:{str(platform_job_id).strip()}"
    else:
        base = f"{platform}:{normalize(title)}:{normalize(company)}:{normalize(url)}"

    return hashlib.sha256(base.encode("utf-8")).hexdigest()


