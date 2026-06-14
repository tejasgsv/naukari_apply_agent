"""AI output schemas and validation.

Phase 2 scope:
- Validate and normalize the strict JSON outputs expected by local Ollama.
- Do not depend on external schema libraries.

Expected outputs:
1) job decision:
{
  "decision": "APPLY" | "SKIP",
  "match_score": number,
  "reason": string,
  "skills_matched": [string, ...],
  "skills_missing": [string, ...],
  "custom_pitch": string
}

2) answers:
{
  "<question>": "<answer>",
  ...
}
"""

from __future__ import annotations

from typing import Any, Dict, List


def _as_int(x: Any, default: int = 0) -> int:
    try:
        # allow float strings etc.
        return int(float(x))
    except Exception:
        return default


def validate_job_decision(payload: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be an object")

    decision = payload.get("decision")
    if decision not in {"APPLY", "SKIP"}:
        raise ValueError("decision must be APPLY or SKIP")

    match_score = _as_int(payload.get("match_score"), default=0)
    match_score = max(0, min(100, match_score))

    reason = payload.get("reason")
    if not isinstance(reason, str):
        reason = str(reason) if reason is not None else ""

    skills_matched = payload.get("skills_matched", [])
    if not isinstance(skills_matched, list):
        skills_matched = []
    skills_matched = [str(s) for s in skills_matched if s is not None]

    skills_missing = payload.get("skills_missing", [])
    if not isinstance(skills_missing, list):
        skills_missing = []
    skills_missing = [str(s) for s in skills_missing if s is not None]

    custom_pitch = payload.get("custom_pitch")
    if not isinstance(custom_pitch, str):
        custom_pitch = str(custom_pitch) if custom_pitch is not None else ""

    return {
        "decision": decision,
        "match_score": match_score,
        "reason": reason,
        "skills_matched": skills_matched,
        "skills_missing": skills_missing,
        "custom_pitch": custom_pitch,
    }


def validate_answers(payload: Dict[str, Any]) -> Dict[str, str]:
    if not isinstance(payload, dict):
        raise ValueError("answers payload must be an object")

    out: Dict[str, str] = {}
    for k, v in payload.items():
        # questions must be strings; values become strings
        if k is None:
            continue
        out[str(k)] = "" if v is None else str(v)

    return out


