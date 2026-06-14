"""ATS router.

Detect ATS vendor by external apply URL and route to the right handler.

Detection rules:
- myworkdayjobs -> workday
- greenhouse.io -> greenhouse
- lever.co -> lever
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from job_apply_bot.ats.workday import WorkdayATS
from job_apply_bot.ats.greenhouse import GreenhouseATS
from job_apply_bot.ats.lever import LeverATS


@dataclass(frozen=True)
class ATSRoute:
    platform: str
    handler: object


class ATSRouter:
    @staticmethod
    def detect(url: str) -> Optional[str]:
        if not url:
            return None
        u = url.lower()
        if "myworkdayjobs" in u:
            return "workday"
        if "greenhouse.io" in u:
            return "greenhouse"
        if "lever.co" in u:
            return "lever"
        return None

    @staticmethod
    def route(*, page, url: str, settings) -> Optional[ATSRoute]:
        platform = ATSRouter.detect(url)
        if platform == "workday":
            return ATSRoute(platform=platform, handler=WorkdayATS(page=page, settings=settings))
        if platform == "greenhouse":
            return ATSRoute(platform=platform, handler=GreenhouseATS(page=page, settings=settings))
        if platform == "lever":
            return ATSRoute(platform=platform, handler=LeverATS(page=page, settings=settings))
        return None

