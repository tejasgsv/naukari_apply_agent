"""Logging setup.

Guarantees:
- log file(s) are created under ./logs/
- console logging remains enabled
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Optional


def get_logger(name: str = "job_apply_bot", log_file: Optional[str] = None) -> logging.Logger:
    logger = logging.getLogger(name)

    # If handlers already exist, don't duplicate handlers.
    if getattr(logger, "_bbai_configured", False):
        return logger

    logger.setLevel(logging.INFO)

    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s - %(message)s")

    # Console
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    # File
    logs_dir = os.path.join(os.getcwd(), "logs")
    os.makedirs(logs_dir, exist_ok=True)

    if log_file is None:
        # Stable filename per run date.
        log_file = os.path.join(logs_dir, f"job_apply_bot_{datetime.utcnow().strftime('%Y-%m-%d')}.log")
    else:
        # If caller passes a relative path, keep it relative to logs_dir.
        if not os.path.isabs(log_file):
            log_file = os.path.join(logs_dir, log_file)

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    logger._bbai_configured = True  # type: ignore[attr-defined]
    return logger


