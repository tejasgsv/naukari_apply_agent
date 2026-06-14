"""Local AI engine using Ollama only.

Phase 2 scope:
- analyze job: return strict JSON decision
- answer application questions: return strict JSON answers mapping
- uses prompts from config/prompts.py (existing stub; will be improved in later phases)
- timeout/malformed JSON recovery lives in OllamaClient
- if Ollama fails: raise to caller (bot will skip gracefully per orchestration rules)
"""

from __future__ import annotations

from typing import Any, Dict, List

from job_apply_bot.ai.ollama_client import OllamaClient
from job_apply_bot.config.settings import Settings
from job_apply_bot.ai.schema import validate_answers



class AIEngine:
    def __init__(self, settings: Settings):
        self.settings = settings

        # GitHub Actions compatibility: when REMOTE_ONLY=true we must not require
        # local Ollama. Use fallback logic instead.
        self.remote_only = bool(getattr(settings, "remote_only", False)) is True

        if self.remote_only:
            self.client = None
        else:
            self.client = OllamaClient(settings.ollama_base_url, settings.ollama_model)


    def _prompt_analyze_job(self, profile: Dict[str, Any], job_title: str, company: str, description: str, policy: Dict[str, Any]) -> str:
        # NOTE: config/prompts.py is still a stub; keep prompt inline for now.
        return f"""You are an expert recruiter assistant.

Return STRICT JSON only with this schema:
{{
  \"decision\": \"APPLY\" or \"SKIP\",
  \"match_score\": <number 0-100>,
  \"reason\": <string>,
  \"skills_matched\": [<string>...],
  \"skills_missing\": [<string>...],
  \"custom_pitch\": <string>
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
- decision is APPLY only if match is high enough AND seniority/year constraints are satisfied.
- skills_* must be lists of short skill phrases.
- custom_pitch max ~3 lines.
"""

    def analyze_job(
        self,
        job_title: str,
        company: str,
        description: str,
        profile: Dict[str, Any],
        policy: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Strict Phase-6 decision.

        Must return strict JSON only (python dict):
        {"decision": "APPLY" | "SKIP"}
        """
        # Hard rejects based on rules.
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
        if any(k in title_l or k in desc_l for k in senior_keywords):
            match_score_i = 0
            decision_payload = {"decision": "SKIP", "reason": "senior_role", "match_score": match_score_i}
            print(f"[AI] title={job_title} company={company} AI decision={decision_payload.get('decision')} match_score={match_score_i} reason={decision_payload.get('reason')}")
            return decision_payload


        # Experience hard reject: if job asks for > max_required_years

        # Best-effort extraction of years from title/description.
        import re

        max_required = int(getattr(self.settings, "max_required_years", 3))
        years_found = []
        for m in re.finditer(r"(\d+(?:\.\d+)?)\s*(?:\+|plus)?\s*\b(?:years|yrs)\b", title_l + " " + desc_l):
            try:
                years_found.append(float(m.group(1)))
            except Exception:
                pass
        if years_found:
            if max(years_found) > max_required:
                match_score_i = 0
                decision_payload = {"decision": "SKIP", "reason": "high_experience", "match_score": match_score_i}
                print(f"[AI] title={job_title} company={company} AI decision={decision_payload.get('decision')} match_score={match_score_i} reason={decision_payload.get('reason')}")
                return decision_payload



        # Skills match and easy-apply are evaluated via Ollama.
        # In REMOTE_ONLY/fallback mode we must not call local Ollama.
        if self.client is None:
            # In REMOTE_ONLY mode we cannot score with local Ollama.
            # Keep automation running by returning a safe deterministic APPLY.
            return {
                "decision": "APPLY",
                "reason": "remote fallback mode",
                "match_score": 75,
                "skills_matched": [],
                "skills_missing": [],
                "custom_pitch": "",
            }


        # Prompt Ollama to return strict JSON, then hard-filter by match_score.
        prompt = self._prompt_analyze_job(
            profile=profile,
            job_title=job_title,
            company=company,
            description=description,
            policy=policy,
        )
        payload = self.client.generate_json(prompt)


        # Reject if Ollama returns missing/low match.
        match_score = payload.get("match_score", None)
        try:
            match_score_i = int(float(match_score))
        except Exception:
            match_score_i = 0

        # Low-match hard reject
        if match_score_i < 55:
            decision_payload = {"decision": "SKIP", "reason": "low_match_score", "match_score": match_score_i}
            print(f"[AI] title={job_title} company={company} AI decision={decision_payload.get('decision')} match_score={match_score_i} reason={decision_payload.get('reason')}")
            return decision_payload



        # If Ollama indicates no easy apply, skip. (best-effort)
        # We look for common phrases in reason/fields.
        easy_apply_ok = False
        for k in ("reason", "custom_pitch"):
            v = payload.get(k)
            if isinstance(v, str) and "easy" in v.lower() and "apply" in v.lower():
                easy_apply_ok = True
        if not easy_apply_ok and isinstance(payload.get("reason"), str):
            # If reason doesn't mention it, don't trust; skip.
            decision_payload = {"decision": "SKIP", "reason": "no_easy_apply", "match_score": match_score_i}
            print(f"[AI] title={job_title} company={company} AI decision={decision_payload.get('decision')} match_score={match_score_i} reason={decision_payload.get('reason')}")
            return decision_payload



        decision = payload.get("decision")
        if decision == "APPLY" and match_score_i >= 55:
            return {"decision": "APPLY", "match_score": match_score_i}
        return {"decision": "SKIP", "reason": payload.get("reason", "low_match_score"), "match_score": match_score_i}





    def _prompt_answer_questions(self, profile: Dict[str, Any], question: str) -> str:
        return f"""You are an expert at job applications.

Return STRICT JSON only:
{{"answer": "<string>"}}

Candidate profile:
{profile}

Question:
{question}

Guidelines:
- Answer directly and truthfully.
- Keep it concise and professional.
"""

    def analyze_application_questions(self, question: str, profile: Dict[str, Any]) -> Dict[str, str]:
        """Return mapping for a single question."""

        # Fallback mode: never call Ollama.
        if self.client is None:
            return validate_answers({question: ""})

        prompt = self._prompt_answer_questions(profile=profile, question=question)
        payload = self.client.generate_json(prompt)

        # normalize to required answers schema: {question: answer}
        if not isinstance(payload, dict) or "answer" not in payload:
            raise ValueError("Invalid answers payload")
        return validate_answers({question: payload.get("answer", "")})



