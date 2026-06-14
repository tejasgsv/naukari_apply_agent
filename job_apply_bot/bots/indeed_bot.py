"""Indeed bot (Playwright-based, Phase 7 implementation).

Best-effort implementation using resilient selector chains.

Key behaviors:
- Filter jobs by last 24 hours only (best-effort via visible text/URL heuristics)
- Duplicate prevention via Tracker signatures
- AI decision via AIEngine and strict APPLY threshold >= 55
- Easy-apply detection best-effort and graceful skipping when not available
- Prints/logs skip reasons exactly like LinkedInBot.
"""

from __future__ import annotations

import logging
import re
from typing import Dict, Iterable, List, Optional, Tuple

from playwright.sync_api import Page

from job_apply_bot.ai.engine import AIEngine
from job_apply_bot.automation.behavior_engine import BehaviorEngine
from job_apply_bot.bots.base import PlatformBot
from job_apply_bot.config.settings import Settings
from job_apply_bot.tracking.tracker import Tracker


class IndeedBot(PlatformBot):
    platform = "indeed"

    _CARD_SELECTORS = [
        "a[data-tn-element='jobTitle']",
        "div.slider_container",
        "div.jobsearch-SerpJobCard",
        "a[href*='/rc/clk']",
        "a[href*='viewjob']",
    ]

    def __init__(self, settings: Settings, ai_engine: AIEngine, tracker: Tracker):
        self.settings = settings
        self.ai_engine = ai_engine
        self.tracker = tracker

    def search_jobs(self, role: str, filters: Dict) -> Iterable[object]:
        return []

    def extract_job_details(self, job: object) -> object:
        return job

    # --------------------
    # Heuristics
    # --------------------

    def _build_search_url(self, role: str, start: int) -> str:
        # Indeed often uses 'start=' offset and 'q=' for query.
        keywords = role.replace(" ", "+")
        return (
            "https://www.indeed.com/jobs?q="
            f"{keywords}&l={self.settings.country}&start={start}"
        )

    def _is_recent_24h(self, card_el) -> bool:
        try:
            text = (card_el.inner_text() or "").lower()
        except Exception:
            text = ""

        patterns = [
            r"\bjust now\b",
            r"\b(\d+\s*(min|mins|minutes))\b",
            r"\b24\s*hours\b",
            r"\blast\s*24\s*hours\b",
            r"\b1\s*day\b",
            r"\btoday\b",
        ]
        return any(re.search(p, text) for p in patterns)

    def _print_job_ai(self, job: dict, decision_payload: dict) -> None:
        title = job.get("title", "")
        company = job.get("company", "")
        ai_decision = decision_payload.get("decision", "")
        match_score = decision_payload.get("match_score", "")
        reason = decision_payload.get("reason", "")
        print(f"[AI] title={title} company={company} AI decision={ai_decision} match_score={match_score} reason={reason}")

    def _ai_decide(self, job: dict) -> Dict:
        return self.ai_engine.analyze_job(
            job_title=job.get("title", ""),
            company=job.get("company", ""),
            description=job.get("description", ""),
            profile=self.settings.profile,
            policy={},
        )

    def _apply_best_effort(self, page: Page, job: dict, behavior: BehaviorEngine) -> str:
        # Indeed has Apply/Quick Apply buttons.
        try:
            behavior.slow_scroll(page)
            candidates = [
                page.locator("text=/quick apply/i"),
                page.locator("button:has-text('Quick Apply')"),
                page.locator("button:has-text('Apply')"),
                page.locator("a:has-text('Apply')"),
            ]

            for loc in candidates:
                try:
                    if loc.first.is_visible():
                        behavior.random_click_delay()
                        loc.first.click()
                        behavior.human_delay(2.0, 4.0)
                        return "MANUAL_REQUIRED"  # best-effort; form flow may require further manual steps
                except Exception:
                    continue
        except Exception:
            pass

        return "NEEDS_MANUAL"

    # --------------------
    # Main entry
    # --------------------

    def run(
        self,
        page: Page,
        role: str,
        filters: Dict,
        behavior: BehaviorEngine,
        max_pages: Optional[int] = None,
    ) -> Tuple[int, int, int, int]:
        max_pages = max_pages if max_pages is not None else int(getattr(self.settings, "max_pages", 3))

        applied = skipped = failed = manual = 0

        postings: List[dict] = []
        for page_num in range(max_pages):
            start = page_num * 10
            url = self._build_search_url(role=role, start=start)
            try:
                page.goto(url, timeout=30000)
            except Exception:
                continue

            behavior.random_mouse_move(page)
            behavior.human_delay(2, 4)

            card_els = []
            for sel in self._CARD_SELECTORS:
                try:
                    locs = page.locator(sel).all()
                    if locs:
                        card_els.extend(locs)
                except Exception:
                    continue

            seen_urls = set()
            for el in card_els:
                try:
                    href = el.get_attribute("href") or ""
                except Exception:
                    href = ""
                if href and href in seen_urls:
                    continue
                if href:
                    seen_urls.add(href)

                if not self._is_recent_24h(el):
                    continue

                try:
                    txt = (el.inner_text() or "").strip()
                except Exception:
                    txt = ""
                if not txt:
                    continue

                parts = [p.strip() for p in txt.split("\n") if p.strip()]
                title = parts[0] if parts else txt[:80]
                company = parts[1] if len(parts) > 1 else ""
                description = txt

                postings.append(
                    {
                        "platform": self.platform,
                        "platform_job_id": href if href else title,
                        "title": title,
                        "company": company,
                        "job_url": href or page.url,
                        "description": description,
                    }
                )

            if len(postings) > 50:
                break

        for job in postings:
            try:
                title = job.get("title", "")
                company = job.get("company", "")
                job_url = job.get("job_url", "")
                platform_job_id = job.get("platform_job_id")

                signature = self.tracker.signature_for(
                    platform=self.platform,
                    platform_job_id=platform_job_id,
                    title=title,
                    company=company,
                    url=job_url,
                )

                if self.tracker.is_processed(signature):
                    print(f"[SKIP] duplicate title={title} company={company}")
                    logging.getLogger(__name__).info("Skipped duplicate: title=%s company=%s", title, company)
                    skipped += 1
                    continue

                decision = self._ai_decide(job)
                if isinstance(decision, dict):
                    self._print_job_ai(job, decision)

                if decision.get("decision") != "APPLY":
                    reason = decision.get("reason", "")
                    match_score = decision.get("match_score", "")
                    print(f"[SKIP] {reason or 'ai_skip'} title={title} company={company} match_score={match_score}")
                    logging.getLogger(__name__).info(
                        "Skipped (AI): title=%s company=%s reason=%s match_score=%s",
                        title,
                        company,
                        reason,
                        match_score,
                    )
                    self.tracker.record(
                        signature=signature,
                        platform=self.platform,
                        status="SKIPPED",
                        reason=reason,
                    )
                    skipped += 1
                    continue

                try:
                    if job_url:
                        page.goto(job_url)
                except Exception:
                    pass

                status = self._apply_best_effort(page, job, behavior)

                if status == "APPLIED":
                    self.tracker.record(signature=signature, platform=self.platform, status="APPLIED", reason="Applied")
                    applied += 1
                elif status in ("MANUAL_REQUIRED", "NEEDS_MANUAL"):
                    self.tracker.record(
                        signature=signature,
                        platform=self.platform,
                        status="MANUAL_REQUIRED",
                        reason="Manual confirmation required",
                    )
                    manual += 1
                else:
                    self.tracker.record(signature=signature, platform=self.platform, status="FAILED", reason="Apply failed")
                    failed += 1

            except Exception:
                failed += 1
                continue

        return applied, skipped, failed, manual

    def apply(self, job: object, application_plan: object, behavior: object) -> object:
        raise NotImplementedError(
            "This IndeedBot expects page-aware application via run(page, ...)."
        )

