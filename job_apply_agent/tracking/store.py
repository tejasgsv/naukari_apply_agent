"""JSON-based storage abstraction (stub)."""

from typing import Dict, Any, Iterable, Optional


class JSONStore:
    def __init__(self, data_dir: str):
        self.data_dir = data_dir

    def read_state(self) -> Dict[str, Any]:
        # TODO: implement reading applied_jobs.json
        return {}

    def write_state(self, state: Dict[str, Any]) -> None:
        # TODO: implement writing applied_jobs.json
        return

    def append_event(self, event: Dict[str, Any]) -> None:
        # TODO: implement writing job_events.jsonl
        return

