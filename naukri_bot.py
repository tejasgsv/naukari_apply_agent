import urllib.parse
import os
from playwright.sync_api import sync_playwright
from ai_brain import analyze_job
from utils import human_delay, random_mouse_move, slow_scroll
from tracker import is_job_processed, save_job
from config import SEARCH_ROLES, MAX_PAGES

def run_bot():
    if not os.path.exists("naukri_session.json"):
        print("Please run 'python login.py naukri' first.")
        return

    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path="C:\\Program Files\\BraveSoftware\\Brave-Browser\\Application\\brave.exe",
            headless=False
        )

        context = browser.new_context(storage_state="naukri_session.json")
        page = context.new_page()

        for role in SEARCH_ROLES:
            print(f"\nSearching for {role} on Naukri...")
            query = role.replace(" ", "-")
            
            for page_num in range(1, MAX_PAGES + 1):
                print(f"Loading page {page_num}...")
                if page_num == 1:
                    search_url = f"https://www.naukri.com/{query}-jobs?jobAge=15"
                else:
                    search_url = f"https://www.naukri.com/{query}-jobs-{page_num}?jobAge=15"
                
                page.goto(search_url)
                human_delay(5, 8)

                try:
                    jobs = page.locator(".srp-jobtuple-wrapper").all()
                    if not jobs:
                        print("No more jobs found. Moving to next role.")
                        break
                        
                    print(f"Found {len(jobs)} jobs for {role} on page {page_num}")

                    for i in range(len(jobs)):
                        try:
                            job = jobs[i]
                            job_id = job.get_attribute("data-job-id")
                            if not job_id or is_job_processed(f"naukri_{job_id}"):
                                continue

                            title = job.locator(".title").inner_text().strip()
                            company = job.locator(".comp-name").inner_text().strip()
                            job_link = job.locator(".title").get_attribute("href")
                            
                            job.scroll_into_view_if_needed()
                            random_mouse_move(page)
                            
                            # Open job in new tab to read description
                            with context.expect_page() as new_page_info:
                                job.locator(".title").click()
                            
                            job_page = new_page_info.value
                            job_page.wait_for_load_state()
                            human_delay(3, 6)
                            slow_scroll(job_page)
                            
                            description_locator = job_page.locator(".job-desc")
                            description = description_locator.inner_text().strip() if description_locator.is_visible() else ""
                            
                            result = analyze_job(title, description)
                            if result and result.get("decision") == "APPLY":
                                apply_btn = job_page.locator("#apply-button")
                                if apply_btn.is_visible():
                                    print("Applying to job... Waiting for manual confirmation.")
                                    input("Press Enter to click apply or skip...")
                                    apply_btn.click()
                                    save_job(f"naukri_{job_id}", "Naukri", company, title, job_link, "APPLIED", result.get("reason"))
                            else:
                                save_job(f"naukri_{job_id}", "Naukri", company, title, job_link, "SKIPPED", result.get("reason", "No match"))
                            
                            job_page.close()
                        except Exception as e:
                            print(f"Error processing individual job: {e}")
                except Exception as e:
                    print(f"Error fetching jobs list: {e}")

        browser.close()