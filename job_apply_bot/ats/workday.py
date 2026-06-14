"""Workday ATS foundation (starter).

Provides reusable Playwright-oriented building blocks for:
- login/session reuse
- job listing scraping
- resume upload flow
- form autofill
- submit flow

This is starter architecture only; not integrated into orchestrator yet.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


class WorkdayATS:
    platform = "workday"

    def __init__(self, *, page, settings: Optional[object] = None):
        self.page = page
        self.settings = settings

    # ---- Listing ----
    def list_jobs(self, *, role: str, max_results: int = 20) -> list[Dict[str, Any]]:
        # Starter stub: implement portal-specific selectors in future phases.
        return []

    # ---- Resume Upload ----
    def upload_resume(self, *, resume_path: str) -> bool:
        # Starter: detect and upload resume using a generic file input.
        from job_apply_bot.utils.resume_uploader import upload_resume_if_needed

        result = upload_resume_if_needed(page=self.page, resume_path=resume_path)
        return result.success

    # ---- Autofill ----
    def autofill_form(self, *, fields: Dict[str, str]) -> None:
        # Starter stub.
        return None

    # ---- Submit ----
    def submit_application(self) -> bool:
        # Starter stub.
        return False

