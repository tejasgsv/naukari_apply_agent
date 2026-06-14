"""Ollama client wrapper.

Phase 2 scope:
- health check
- generate responses with JSON-only prompting
- timeout handling
- malformed JSON recovery (best-effort)
- retry support (delegated by caller or internal small retries)

Ollama endpoints used (default):
- GET  {base_url}/api/tags
- POST {base_url}/api/generate
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Dict, Optional

"""HTTP client wrapper for Ollama.

Note:
- We intentionally import `requests` lazily inside methods to avoid hard
  import-time dependency issues in environments where `requests` may be
  misconfigured.
"""



@dataclass(frozen=True)
class OllamaResponse:
    raw_text: str
    usage: Optional[Dict[str, Any]] = None


class OllamaClient:
    def __init__(self, base_url: str, model: str, timeout_sec: float = 60.0):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_sec = timeout_sec

    def _get_requests(self):
        try:
            import requests  # type: ignore

            return requests
        except Exception as e:
            raise RuntimeError(
                "Missing or broken `requests` dependency. Install requests or fix environment."
            ) from e

    def health_check(self) -> bool:
        try:
            requests = self._get_requests()
            resp = requests.get(f"{self.base_url}/api/tags", timeout=self.timeout_sec / 3)
            return resp.status_code == 200
        except Exception:
            return False


    def check_ollama_running(self) -> None:
        if not self.health_check():
            raise RuntimeError(f"Ollama is not reachable at {self.base_url}")

    def _extract_first_json_object(self, text: str) -> str:
        """Best-effort extraction of first JSON object from arbitrary text."""
        start = text.find("{")
        if start == -1:
            raise ValueError("No JSON object found")

        # Find matching closing brace using stack.
        stack = 0
        for i in range(start, len(text)):
            c = text[i]
            if c == "{":
                stack += 1
            elif c == "}":
                stack -= 1
                if stack == 0:
                    return text[start : i + 1]

        raise ValueError("Unterminated JSON object")

    def generate_response(self, prompt: str) -> OllamaResponse:
        requests = self._get_requests()

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }
        resp = requests.post(
            f"{self.base_url}/api/generate",
            json=payload,
            timeout=self.timeout_sec,
        )
        resp.raise_for_status()
        data = resp.json()
        raw_text = data.get("response") or ""
        usage = data.get("eval_count")  # Ollama may not provide token usage consistently
        return OllamaResponse(raw_text=str(raw_text), usage={"eval_count": usage} if usage else None)


    def generate_json(self, prompt: str) -> Dict[str, Any]:
        """Generate JSON from Ollama. Best-effort malformed JSON recovery.

        Caller must ensure the prompt asks for strict JSON.
        """
        self.check_ollama_running()

        raw = self.generate_response(prompt)
        text = raw.raw_text.strip()

        # Common wrappers: ```json ... ```
        if text.startswith("```"):
            # strip first code fence
            text = text.strip("`")
            # remove possible language prefix
            if text.lower().startswith("json"):
                text = text[4:].lstrip()

        # If already JSON, parse directly
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass

        # Otherwise: try to extract first JSON object
        extracted = self._extract_first_json_object(raw.raw_text)
        parsed2 = json.loads(extracted)
        if not isinstance(parsed2, dict):
            raise ValueError("Parsed JSON is not an object")
        return parsed2


