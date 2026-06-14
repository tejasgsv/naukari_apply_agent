"""Greenhouse ATS flow (best-effort)."""

from __future__ import annotations

from typing import Any, Dict, Optional

from job_apply_bot.utils.resume_uploader import fill_profile, upload_resume


class GreenhouseATS:
    platform = "greenhouse"

    def __init__(self, *, page, settings: Optional[object] = None):
        self.page = page
        self.settings = settings

    def _should_skip(self) -> Optional[str]:
        try:
            text = (self.page.content() or "").lower()
        except Exception:
            text = ""

        for needle, reason in [
            ("captcha", "captcha"),
            ("enter otp", "otp"),
            ("one-time", "otp"),
            ("verification code", "otp"),
            ("assessment", "assessment"),
            ("coding", "assessment"),
            ("video introduction", "video intro"),
            ("video intro", "video intro"),
        ]:
            if needle in text:
                return reason

        try:
            for ta in self.page.locator("textarea").all():
                try:
                    v = ta.input_value()
                    if v and len(v) > 300:
                        return "essay_too_long"
                except Exception:
                    continue
        except Exception:
            pass
        return None

    def apply(self, *, url: str) -> Dict[str, str]:
        resume_path = getattr(self.settings, "resume_path", "")
        profile = getattr(self.settings, "profile", {})

        skip_reason = self._should_skip()
        if skip_reason:
            print(f"[ATS MANUAL] reason={skip_reason}")
            return {"status": "manual_required", "reason": skip_reason}

        print("[ATS DETECTED] greenhouse")
        print("[ATS UPLOAD]")
        up = upload_resume(page=self.page, path=resume_path)
        if not up.success:
            print(f"[ATS FAIL] reason={up.reason}")
            return {"status": "failed", "reason": up.reason}

        print("[ATS FILL]")
        fill_profile(page=self.page, profile=profile)

        # Fill likely pages: contact + links are best-effort using generic selectors.
        # Submit
        for _ in range(10):
            try:
                submit_btn = self.page.locator(
                    "button[type='submit'], button:has-text('Submit'), button:has-text('Apply'), input[type='submit']"
                ).first
                if submit_btn.is_visible():
                    submit_btn.click()
                    self.page.wait_for_timeout(2000)
                    print("[ATS SUBMIT]")
                    return {"status": "applied", "reason": "submitted"}

                next_btn = self.page.locator(
                    "button:has-text('Next'), button:has-text('Continue'), button[aria-label*='Next'], button[aria-label*='Continue']"
                ).first
                if next_btn.is_visible():
                    next_btn.click()
                    self.page.wait_for_timeout(1200)
                    continue

                break
            except Exception as e:
                # transient retry
                try:
                    self.page.wait_for_timeout(1000)
                except Exception:
                    pass

        print("[ATS MANUAL] reason=submit_not_reached")
        return {"status": "manual_required", "reason": "submit_not_reached"}


