import urllib.parse
import os
from playwright.sync_api import sync_playwright
from ai_brain import analyze_job
from utils import human_delay, random_mouse_move, slow_scroll
from tracker import is_job_processed, save_job
from config import SEARCH_ROLES, MAX_PAGES

def run_bot():
    if not os.path.exists("indeed_session.json"):
        print("Please run 'python login.py indeed' first.")
        return

    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path="C:\\Program Files\\BraveSoftware\\Brave-Browser\\Application\\brave.exe",
            headless=False
        )

        context = browser.new_context(storage_state="indeed_session.json")
        page = context.new_page()

        for role in SEARCH_ROLES:
            print(f"\nSearching for {role} on Indeed...")
            query = urllib.parse.quote(role)
            
            for page_num in range(MAX_PAGES):
                print(f"Loading page {page_num + 1}...")
                start_param = page_num * 10
                search_url = f"https://in.indeed.com/jobs?q={query}&start={start_param}"
                page.goto(search_url)
                human_delay(5, 8)

                try:
                    jobs = page.locator(".job_seen_beacon").all()
                    if not jobs:
                        print("No more jobs found. Moving to next role.")
                        break
                        
                    print(f"Found {len(jobs)} jobs for {role} on page {page_num + 1}")

                    for job in jobs:
                        try:
                            job_id_elem = job.locator("h2 a")
                            if not job_id_elem.is_visible():
                                continue
                                
                            job_id = job_id_elem.get_attribute("data-jk")
                            if not job_id or is_job_processed(f"indeed_{job_id}"):
                                continue

                            title = job_id_elem.inner_text().strip()
                            company = job.locator("[data-testid='company-name']").inner_text().strip()
                            job_link = f"https://in.indeed.com/viewjob?jk={job_id}"
                            
                            job.scroll_into_view_if_needed()
                            random_mouse_move(page)
                            job_id_elem.click()
                            human_delay(3, 6)
                            
                            # Indeed loads description in a side pane
                            desc_pane = page.locator("#jobDescriptionText")
                            page.wait_for_selector("#jobDescriptionText", timeout=5000)
                            slow_scroll(page)
                            description = desc_pane.inner_text().strip()
                            
                            result = analyze_job(title, description)
                            if result and result.get("decision") == "APPLY":
                                print("Job matched. Manual intervention needed for Indeed Apply flow.")
                                input("Press Enter to continue after reviewing/applying...")
                                save_job(f"indeed_{job_id}", "Indeed", company, title, job_link, "APPLIED", result.get("reason"))
                            else:
                                save_job(f"indeed_{job_id}", "Indeed", company, title, job_link, "SKIPPED", result.get("reason", "No match"))
                                
                        except Exception as e:
                            print(f"Error processing individual job: {e}")
                except Exception as e:
                    print(f"Error fetching jobs list: {e}")

        browser.close()