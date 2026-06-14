"""LinkedIn bot (production-ready implementation).

Implements only LinkedIn platform bot for Phase 5A.

Core responsibilities:
- Search jobs across multiple roles from Settings
- Extract job postings (title, company, url, description, platform_job_id)
- Duplicate prevention via Tracker signatures
- AI decision via AIEngine
- Apply via Easy Apply flow with retry + safe fallbacks

Notes:
- This bot assumes that `SessionManager`/`PlaywrightManager` are already wired in later phases.
- In this Phase 5A file we implement the bot behavior behind the PlatformBot interface.
"""

from __future__ import annotations

import time
import logging

from typing import Dict, Iterable, List, Optional, Tuple

from playwright.sync_api import Page

from job_apply_bot.bots.base import PlatformBot
from job_apply_bot.automation.behavior_engine import BehaviorEngine
from job_apply_bot.ai.engine import AIEngine
from job_apply_bot.config.settings import Settings
from job_apply_bot.tracking.tracker import Tracker


class LinkedInBot(PlatformBot):
    platform = "linkedin"

    # LinkedIn selectors are volatile; keep them centralized.
    _SELECTORS = {
        "job_cards": ".job-card-container",
        "job_title": "h2.jobs-details-top-card__job-title, .job-details-jobs-unified-top-card__job-title",
        "company": ".job-details-jobs-unified-top-card__company-name",
        "description": ".jobs-description",
        "easy_apply_btn": "button.jobs-apply-button",
        "easy_apply_modal": ".artdeco-modal",
        "continue_btn": "button[aria-label='Continue to next step'], button[aria-label='Continue to next step']",
        "review_btn": "button[aria-label='Review your application']",
        "submit_btn": "button[aria-label='Submit application'], button[aria-label='Submit'], button[type='submit']",
        "application_question_labels": ".jobs-easy-apply-form-element label",
        "form_inputs": ".jobs-easy-apply-form-element input, .jobs-easy-apply-form-element select, .jobs-easy-apply-form-element textarea",
        "custom_file_inputs": "input[type='file']",
    }

    def __init__(self, settings: Settings, ai_engine: AIEngine, tracker: Tracker):
        self.settings = settings
        self.ai_engine = ai_engine
        self.tracker = tracker

    # --------------------
    # Search + extraction
    # --------------------

    def _build_search_url(self, role: str, start: int, location: str = "India") -> str:
        # Supports India + remote/no-city by relying on LinkedIn query.
        # Using keywords for role and remote/India hints.
        keywords = role
        # Remote/no-city support: include "remote" keyword as a broad hint.
        # Users can refine via BOT_FILTERS later.
        if "remote" not in keywords.lower():
            keywords = f"{keywords} remote"

        q = keywords.replace(" ", "%20")
        # f_WT=2%2C1 commonly used for "Past month"/employment type filters; keep stable for now.
        # LinkedIn "Past 24 hours" filter
        # f_TPR=r86400 -> 24 hours
        f_tpr = "r86400"

        # If remote_only is enabled, allow remote-friendly results.
        # We keep location in the URL for consistent geo filtering.
        location_param = location
        return (
            "https://www.linkedin.com/jobs/search/"
            f"?keywords={q}&location={location_param}&f_WT=2%2C1&f_TPR={f_tpr}&start={start}"
        )


    def _get_job_id(self, card_el) -> Optional[str]:
        try:
            job_id = card_el.get_attribute("data-job-id")
            return job_id
        except Exception:
            return None

    def search_jobs(self, role: str, filters: Dict) -> Iterable[object]:
        # Interface compatibility: without a Page handle, we cannot scrape.
        # Orchestrator should call LinkedInBot methods via a page-aware private API.
        return []

    def _search_jobs_on_page(
        self,
        page: Page,
        role: str,
        filters: Dict,
        behavior: BehaviorEngine,
        max_pages: int,
    ) -> List[dict]:
        results: List[dict] = []

        for page_num in range(max_pages):
            start = page_num * 25
            search_url = self._build_search_url(role=role, start=start)
            page.goto(
                search_url,
                wait_until="domcontentloaded",
                timeout=90000,
            )
            behavior.random_mouse_move(page)

            behavior.human_delay(4, 8)

            cards = page.locator(self._SELECTORS["job_cards"]).all()
            if not cards:
                break

            for card in cards:
                job_id = self._get_job_id(card)
                if not job_id:
                    continue

                # Duplicate check happens after we have title/company/url.
                # Click card to populate the right details pane.
                try:
                    card.scroll_into_view_if_needed()
                    behavior.random_mouse_move(page)
                    behavior.random_click_delay()
                    card.click()
                    behavior.human_delay(1.5, 3.0)

                    # wait for description pane
                    page.wait_for_selector(self._SELECTORS["description"], timeout=10000)

                    title_el = page.locator(self._SELECTORS["job_title"]).first
                    title = title_el.inner_text().strip() if title_el.is_visible() else ""

                    company_el = page.locator(self._SELECTORS["company"]).first
                    company = company_el.inner_text().strip() if company_el.is_visible() else ""

                    desc_el = page.locator(self._SELECTORS["description"]).first
                    description = desc_el.inner_text().strip() if desc_el.is_visible() else ""

                    job_url = page.url

                    external_apply_url = None
                    try:
                        # Try common offsite/apply links
                        offsite = page.locator('a[href*="offsite"]').first
                        if offsite.is_visible():
                            external_apply_url = offsite.get_attribute("href")
                    except Exception:
                        external_apply_url = None

                    try:
                        if not external_apply_url:
                            btn = page.locator('button:has-text("Apply on company website"), a:has-text("Apply on company website"), a:has-text("Apply")').first
                            if btn.is_visible():
                                external_apply_url = btn.get_attribute("href")
                    except Exception:
                        pass

                    # Fallback heuristic: any visible link that isn't linkedin.com counts as external_apply_url
                    try:
                        if not external_apply_url:
                            links = page.locator('a[href]').all()
                            for a in links:
                                try:
                                    href = a.get_attribute("href")
                                    if not href:
                                        continue
                                    low = href.lower()
                                    if ("linkedin.com" not in low) and ("http" in low):
                                        # Avoid accidental navigation links: prefer apply-ish anchors
                                        if "apply" in low or "offsite" in low or "career" in low:
                                            external_apply_url = href
                                            break
                                except Exception:
                                    continue
                    except Exception:
                        pass

                    if not title or not company:
                        continue


                    signature = self.tracker.signature_for(
                        platform=self.platform,
                        platform_job_id=job_id,
                        title=title,
                        company=company,
                        url=job_url,
                    )

                    if self.tracker.is_processed(signature):
                        continue

                    results.append(
                        {
                            "platform": self.platform,
                            "platform_job_id": job_id,
                            "title": title,
                            "company": company,
                            "job_url": job_url,
                            "description": description,
                            "signature": signature,
                        }
                    )

                except Exception:
                    # Safe skip: continue with next card
                    continue

        return results

    def extract_job_details(self, job: object) -> object:
        # Not used in this phase; extraction is done in _search_jobs_on_page.
        return job

    # --------------------
    # Apply flow
    # --------------------

    def _extract_custom_questions(self, page: Page) -> List[str]:
        labels = page.locator(self._SELECTORS["application_question_labels"]).all()
        questions: List[str] = []
        for lbl in labels:
            try:
                txt = lbl.inner_text().strip()
                if txt:
                    questions.append(txt)
            except Exception:
                continue
        # De-duplicate while preserving order
        seen = set()
        uniq: List[str] = []
        for q in questions:
            if q in seen:
                continue
            seen.add(q)
            uniq.append(q)
        return uniq

    def _fill_and_progress_easy_apply(
        self,
        page: Page,
        behavior: BehaviorEngine,
        application_answers: Dict[str, str],
    ) -> str:
        """Return terminal state: 'SUBMITTED' | 'NEEDS_MANUAL' | 'FAILED'"""
        # Loop bounded by UI steps.
        for _ in range(25):
            try:
                # If submit button exists and visible, stop and allow manual final confirm or click.
                submit_btn = page.locator(self._SELECTORS["submit_btn"]).first
                if submit_btn.is_visible():
                    behavior.random_click_delay(0.4, 1.2)
                    # Click submit if it looks actionable.
                    submit_btn.click()
                    behavior.human_delay(2.0, 4.0)
                    return "SUBMITTED"

                next_btn = page.locator(self._SELECTORS["continue_btn"]).first
                review_btn = page.locator(self._SELECTORS["review_btn"]).first

                # Fill file if asked.
                file_input = page.locator(self._SELECTORS["custom_file_inputs"]).first
                if file_input.is_visible():
                    try:
                        file_input.set_input_files(self.settings.resume_path)
                        behavior.human_delay(1.5, 3.0)
                    except Exception:
                        pass

                # If custom questions appear, fill those we can.
                # (Real field mapping is Phase 6; here we just provide the answers and rely on user/inputs.)
                # We attempt best-effort input filling for text inputs.
                if application_answers:
                    inputs = page.locator(self._SELECTORS["form_inputs"]).all()
                    for inp in inputs:
                        try:
                            # Match by aria-label/name if possible; otherwise skip.
                            name = (inp.get_attribute("aria-label") or inp.get_attribute("name") or "").strip()
                            if not name:
                                continue
                            # crude match
                            for q, a in application_answers.items():
                                if q.lower()[:18] in name.lower() or name.lower() in q.lower():
                                    inp.fill(a)
                                    behavior.human_delay(0.6, 1.2)
                                    break
                        except Exception:
                            continue

                if next_btn.is_visible():
                    behavior.random_click_delay()
                    next_btn.click()
                elif review_btn.is_visible():
                    behavior.random_click_delay()
                    review_btn.click()
                else:
                    # No next/review/submit buttons visible -> likely manual required.
                    return "NEEDS_MANUAL"

                behavior.idle_behavior(page)
                behavior.human_delay(1.5, 3.0)

            except Exception:
                return "FAILED"

        return "FAILED"

    def _apply_single_job(
        self,
        page: Page,
        job: dict,
        behavior: BehaviorEngine,
        max_retries: int = 2,
    ) -> str:
        """Apply to one job. Returns one of: APPLIED | SKIPPED | FAILED | MANUAL_REQUIRED"""

        platform_job_id = job.get("platform_job_id")

        # Print helper: required fields for user visibility.
        def _print_job_ai(decision_payload: dict) -> None:
            title = job.get("title", "")
            company = job.get("company", "")
            ai_decision = decision_payload.get("decision", "")
            match_score = decision_payload.get("match_score", "")
            reason = decision_payload.get("reason", "")
            print(f"[AI] title={title} company={company} AI decision={ai_decision} match_score={match_score} reason={reason}")

        log = logging.getLogger(__name__)


        # Re-check duplicate (defensive)
        title = job["title"]
        company = job["company"]
        url = job["job_url"]
        signature = self.tracker.signature_for(self.platform, platform_job_id, title, company, url)
        if self.tracker.is_processed(signature):
            title = job.get("title", "")
            company = job.get("company", "")
            log.info("Skipped duplicate: title=%s company=%s", title, company)
            print(f"[SKIP] duplicate title={title} company={company}")
            return "SKIPPED"

        # AI decision
        try:
            decision = self.ai_engine.analyze_job(

                job_title=job["title"],
                company=job["company"],
                description=job["description"],
                profile=self.settings.profile,

                policy={},
            )
        except Exception as e:
            # If AI scoring fails (e.g., Ollama timeout), continue safely.
            title = job.get("title", "")
            company = job.get("company", "")
            log.exception(
                "AI engine failed; continuing with safe fallback. title=%s company=%s error=%s",
                title,
                company,
                e,
            )
            print(f"[AI] fallback_due_to_ai_error title={title} company={company}")
            decision = {
                "decision": "APPLY",
                "reason": "ai_scoring_failed_fallback",
                "match_score": 50,
            }


        # Print required fields.
        if isinstance(decision, dict):
            _print_job_ai(decision)

        if decision.get("decision") != "APPLY":
            reason = decision.get("reason", "")
            title = job.get("title", "")
            company = job.get("company", "")
            match_score = decision.get("match_score", "")

            # Logging for each skipped job type.
            if reason == "no_easy_apply":
                log.info("Skipped (no easy apply): title=%s company=%s match_score=%s", title, company, match_score)
                print(f"[SKIP] no_easy_apply title={title} company={company} match_score={match_score}")
            elif reason == "senior_role":
                log.info("Skipped (senior role): title=%s company=%s match_score=%s", title, company, match_score)
                print(f"[SKIP] senior_role title={title} company={company} match_score={match_score}")
            elif reason == "high_experience":
                log.info("Skipped (high experience): title=%s company=%s match_score=%s", title, company, match_score)
                print(f"[SKIP] high_experience title={title} company={company} match_score={match_score}")
            elif reason == "low_match_score":
                log.info("Skipped (low match score): title=%s company=%s match_score=%s", title, company, match_score)
                print(f"[SKIP] low_match_score title={title} company={company} match_score={match_score}")
            else:
                log.info("Skipped (AI decision=%s reason=%s): title=%s company=%s match_score=%s", decision.get("decision"), reason, title, company, match_score)
                print(f"[SKIP] ai_skip reason={reason} title={title} company={company} match_score={match_score}")

            self.tracker.record(signature=signature, platform=self.platform, status="SKIPPED", reason=reason)
            return "SKIPPED"


        # Start Easy Apply
        for attempt in range(max_retries + 1):
            try:
                # The job card has already been clicked in extraction stage; Easy Apply button should be visible now.
                easy_apply_btn = page.locator(self._SELECTORS["easy_apply_btn"]).first
                if not easy_apply_btn.is_visible():
                    title = job.get("title", "")
                    company = job.get("company", "")
                    log.info("Skipped (no easy apply - UI not found): title=%s company=%s", title, company)
                    print(f"[SKIP] no_easy_apply_ui title={title} company={company}")
                    self.tracker.record(signature=signature, platform=self.platform, status="SKIPPED", reason="no_easy_apply")
                    return "SKIPPED"


                behavior.random_click_delay(0.4, 1.2)
                easy_apply_btn.click()
                behavior.human_delay(2.0, 4.0)

                # If custom questions appear, generate answers.
                # We only create answers when questions exist.
                questions = self._extract_custom_questions(page)
                answers: Dict[str, str] = {}
                if questions:
                    # answer each question
                    for q in questions:
                        try:
                            qa = self.ai_engine.analyze_application_questions(question=q, profile={"name": self.settings.profile_name})
                            # analyze_application_questions returns {q: answer}
                            answers.update(qa)
                        except Exception:
                            # keep going; missing answers will be handled manually
                            continue

                result = self._fill_and_progress_easy_apply(page, behavior, answers)

                if result == "SUBMITTED":
                    self.tracker.record(signature=signature, platform=self.platform, status="APPLIED", reason="Easy Apply submitted")
                    return "APPLIED"
                elif result == "NEEDS_MANUAL":
                    self.tracker.record(signature=signature, platform=self.platform, status="MANUAL_REQUIRED", reason="Manual confirmation required")
                    return "MANUAL_REQUIRED"
                else:
                    self.tracker.record(signature=signature, platform=self.platform, status="FAILED", reason="Easy Apply flow failed")
                    return "FAILED"

            except Exception:
                if attempt >= max_retries:
                    self.tracker.record(signature=signature, platform=self.platform, status="FAILED", reason=f"Easy Apply failed (attempt {attempt})")
                    return "FAILED"
                behavior.human_delay(2.0, 4.0)
                continue

        self.tracker.record(signature=signature, platform=self.platform, status="FAILED", reason="Easy Apply exhausted")
        return "FAILED"

    # --------------------
    # PlatformBot interface
    # --------------------

    def apply(self, job: object, application_plan: object, behavior: object) -> object:
        raise NotImplementedError(
            "This LinkedInBot expects page-aware application via _apply_single_job(). "
            "Orchestrator should call the internal methods with a Playwright Page."
        )

    # --------------------
    # Public method for orchestrator (page-aware)
    # --------------------

    def run(
        self,
        page: Page,
        role: str,
        filters: Dict,
        behavior: BehaviorEngine,
        max_pages: Optional[int] = None,
    ) -> Tuple[int, int, int, int]:
        """Run LinkedIn bot for one role.

        Returns counts: (applied, skipped, failed, manual_required)
        """
        max_pages = max_pages if max_pages is not None else int(getattr(self.settings, "max_pages", 3))

        postings = self._search_jobs_on_page(
            page=page,
            role=role,
            filters=filters,
            behavior=behavior,
            max_pages=max_pages,
        )

        applied = skipped = failed = manual = 0

        for job in postings:
            try:
                status = self._apply_single_job(page=page, job=job, behavior=behavior)
                if status == "APPLIED":
                    applied += 1
                elif status == "SKIPPED":
                    skipped += 1
                elif status == "MANUAL_REQUIRED":
                    manual += 1
                else:
                    failed += 1
            except Exception:
                failed += 1
                # Continue next job safely
                continue

        return applied, skipped, failed, manual

