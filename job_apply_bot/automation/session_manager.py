"""Session management (Phase 4).

This module provides persistent Playwright `storage_state` JSON per platform.

Responsibilities:
- save_session(context, platform)
- load_session(browser, platform) (returns storage_state_path)
- session_exists(platform)
- get_session_path(platform)
- ensure_session_or_raise(platform) for later bots/orchestrator wiring

Note:
Detection of logged-out redirects is left for Phase 4+1 when we integrate
platform-specific login checks.
"""

from __future__ import annotations

import os
from typing import Optional


class SessionManager:
    def __init__(self, settings: object):
        self.settings = settings

    def get_session_path(self, platform: str) -> str:
        # sessions/<platform>_session.json
        return os.path.join(
            getattr(self.settings, "sessions_dir", "sessions"),
            f"{platform}_session.json",
        )

    def session_exists(self, platform: str) -> bool:
        return os.path.exists(self.get_session_path(platform))

    def save_session(self, context: object, platform: str) -> None:
        """Persist storage state for a given Playwright context."""
        path = self.get_session_path(platform)
        os.makedirs(os.path.dirname(path), exist_ok=True)

        # Playwright contexts provide `storage_state(path=...)`.
        storage_state_fn = getattr(context, "storage_state", None)
        if not callable(storage_state_fn):
            raise TypeError("context.storage_state(...) is not available")

        storage_state_fn(path=path)

    def load_session(self, browser: object, platform: str) -> Optional[str]:
        """Return storage_state_path if it exists.

        The `browser` parameter exists for future enhancements (e.g. reloading,
        multi-context reuse). For now we only provide the path.
        """
        _ = browser
        if self.session_exists(platform):
            return self.get_session_path(platform)
        return None

    def ensure_session_or_raise(self, platform: str) -> str:
        """Return existing session path or raise instructing manual login."""
        path = self.get_session_path(platform)
        if not self.session_exists(platform):
            raise FileNotFoundError(
                f"No session state for platform='{platform}'. Expected: {path}. "
                "Run login flow to create it first."
            )
        return path


