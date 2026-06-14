"""Workday ATS flow (best-effort).

Implements a generic external-portal application flow:
- detect/skip captcha/otp/assessment/long essay
- upload resume
- fill basic profile fields
- click next buttons until submit

Note: selectors are intentionally generic/best-effort to avoid brittle scraping.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from job_apply_bot.utils.resume_uploader import fill_profile, upload_resume


class WorkdayATS:
    platform = "workday"

    def __init__(self, *, page, settings: Optional[object] = None):
        self.page = page
        self.settings = settings

    def _should_skip(self) -> Optional[str]:
        # Skip logic (best-effort): look for common cues.
        text = ""
        try:
            text = (self.page.content() or "").lower()
        except Exception:
            pass

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
        # Essay length skip: if any textarea contains long content, skip.
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

        print("[ATS DETECTED] workday")
        print("[ATS UPLOAD]")
        up = upload_resume(page=self.page, path=resume_path)
        if not up.success:
            print(f"[ATS FAIL] reason={up.reason}")
            return {"status": "failed", "reason": up.reason}

        print("[ATS FILL]")
        filled = fill_profile(page=self.page, profile=profile)
        _ = filled  # best-effort; may legitimately be False

        # Retry loop for transient failures
        last_reason = ""
        for attempt in range(3):
            try:
                for _ in range(30):
                    if self._should_skip():
                        print("[ATS MANUAL] reason=skip_detected")
                        return {"status": "manual_required", "reason": "skip_detected"}

                    # Upload resume can trigger async UI; wait a touch.
                    try:
                        self.page.wait_for_timeout(800)
                    except Exception:
                        pass

                    # Submit if present
                    submit_btn = self.page.locator(
                        "button[type='submit'], button:has-text('Submit'), button:has-text('Review')"
                    ).first
                    if submit_btn.is_visible():
                        try:
                            submit_btn.click()
                            self.page.wait_for_timeout(2000)
                        except Exception as e:
                            last_reason = f"submit_click_failed:{e}"
                            continue
                        print("[ATS SUBMIT]")
                        return {"status": "applied", "reason": "submitted"}

                    # Otherwise click next/continue
                    next_btn = self.page.locator(
                        "button:has-text('Next'), button:has-text('Continue'), button[aria-label*='Next'], button[aria-label*='Continue']"
                    ).first
                    if next_btn.is_visible():
                        next_btn.click()
                        continue

                    # If no navigation found, manual required.
                    break

                # If loop exits without submit
                print("[ATS MANUAL] reason=submit_not_reached")
                return {"status": "manual_required", "reason": "submit_not_reached"}

            except Exception as e:
                last_reason = f"transient_failure:{e}"
                try:
                    self.page.wait_for_timeout(1500)
                except Exception:
                    pass
                continue

        print(f"[ATS FAIL] reason={last_reason}")
        return {"status": "failed", "reason": last_reason}



