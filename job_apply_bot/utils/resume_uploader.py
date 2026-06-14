"""Resume upload helper.

This helper must remain modular and must NOT change AI engine or tracker logic.
It provides a best-effort mechanism to upload a resume when a file input exists.

It is intentionally generic and relies on selector hints passed in by portal/ATS layers.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ResumeUploadResult:
    attempted: bool
    success: bool
    reason: str = ""


def upload_resume_if_needed(
    *,
    page,
    resume_path: str,
    file_input_selector: str = "input[type='file']",
    timeout_ms: int = 15000,
) -> ResumeUploadResult:
    """Upload resume if a matching file input is present.

    Behavior:
    - detect file input
    - upload resume from resume_path
    - wait for upload completion (best-effort)
    - return success/failure
    """

    attempted = True

    try:
        file_input = page.locator(file_input_selector).first
        if not file_input.is_visible():
            return ResumeUploadResult(attempted=True, success=False, reason="file_input_not_visible")

        file_input.set_input_files(resume_path)

        # Best-effort wait: some UIs show the file name or enable a Continue/Next button.
        # We avoid brittle selectors here; just wait a short moment for the DOM to update.
        try:
            page.wait_for_timeout(1000)
        except Exception:
            pass

        return ResumeUploadResult(attempted=attempted, success=True, reason="uploaded")

    except Exception as e:
        return ResumeUploadResult(attempted=attempted, success=False, reason=f"upload_failed:{e}")

