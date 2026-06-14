"""Resume upload + profile autofill helpers for external ATS portals.

Rules:
- Keep this file modular (no AI/tracker logic here)
- Provide generic selector strategies that ATS handlers can reuse
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


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
    """Backward-compatible wrapper (existing code may import this)."""
    return upload_resume(page=page, path=resume_path, page_timeout_ms=timeout_ms)


def upload_resume(*, page, path: str, page_timeout_ms: int = 15000) -> ResumeUploadResult:
    """Upload resume using the first visible file input."""
    attempted = True
    try:
        file_input = page.locator("input[type='file']").first
        if not file_input.is_visible():
            return ResumeUploadResult(attempted=attempted, success=False, reason="file_input_not_visible")

        file_input.set_input_files(path)
        try:
            page.wait_for_timeout(1000)
        except Exception:
            pass
        return ResumeUploadResult(attempted=attempted, success=True, reason="uploaded")
    except Exception as e:
        return ResumeUploadResult(attempted=attempted, success=False, reason=f"upload_failed:{e}")


def _fill_by_selectors(page, selectors: list[str], value: str) -> bool:
    if value is None:
        return False
    filled = False
    for sel in selectors:
        loc = page.locator(sel).first
        try:
            if loc.count() > 0 and loc.is_visible():
                loc.fill(str(value))
                filled = True
                break
        except Exception:
            continue
    return filled


def fill_profile(*, page, profile: Dict[str, Any]) -> bool:
    """Best-effort profile autofill.

    Selector strategy (per-field):
    - input[type=file] handled by upload_resume
    - inputs via: input[name*=...]
    - textarea via: textarea
    - dropdowns via: select (only best-effort)
    """
    filled_any = False

    mapping = {
        "name": ["input[name*=name]", "input[aria-label*=name]", "input[placeholder*=name]"],
        "email": ["input[name*=email]", "input[aria-label*=email]", "input[placeholder*=email]"],
        "phone": ["input[name*=phone]", "input[aria-label*=phone]", "input[placeholder*=phone]"],
        "location": ["input[name*=location]", "input[aria-label*=location]", "textarea"],
        "linkedin": ["input[name*=linkedin]", "input[aria-label*=linkedin]", "input[placeholder*=linkedin]"],
        "github": ["input[name*=github]", "input[aria-label*=github]", "input[placeholder*=github]"],
        "experience": ["textarea", "input[name*=experience]", "input[aria-label*=experience]"],
        "notice_period": ["input[name*=notice]", "select[name*=notice]", "input[aria-label*=notice]"],
        "current_ctc": ["input[name*=current]", "input[name*=ctc]", "input[aria-label*=current]"],
        "expected_ctc": ["input[name*=expected]", "input[name*=ctc]", "input[aria-label*=expected]"],
    }

    for key, selectors in mapping.items():
        if key not in profile:
            continue
        val = profile.get(key)
        if val is None:
            continue

        # Special-case: experience/textarea may need newline normalization
        if key == "experience" and isinstance(val, str):
            val = val.strip()

        ok = _fill_by_selectors(page, selectors, str(val))
        if ok:
            filled_any = True

    return filled_any


