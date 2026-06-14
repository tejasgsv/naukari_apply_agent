"""Greenhouse ATS foundation (starter).

Starter reusable Playwright architecture. Not integrated into orchestrator yet.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


class GreenhouseATS:
    platform = "greenhouse"

    def __init__(self, *, page, settings: Optional[object] = None):
        self.page = page
        self.settings = settings

    def list_jobs(self, *, role: str, max_results: int = 20) -> list[Dict[str, Any]]:
        return []

    def upload_resume(self, *, resume_path: str) -> bool:
        from job_apply_bot.utils.resume_uploader import upload_resume_if_needed

        result = upload_resume_if_needed(page=self.page, resume_path=resume_path)
        return result.success

    def autofill_form(self, *, fields: Dict[str, str]) -> None:
        return None

    def submit_application(self) -> bool:
        return False

