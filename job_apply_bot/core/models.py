"""Domain models (stub)."""

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class JobPosting:
    platform: str
    title: str
    company: str
    description: str
    url: str
    platform_job_id: Optional[str] = None
    location: Optional[str] = None
    raw: Optional[Dict[str, Any]] = None


@dataclass(frozen=True)
class AIJobDecision:
    decision: str  # "APPLY" | "SKIP"
    match_percentage: int
    reason: str
    pitch: str


@dataclass(frozen=True)
class ApplicationPlan:
    resume_upload: bool
    answers: Dict[str, str]
    # Extend later with other form field mapping


@dataclass(frozen=True)
class ApplicationResult:
    status: str  # "APPLIED" | "SKIPPED" | "MANUAL_REQUIRED" | "FAILED"
    reason: str = ""
    metadata: Optional[Dict[str, Any]] = None

