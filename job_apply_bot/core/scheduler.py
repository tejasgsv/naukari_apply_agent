"""Hourly scheduler.

Phase 6 requirements:
- Infinite hourly loop
- Sleep using settings.check_interval_minutes
- Call orchestrator.run(settings)
"""

from __future__ import annotations

import time
from typing import Optional

from job_apply_bot.config.settings import Settings


def run_scheduler(settings: Settings) -> None:
    # Infinite loop
    while True:
        from job_apply_bot.core.orchestrator import run

        run(settings)
        time.sleep(int(getattr(settings, "check_interval_minutes", 60)) * 60)


