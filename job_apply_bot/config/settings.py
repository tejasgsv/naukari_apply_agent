from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


def _get_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


def _get_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except Exception:
        return default


def _get_list(name: str, default: List[str]) -> List[str]:
    raw = os.getenv(name)
    if not raw:
        return default
    return [x.strip() for x in raw.split(",") if x.strip()]


def _get_dict(name: str, default: Dict[str, Any]) -> Dict[str, Any]:
    raw = os.getenv(name)
    if not raw:
        return default
    return default


@dataclass(frozen=True)
class Settings:
    roles: List[str]
    country: str
    max_pages: int
    headless: bool

    ollama_model: str
    ollama_base_url: str

    resume_path: str
    remote_only: bool

    job_post_max_age_hours: int
    check_interval_minutes: int
    max_required_years: int

    profile: Dict[str, Any]
    filters: Dict[str, Any]

    browser_executable_path: Optional[str] = None

    @staticmethod
    def load() -> "Settings":
        roles = _get_list(
            "ROLES",
            default=[
                "DevOps Engineer",
                "Cloud Engineer",
                "Platform Engineer",
            ],
        )

        country = os.getenv("COUNTRY", "India")
        max_pages = _get_int("MAX_PAGES", 3)
        headless = _get_bool("HEADLESS", False)

        # Ollama config
        ollama_model = os.getenv("OLLAMA_MODEL", "llama3:latest")
        ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

        resume_path = os.getenv(
            "RESUME_PATH",
            "resumes/TEJAS_DEVOPS_UPDATED_CV.pdf"
        )

        # IMPORTANT FIX
        remote_only = _get_bool("REMOTE_ONLY", False)

        job_post_max_age_hours = _get_int("JOB_POST_MAX_AGE_HOURS", 24)
        check_interval_minutes = _get_int("CHECK_INTERVAL_MINUTES", 60)
        max_required_years = _get_int("MAX_REQUIRED_YEARS", 3)

        profile = {
            "name": os.getenv("PROFILE_NAME", "Tejas Goswami"),
            "experience_years": float(
                os.getenv("PROFILE_EXPERIENCE_YEARS", "1.5")
            ),
            "current_company": os.getenv(
                "PROFILE_CURRENT_COMPANY",
                "Reliance Jio"
            ),
            "skills": _get_list(
                "PROFILE_SKILLS",
                default=[
                    "Terraform",
                    "Azure",
                    "Azure Pipelines",
                    "GitHub Actions",
                    "Docker",
                    "Kubernetes",
                    "Linux",
                    "Bash",
                    "PowerShell",
                    "YAML",
                ],
            ),
        }

        filters = _get_dict("FILTERS", {})
        browser_executable_path = os.getenv("BROWSER_PATH")

        return Settings(
            roles=roles,
            country=country,
            max_pages=max_pages,
            headless=headless,
            ollama_model=ollama_model,
            ollama_base_url=ollama_base_url,
            resume_path=resume_path,
            remote_only=remote_only,
            job_post_max_age_hours=job_post_max_age_hours,
            check_interval_minutes=check_interval_minutes,
            max_required_years=max_required_years,
            profile=profile,
            filters=filters,
            browser_executable_path=browser_executable_path,
        )