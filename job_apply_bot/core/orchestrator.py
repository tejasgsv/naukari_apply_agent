"""Application orchestrator (Phase 5B: LinkedIn-only wiring).

Wires together:
- Settings
- JSON tracker + duplicate prevention
- Ollama AI engine
- Human behavior engine
- Playwright browser manager
- Persistent session manager
- LinkedIn bot

Stops after LinkedIn orchestration.
"""

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
from job_apply_bot.ats.router import ATSRouter


def _summarize(start: Dict[str, int], add: Tuple[int, int, int, int]) -> Dict[str, int]:


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
    linkedin_bot = LinkedInBot(settings=settings, ai_engine=ai_engine, tracker=tracker)
    naukri_bot = NaukriBot(settings=settings, ai_engine=ai_engine, tracker=tracker)
    indeed_bot = IndeedBot(settings=settings, ai_engine=ai_engine, tracker=tracker)

    summary = {"applied": 0, "skipped": 0, "failed": 0, "manual_required": 0}

    handles = None

    try:
        # 1) AI availability check is best-effort only.
        # Never abort the whole run in GitHub Actions.
        try:
            # When REMOTE_ONLY=true, AI engine should already be in fallback mode.
            if getattr(settings, "remote_only", False) is not True:
                ai_engine.client.check_ollama_running()
        except Exception as e:
            logger.error(f"AI/Ollama unavailable. Continuing with fallback mode: {e}")

        # 2) Load sessions (best-effort per platform)
        platforms = ["linkedin", "naukri", "indeed"]
        session_paths: Dict[str, str] = {}
        for p in platforms:
            try:
                # If session artifacts don't exist (common in CI), skip platform without failing.
                if session_mgr.session_exists(p):
                    session_paths[p] = session_mgr.get_session_path(p)
                else:
                    logger.warning(
                        "No session artifacts for platform='%s' (expected: %s). Skipping this platform.",
                        p,
                        session_mgr.get_session_path(p),
                    )
            except Exception as e:
                logger.error("Failed to load session path for platform='%s': %s", p, e)


        # 3) Launch browser per platform (shared manager, separate contexts)
        # Using sequential contexts to avoid cross-platform selector/session issues.
        for p in platforms:
            if p not in session_paths:
                continue

            handles = playwright_mgr.create_context(
                platform=p,
                storage_state_path=session_paths[p],
            )


            page = handles.page

            # 4) Loop roles for that platform
            for role in settings.roles:
                logger.info(f"Starting {p.capitalize()} run for role: {role}")
                try:
                    if p == "linkedin":
                        bot = linkedin_bot
                    elif p == "naukri":
                        bot = naukri_bot
                    else:
                        bot = indeed_bot

                    applied, skipped, failed, manual_required = bot.run(
                        page=page,
                        role=role,
                        filters=settings.filters,
                        behavior=behavior,
                        max_pages=settings.max_pages,
                    )
                    summary = _summarize(summary, (applied, skipped, failed, manual_required))
                except Exception as e:
                    logger.exception(
                        "%s failed for role=%s. Continuing next role. Error: %s",
                        p.capitalize(),
                        role,
                        e,
                    )
                    continue

                finally:
                    try:
                        handles.context.close()
                    except Exception:
                        pass

            # ensure page/context closed before moving to next platform
            try:
                handles.context.close()
            except Exception:
                pass


        logger.info(
            "Run summary: "
            f"applied={summary['applied']}, skipped={summary['skipped']}, failed={summary['failed']}, "
            f"manual_required={summary['manual_required']}"
        )


    finally:
        # Always cleanup
        try:
            if handles is not None:
                handles.context.close()
        except Exception:
            pass
        try:
            playwright_mgr.close()
        except Exception:
            pass


