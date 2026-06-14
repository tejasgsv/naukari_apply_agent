"""JSON-based storage abstraction.

Phase 1 scope:
- Persist job status state to applied_jobs.json
- Append audit events to job_events.jsonl

This is designed to be swapped to DB later without changing Tracker interface.
"""

from __future__ import annotations

from typing import Any, Dict, Optional
import os
import json
import time


class JSONStore:
    def __init__(
        self,
        data_dir: str,
        applied_jobs_file: str = "applied_jobs.json",
        events_file: str = "job_events.jsonl",
    ):
        self.data_dir = data_dir
        self.applied_jobs_file = os.path.join(data_dir, applied_jobs_file)
        self.events_file = os.path.join(data_dir, events_file)

    def _ensure_dirs(self) -> None:
        os.makedirs(self.data_dir, exist_ok=True)

    def read_state(self) -> Dict[str, Any]:
        """Read applied jobs state.

        Expected shape (v1):
        {
          "<signature>": { platform, company, role, job_link, status, reason, date }
        }
        """
        self._ensure_dirs()
        if not os.path.exists(self.applied_jobs_file):
            return {}
        try:
            with open(self.applied_jobs_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
            return {}
        except json.JSONDecodeError:
            # Corrupted file: treat as empty (safe for phase 1).
            return {}

    def write_state(self, state: Dict[str, Any]) -> None:
        self._ensure_dirs()
        tmp_path = self.applied_jobs_file + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, self.applied_jobs_file)

    def append_event(self, event: Dict[str, Any]) -> None:
        """Append a single event line as JSON to job_events.jsonl."""
        self._ensure_dirs()
        event = dict(event)
        event.setdefault("timestamp", time.time())
        line = json.dumps(event, ensure_ascii=False)
        with open(self.events_file, "a", encoding="utf-8") as f:
            f.write(line + "\n")


