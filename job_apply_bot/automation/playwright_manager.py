"""Playwright lifecycle manager (Phase 4).

Provides reusable browser/context/page creation with:
- Brave support (fallback to Chromium)
- configurable headless
- storage_state reuse
- anti-detection browser args (baseline)
- random viewport sizes
- user-agent rotation (optional via settings)
- safe cleanup

This is intentionally a thin wrapper. Platform bots use `page`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence
import os
import random

from playwright.sync_api import sync_playwright


@dataclass
class BrowserHandles:
    context: object
    page: object
    browser: object


class PlaywrightManager:
    def __init__(self, settings: object):
        self.settings = settings
        self._pw = None
        self._browser = None

    def _browser_executable(self) -> Optional[str]:
        brave_path = getattr(self.settings, "browser_executable_path", None)
        if brave_path and os.path.exists(brave_path):
            return brave_path
        return None

    def _viewport(self) -> dict:
        # Simple randomized viewport sizes to reduce fingerprinting.
        candidates = [
            {"width": 1366, "height": 768},
            {"width": 1440, "height": 900},
            {"width": 1536, "height": 864},
            {"width": 1600, "height": 900},
        ]
        return random.choice(candidates)

    def _user_agent_rotation(self) -> Optional[str]:
        # Optional: BOT_USER_AGENTS="ua1,ua2,...".
        agents_raw = os.getenv("BOT_USER_AGENTS")
        if not agents_raw:
            return None
        agents: Sequence[str] = [a.strip() for a in agents_raw.split(",") if a.strip()]
        if not agents:
            return None
        return random.choice(list(agents))

    def _anti_detection_args(self) -> list[str]:
        # Baseline args; platform-specific adjustments can be added later.
        return [
            "--disable-blink-features=AutomationControlled",
            "--disable-infobars",
            "--no-sandbox",
            "--disable-dev-shm-usage",
        ]

    def launch_browser(self) -> object:
        if self._browser is not None:
            return self._browser

        headless = bool(getattr(self.settings, "headless", False))
        brave_exe = self._browser_executable()

        self._pw = sync_playwright().start()
        launch_kwargs = {
            "headless": headless,
            "args": self._anti_detection_args(),
        }
        if brave_exe:
            # Brave installed at user path; Playwright launch uses chromium with an explicit executable.
            launch_kwargs["executable_path"] = brave_exe

        self._browser = self._pw.chromium.launch(**launch_kwargs)
        return self._browser

    def create_context(self, platform: str, storage_state_path: Optional[str] = None) -> BrowserHandles:
        browser = self.launch_browser()

        viewport = self._viewport()
        user_agent = self._user_agent_rotation()

        context_kwargs = {
            "viewport": viewport,
            "locale": "en-IN",
        }
        if user_agent:
            context_kwargs["user_agent"] = user_agent

        if storage_state_path:
            context_kwargs["storage_state"] = storage_state_path

        context = browser.new_context(**context_kwargs)
        page = context.new_page()

        # platform param kept for future per-platform context tweaks.
        _ = platform

        return BrowserHandles(context=context, page=page, browser=browser)

    def close(self) -> None:
        try:
            if self._browser is not None:
                self._browser.close()
        finally:
            self._browser = None
            if self._pw is not None:
                try:
                    self._pw.stop()
                except Exception:
                    pass
                self._pw = None


