"""Job Application Bot - single CLI entrypoint.

Phase 5C scope:
- Load settings
- Initialize logging
- Run LinkedIn-only orchestration
- Handle KeyboardInterrupt / unexpected exceptions with readable messages
"""

from __future__ import annotations

import logging
import sys
from typing import Optional

from job_apply_bot.core.orchestrator import run
from job_apply_bot.config.settings import Settings
from job_apply_bot.logging.setup import get_logger


def main(argv: Optional[list[str]] = None) -> int:
    _ = argv  # reserved for future CLI flags (dry-run, etc.)

    logger = get_logger()

    logger.info("==============================================")
    logger.info(" Job Application Bot (LinkedIn-only) ")
    logger.info("==============================================")
    try:
        settings = Settings.load()
        run(settings)
        logger.info("Completed run.")
        return 0
    except KeyboardInterrupt:
        logger.warning("Interrupted by user (Ctrl+C). Shutting down safely...")
        return 130
    except Exception:
        logger.exception("Unexpected error. Exiting with failure.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))


