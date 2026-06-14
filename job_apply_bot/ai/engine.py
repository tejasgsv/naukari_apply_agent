"""Local AI engine using Ollama only."""

from __future__ import annotations

from typing import Any, Dict

from job_apply_bot.ai.ollama_client import OllamaClient
from job_apply_bot.config.settings import Settings
from job_apply_bot.ai.schema import validate_answers


class AIEngine:
    def __init__(self, settings: Settings):
        self.settings = settings

        # Fixed remote mode logic
        self.remote_only = bool(
            getattr(settings, "remote_only", False)
        )

        # Debug logs
        print("=" * 50)
        print("AI ENGINE STARTED")
        print("REMOTE_ONLY =", self.remote_only)
        print("OLLAMA MODEL =", settings.ollama_model)
        print("OLLAMA URL =", settings.ollama_base_url)
        print("=" * 50)

        if self.remote_only:
            self.client = None
        else:
            self.client = OllamaClient(
                settings.ollama_base_url,
                settings.ollama_model
            )

    def _prompt_analyze_job(
        self,
        profile: Dict[str, Any],
        job_title: str,
        company: str,
        description: str,
        policy: Dict[str, Any]
    ) -> str:

        return f"""
You are an expert recruiter assistant.

Return STRICT JSON only with this schema:
{{
  "decision": "APPLY" or "SKIP",
  "match_score": <number 0-100>,
  "reason": "<string>",
  "skills_matched": ["<string>"],
  "skills_missing": ["<string>"],
  "custom_pitch": "<string>"
}}

Candidate profile:
{profile}

Job:
Title: {job_title}
Company: {company}
Description:
{description}

Policy constraints:
{policy}

Rules:
- decision is APPLY only if match is high enough.
- skills_* must be short phrases.
- custom_pitch max 3 lines.
"""

    def analyze_job(
        self,
        job_title: str,
        company: str,
        description: str,
        profile: Dict[str, Any],
        policy: Dict[str, Any],
    ) -> Dict[str, Any]:

        title_l = (job_title or "").lower()
        desc_l = (description or "").lower()

        senior_keywords = {
            "senior",
            "lead",
            "manager",
            "architect",
            "principal",
            "head of",
            "director",
            "staff",
        }

        # Reject senior roles
        if any(k in title_l or k in desc_l for k in senior_keywords):
            result = {
                "decision": "SKIP",
                "reason": "senior_role",
                "match_score": 0,
            }

            print(f"[AI] {job_title} | {company} -> {result}")
            return result

        import re

        max_required = int(
            getattr(self.settings, "max_required_years", 3)
        )

        years_found = []

        for m in re.finditer(
            r"(\d+(?:\.\d+)?)\s*(?:\+|plus)?\s*\b(?:years|yrs)\b",
            title_l + " " + desc_l,
        ):
            try:
                years_found.append(float(m.group(1)))
            except Exception:
                pass

        # Reject high experience jobs
        if years_found and max(years_found) > max_required:
            result = {
                "decision": "SKIP",
                "reason": "high_experience",
                "match_score": 0,
            }

            print(f"[AI] {job_title} | {company} -> {result}")
            return result

        # Fallback mode if remote_only enabled
        if self.client is None:
            result = {
                "decision": "APPLY",
                "reason": "remote fallback mode",
                "match_score": 75,
                "skills_matched": [],
                "skills_missing": [],
                "custom_pitch": "",
            }

            print(f"[AI] {job_title} | {company} -> {result}")
            return result

        # Ollama analysis
        prompt = self._prompt_analyze_job(
            profile=profile,
            job_title=job_title,
            company=company,
            description=description,
            policy=policy,
        )

        payload = self.client.generate_json(prompt)

        match_score = payload.get("match_score", 0)

        try:
            match_score_i = int(float(match_score))
        except Exception:
            match_score_i = 0

        # Reject low score
        if match_score_i < 55:
            result = {
                "decision": "SKIP",
                "reason": "low_match_score",
                "match_score": match_score_i,
            }

            print(f"[AI] {job_title} | {company} -> {result}")
            return result

        decision = payload.get("decision", "SKIP")

        if decision == "APPLY":
            result = {
                "decision": "APPLY",
                "match_score": match_score_i,
                "reason": payload.get("reason", ""),
                "skills_matched": payload.get("skills_matched", []),
                "skills_missing": payload.get("skills_missing", []),
                "custom_pitch": payload.get("custom_pitch", ""),
            }

            print(f"[AI] {job_title} | {company} -> {result}")
            return result

        result = {
            "decision": "SKIP",
            "reason": payload.get("reason", "not_matched"),
            "match_score": match_score_i,
        }

        print(f"[AI] {job_title} | {company} -> {result}")
        return result

    def _prompt_answer_questions(
        self,
        profile: Dict[str, Any],
        question: str
    ) -> str:

        return f"""
You are an expert at job applications.

Return STRICT JSON only:
{{"answer": "<string>"}}

Candidate profile:
{profile}

Question:
{question}

Guidelines:
- Answer directly and truthfully.
- Keep concise and professional.
"""

    def analyze_application_questions(
        self,
        question: str,
        profile: Dict[str, Any]
    ) -> Dict[str, str]:

        if self.client is None:
            return validate_answers({
                question: ""
            })

        prompt = self._prompt_answer_questions(
            profile=profile,
            question=question
        )

        payload = self.client.generate_json(prompt)

        if not isinstance(payload, dict) or "answer" not in payload:
            raise ValueError("Invalid answers payload")

        return validate_answers({
            question: payload.get("answer", "")
        })