# TODO - GitHub Actions compatibility updates for job_apply_bot

- [x] Update AI engine to bypass Ollama when REMOTE_ONLY=true and provide fallback behaviors.

- [ ] Update orchestrator to never abort run due to missing/failed Ollama; continue with fallback.
- [ ] Expand Settings.profile loading from env/secrets and define required profile fields.
- [ ] Add validation for required profile fields before attempting application; skip safely if missing.
- [ ] Enhance logging setup to always create `logs/` and write to file.
- [ ] Update orchestrator/session handling: if session artifacts missing, skip platform restore without failing.
- [ ] Ensure session persistence remains saved to `sessions/` after login (verify login/session manager flow).
- [ ] Improve error logging for job search and apply failures with context.
- [ ] Ensure Playwright remains headless in GH Actions via HEADLESS setting.
- [ ] Ensure bot continues safely even if AI scoring fails (no global aborts).


