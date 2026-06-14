"""JSON utilities (stub)."""

import json
from typing import Any, Dict


def safe_parse_json(text: str) -> Dict[str, Any]:
    """Parse JSON from text (stub)."""
    return json.loads(text)

