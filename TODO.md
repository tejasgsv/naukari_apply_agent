TODO (Phase 7):
1) Update core/orchestrator.py: import NaukriBot + IndeedBot; extend orchestration to run those bots and ensure session files are used.
2) Update login.py: add --platform CLI; support linkedin/naukri/indeed login URLs; save sessions/{platform}_session.json.
3) Implement bots/naukri_bot.py: Playwright-based scraping with resilient selectors + heuristics for last 24h jobs; duplicate prevention; AI decision; apply flow (best-effort) with skip logging.
4) Implement bots/indeed_bot.py: same as Naukri.
5) Compile validation only for the Phase 7 files.
6) Ensure LinkedIn bot and ai/engine remain untouched.
