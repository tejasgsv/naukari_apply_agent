"""Retry mechanism (stub)."""

from typing import Callable, TypeVar
import time

T = TypeVar("T")


def retry(fn: Callable[[], T], attempts: int, backoff_sec: float = 1.0) -> T:
    last_err: Exception | None = None
    for i in range(attempts):
        try:
            return fn()
        except Exception as e:  # noqa: BLE001
            last_err = e
            time.sleep(backoff_sec * (i + 1))
    assert last_err is not None
    raise last_err

