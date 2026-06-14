import json
import os
import time

APPLIED_JOBS_FILE = "applied_jobs.json"

def load_applied_jobs():
    if os.path.exists(APPLIED_JOBS_FILE):
        with open(APPLIED_JOBS_FILE, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

def save_job(job_id, platform, company, role, job_link, status, reason=""):
    jobs = load_applied_jobs()
    jobs[job_id] = {
        "platform": platform,
        "company": company,
        "role": role,
        "job_link": job_link,
        "status": status,
        "reason": reason,
        "date": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    with open(APPLIED_JOBS_FILE, "w") as f:
        json.dump(jobs, f, indent=4)

def is_job_processed(job_id):
    jobs = load_applied_jobs()
    return job_id in jobs