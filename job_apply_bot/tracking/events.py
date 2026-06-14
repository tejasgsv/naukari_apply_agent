"""Job events model (stub)."""

from dataclasses import dataclass
from typing import Any, Dict, Optional
import time


@dataclass(frozen=True)
class JobEvent:
    signature: str
    platform: str
    event_type: str  # FOUND, DECIDED_APPLY, APPLIED, SKIPPED, FAILED, MANUAL_REQUIRED
    timestamp: float
    payload: Optional[Dict[str, Any]] = None

    @staticmethod
    def now(signature: str, platform: str, event_type: str, payload: Optional[Dict[str, Any]] = None) -> "JobEvent":
        return JobEvent(
            signature=signature,
            platform=platform,
            event_type=event_type,
            timestamp=time.time(),
            payload=payload,
        )

