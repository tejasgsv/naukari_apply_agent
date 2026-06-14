"""LinkedIn session bootstrap.

Run to create/refresh `sessions/linkedin_session.json` for storage_state reuse.

Flow:
- Launch browser (Brave if configured, else Chromium)
- Navigate to LinkedIn login page
- Wait for manual login
- Save Playwright storage_state to sessions/linkedin_session.json

Usage:
python -m job_apply_bot.login
"""

from __future__ import annotations

import sys
import traceback
import argparse
from typing import Optional

from job_apply_bot.automation.playwright_manager import PlaywrightManager
from job_apply_bot.automation.session_manager import SessionManager
from job_apply_bot.config.settings import Settings
from job_apply_bot.logging.setup import get_logger



LINKEDIN_LOGIN_URL = "https://www.linkedin.com/login"
NAUKRI_LOGIN_URL = "https://www.naukri.com/nlogin/login"
INDEED_LOGIN_URL = "https://secure.indeed.com/account/login"


def login() -> int:
    logger = get_logger("job_apply_bot.login")

    parser = argparse.ArgumentParser(description="Job apply bot login bootstrap")
    parser.add_argument(
        "--platform",
        choices=["linkedin", "naukri", "indeed"],
        default="linkedin",
        help="Target platform to login bootstrap",
    )
    args = parser.parse_args()

    platform = args.platform

    login_url = {
        "linkedin": LINKEDIN_LOGIN_URL,
        "naukri": NAUKRI_LOGIN_URL,
        "indeed": INDEED_LOGIN_URL,
    }[platform]

    settings = Settings.load()
    playwright_mgr = PlaywrightManager(settings=settings)
    session_mgr = SessionManager(settings=settings)

    handles = None
    try:
        logger.info(f"Launching browser for {platform} login bootstrap...")
        handles = playwright_mgr.create_context(platform=platform, storage_state_path=None)
        page = handles.page

        logger.info(f"Navigating to {platform} login...")
        page.goto(login_url)


        logger.info("Please complete login in the opened browser.")
        logger.info("After you are fully logged in, press Enter here to save the session...")
        input("Press Enter after successful login (or close browser to abort)...")

        # Persist the session
        session_mgr.save_session(context=handles.context, platform=platform)
        logger.info(f"Saved session: {session_mgr.get_session_path(platform)}")

        return 0

    except KeyboardInterrupt:
        logger.warning("Login bootstrap interrupted. No session saved.")
        return 130

    except Exception as e:
        logger.error(f"Login bootstrap failed: {e}")
        logger.debug(traceback.format_exc())
        return 1

    finally:
        try:
            if handles is not None:
                try:
                    handles.context.close()
                except Exception:
                    pass
        finally:
            try:
                playwright_mgr.close()
            except Exception:
                pass


if __name__ == "__main__":
    raise SystemExit(login())

