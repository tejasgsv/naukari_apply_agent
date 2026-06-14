# VPS Deployment (Ubuntu)

## 1) Install prerequisites
```bash
sudo apt-get update
sudo apt-get install -y python3 python3-pip git
```

(Optional) create/activate a venv
```bash
python3 -m venv .venv
source .venv/bin/activate
```

## 2) Install Ollama
```bash
curl -fsSL https://ollama.com/install.sh | sh
```
Then run:
```bash
ollama serve
```

## 3) Install Python dependencies
```bash
pip install -r requirements.txt
```

## 4) Install Playwright browsers
```bash
python -m playwright install --with-deps
```

## 5) Clone repository
```bash
git clone <YOUR_REPO_URL>
cd <YOUR_REPO_DIR>
```

## 6) Environment variables
Copy env example:
```bash
cp .env.example .env
```
Edit `.env` as needed.

## 7) Run the bot
```bash
python -m job_apply_bot.main
```

## 8) Cron setup (hourly)
Edit crontab:
```bash
crontab -e
```
Add (every hour):
```bash
0 * * * * /usr/bin/env bash -lc 'cd <YOUR_REPO_DIR> && source .venv/bin/activate && python -m job_apply_bot.main >> bot.log 2>&1'
```

## 9) Session persistence strategy
- Login bootstrap stores Playwright `storage_state` JSON files under `sessions/`.
- Ensure the `sessions/` directory is persisted across restarts:
  - Do not delete `sessions/*.json`.
  - Back up `sessions/` if using ephemeral environments.
- For unattended runs, you must run:
  - `python -m job_apply_bot.login --platform linkedin`
  - `python -m job_apply_bot.login --platform naukri`
  - `python -m job_apply_bot.login --platform indeed`
  at least once manually to create the session files.

