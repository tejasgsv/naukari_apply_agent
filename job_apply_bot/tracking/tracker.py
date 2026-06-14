"""Tracker: duplicate prevention + job lifecycle state machine.

Phase 1 scope:
- determine if job signature already processed
- record statuses into applied_jobs.json and write audit events

Status values are free-form strings, but we standardize expected ones:
- APPLIED
- SKIPPED
- FAILED
- MANUAL_REQUIRED
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from job_apply_bot.config.settings import Settings
from job_apply_bot.tracking.signatures import compute_job_signature
from job_apply_bot.tracking.store import JSONStore


class Tracker:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.store = JSONStore(data_dir="data")

        self._state: Dict[str, Any] = self.store.read_state()

    def signature_for(
        self,
        platform: str,
        platform_job_id: Optional[str],
        title: str,
        company: str,
        url: str,
    ) -> str:
        return compute_job_signature(platform, platform_job_id, title, company, url)

    def is_processed(self, signature: str) -> bool:
        job = self._state.get(signature)
        if not job:
            return False
        # If status exists, consider it processed.
        return "status" in job

    def get(self, signature: str) -> Optional[Dict[str, Any]]:
        return self._state.get(signature)

    def record(
        self,
        signature: str,
        platform: str,
        status: str,
        reason: str = "",
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Update current state and append event.

        Phase 1 expects:
        - applied_jobs.json is the source for is_processed()
        - job_events.jsonl is an audit log
        """
        extra = extra or {}
        self._state[signature] = {
            **self._state.get(signature, {}),
            "platform": platform,
            "status": status,
            "reason": reason,
            **extra,
        }

        self.store.write_state(self._state)

        self.store.append_event(
            {
                "signature": signature,
                "platform": platform,
                "event_type": status,
                "reason": reason,
                "extra": extra,
            }
        )


