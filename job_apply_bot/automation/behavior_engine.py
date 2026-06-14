"""Human-like behavior engine (anti-detection).

Phase 3 scope:
- reusable across all platform bots
- randomized delays/scroll/mouse
- anti-pattern repetition reduction (bounded action recipes)
- safe fallbacks if Playwright page is unavailable

This module should only implement interaction primitives; platform bots decide *where*
(and *how often*) they are used.
"""

from __future__ import annotations

import random
import time
from typing import Optional

from job_apply_bot.utils.timing import jitter, random_interval, reading_time


class BehaviorEngine:
    def __init__(self, seed: Optional[int] = None, max_scroll_chunks: int = 5):
        self._rng = random.Random(seed)
        self._max_scroll_chunks = max_scroll_chunks
        self._last_mouse_moves: list[tuple[int, int]] = []

    def human_delay(self, min_sec: float = 0.5, max_sec: float = 2.5) -> None:
        """Pause execution for a random bounded amount of time."""
        sec = random_interval(min_sec, max_sec)
        sec = jitter(sec, jitter_ratio=0.2)
        time.sleep(sec)

    # Backwards compatible alias
    delay = human_delay

    def random_mouse_move(self, page: object) -> None:
        """Simulate human mouse cursor movement.

        Safe fallback if page doesn't support Playwright API.
        """
        if page is None:
            return

        mouse = getattr(page, "mouse", None)
        viewport_size = getattr(page, "viewport_size", None)

        if mouse is None or not hasattr(mouse, "move"):
            return

        width = 1920
        height = 1080
        if isinstance(viewport_size, dict):
            width = int(viewport_size.get("width", width) or width)
            height = int(viewport_size.get("height", height) or height)

        # anti-pattern repetition: avoid exact same coordinates too often
        for _ in range(5):
            x = self._rng.randint(0, max(1, width - 1))
            y = self._rng.randint(0, max(1, height - 1))
            if (x, y) in self._last_mouse_moves:
                continue

            mouse.move(x, y)
            self._last_mouse_moves.append((x, y))
            self._last_mouse_moves = self._last_mouse_moves[-10:]
            break

    def slow_scroll(self, page: object, content_length: int | None = None) -> None:
        """Scroll down in chunks with random pauses."""
        if page is None:
            return

        evaluate = getattr(page, "evaluate", None)
        if not callable(evaluate):
            return

        chunks = self._rng.randint(2, self._max_scroll_chunks)
        for i in range(chunks):
            # scroll roughly half viewport at a time
            evaluate("window.scrollBy(0, window.innerHeight * 0.5);")
            # pauses between chunks
            pause_min = 0.6
            pause_max = 1.8
            self.human_delay(pause_min, pause_max)

            if content_length is not None and i == 0:
                # reading simulation after initial content appears
                self.simulate_reading(page, content_length)

    def simulate_reading(self, page: object, content_length: int) -> None:
        """Simulate a human reading time estimate.

        If page is unavailable, it degrades to a delay only.
        """
        sec = reading_time(content_length)
        # add slight variation
        sec = jitter(sec, jitter_ratio=0.15)
        # occasional mouse move while reading
        if page is not None and self._rng.random() < 0.35:
            self.random_mouse_move(page)
        time.sleep(sec)

    def random_click_delay(self, min_sec: float = 0.3, max_sec: float = 1.0) -> None:
        """Small pause before clicking to look more natural."""
        self.human_delay(min_sec, max_sec)

    def idle_behavior(self, page: object) -> None:
        """Occasional micro-interactions during idle time."""
        if page is None:
            return

        # low probability to avoid repetitive patterns
        if self._rng.random() < 0.25:
            self.random_mouse_move(page)
            self.human_delay(0.4, 1.2)

    # Backwards compatible aliases (from requirements / older stub)
    scroll_recipe = slow_scroll
    pointer_recipe = random_mouse_move


