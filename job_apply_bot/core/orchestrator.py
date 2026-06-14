"""Application orchestrator (Phase 5B: LinkedIn-only wiring)."""

from __future__ import annotations

from typing import Dict, Tuple

from job_apply_bot.ai.engine import AIEngine
from job_apply_bot.automation.behavior_engine import BehaviorEngine
from job_apply_bot.automation.playwright_manager import PlaywrightManager
from job_apply_bot.automation.session_manager import SessionManager

from job_apply_bot.bots.linkedin_bot import LinkedInBot
from job_apply_bot.bots.naukri_bot import NaukriBot
from job_apply_bot.bots.indeed_bot import IndeedBot

from job_apply_bot.config.settings import Settings
from job_apply_bot.logging.setup import get_logger
from job_apply_bot.tracking.tracker import Tracker


def _summarize(
    start: Dict[str, int],
    add: Tuple[int, int, int, int]
) -> Dict[str, int]:
    applied, skipped, failed, manual = add

    start["applied"] += applied
    start["skipped"] += skipped
    start["failed"] += failed
    start["manual_required"] += manual

    return start


def run(settings: Settings, continuous: bool = False) -> None:
    logger = get_logger()

    playwright_mgr = PlaywrightManager(settings=settings)
    session_mgr = SessionManager(settings=settings)

    tracker = Tracker(settings=settings)
    ai_engine = AIEngine(settings=settings)
    behavior = BehaviorEngine()

    linkedin_bot = LinkedInBot(
        settings=settings,
        ai_engine=ai_engine,
        tracker=tracker
    )

    naukri_bot = NaukriBot(
        settings=settings,
        ai_engine=ai_engine,
        tracker=tracker
    )

    indeed_bot = IndeedBot(
        settings=settings,
        ai_engine=ai_engine,
        tracker=tracker
    )

    summary = {
        "applied": 0,
        "skipped": 0,
        "failed": 0,
        "manual_required": 0
    }

    try:
        # Ollama check
        try:
            if not settings.remote_only and ai_engine.client:
                ai_engine.client.check_ollama_running()
        except Exception as e:
            logger.error(
                f"AI/Ollama unavailable. Continuing with fallback mode: {e}"
            )

        # Load sessions
        platforms = ["linkedin", "naukri", "indeed"]
        session_paths: Dict[str, str] = {}

        for p in platforms:
            try:
                if session_mgr.session_exists(p):
                    session_paths[p] = session_mgr.get_session_path(p)
                else:
                    logger.warning(
                        "No session found for platform='%s'. Skipping.",
                        p
                    )
            except Exception as e:
                logger.error(
                    "Failed loading session for platform='%s': %s",
                    p,
                    e
                )

        # Run platform by platform
        for p in platforms:
            if p not in session_paths:
                continue

            handles = playwright_mgr.create_context(
                platform=p,
                storage_state_path=session_paths[p]
            )

            page = handles.page

            # Select bot
            if p == "linkedin":
                bot = linkedin_bot
            elif p == "naukri":
                bot = naukri_bot
            else:
                bot = indeed_bot

            # Run all roles on same context
            for role in settings.roles:
                logger.info(
                    f"Starting {p.capitalize()} run for role: {role}"
                )

                try:
                    applied, skipped, failed, manual_required = bot.run(
                        page=page,
                        role=role,
                        filters=settings.filters,
                        behavior=behavior,
                        max_pages=settings.max_pages
                    )

                    summary = _summarize(
                        summary,
                        (
                            applied,
                            skipped,
                            failed,
                            manual_required
                        )
                    )

                except Exception as e:
                    logger.exception(
                        "%s failed for role=%s. Continuing next role. Error: %s",
                        p.capitalize(),
                        role,
                        e
                    )
                    continue

            # Close context AFTER all roles completed
            try:
                handles.context.close()
            except Exception:
                pass

        logger.info(
            "Run summary: "
            f"applied={summary['applied']}, "
            f"skipped={summary['skipped']}, "
            f"failed={summary['failed']}, "
            f"manual_required={summary['manual_required']}"
        )

    finally:
        # Only close browser manager
        try:
            playwright_mgr.close()
        except Exception:
            pass