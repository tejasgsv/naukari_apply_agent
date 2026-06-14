import urllib.parse
import os
from playwright.sync_api import sync_playwright
from ai_brain import analyze_job, answer_questions
from utils import human_delay, random_mouse_move, slow_scroll
from tracker import is_job_processed, save_job
from config import SEARCH_ROLES, RESUME_PATH, MAX_PAGES

def process_easy_apply(page):
    easy_apply_button = page.locator("button.jobs-apply-button")
    if not easy_apply_button.is_visible():
        return False
    
    easy_apply_button.click()
    human_delay(2, 5)

    while True:
        try:
            submit_button = page.locator("button[aria-label='Submit application'], button[aria-label='Submit']")
            if submit_button.is_visible():
                print("Reached final submit step. Waiting for manual confirmation.")
                input("Press Enter to confirm and manually submit, or to abort...")
                return True

            next_button = page.locator("button[aria-label='Continue to next step']")
            review_button = page.locator("button[aria-label='Review your application']")

            # Upload Resume if available
            file_input = page.locator("input[type='file']")
            if file_input.is_visible() and os.path.exists(RESUME_PATH):
                print("Found file input, uploading resume...")
                file_input.set_input_files(RESUME_PATH)
                human_delay(2, 4)

            # Answer custom questions
            input_fields = page.locator(".jobs-easy-apply-form-element input, .jobs-easy-apply-form-element select").all()
            if input_fields:
                questions = []
                labels = page.locator(".jobs-easy-apply-form-element label").all()
                for label in labels:
                    questions.append(label.inner_text().strip())
                
                if questions:
                    answers = answer_questions(questions)
                    print("AI Generated Answers:", answers)
                    print("Please fill custom fields manually if they are not auto-filled.")
            
            random_mouse_move(page)
            human_delay(2, 4)

            if next_button.is_visible():
                next_button.click()
            elif review_button.is_visible():
                review_button.click()
            else:
                print("Could not find Next/Review button. Please proceed manually.")
                input("Press Enter to continue bot after manual action...")

            human_delay(3, 6)

        except Exception as e:
            print(f"Error during Easy Apply flow: {e}")
            break

    return False

def run_bot():
    if not os.path.exists("linkedin_session.json"):
        print("Please run 'python login.py linkedin' first.")
        return

    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path="C:\\Program Files\\BraveSoftware\\Brave-Browser\\Application\\brave.exe",
            headless=False
        )

        context = browser.new_context(storage_state="linkedin_session.json")
        page = context.new_page()

        for role in SEARCH_ROLES:
            print(f"\nSearching for {role} on LinkedIn...")
            query = urllib.parse.quote(role)
            
            for page_num in range(MAX_PAGES):
                print(f"Loading page {page_num + 1}...")
                start_param = page_num * 25
                search_url = f"https://www.linkedin.com/jobs/search/?keywords={query}&location=India&f_WT=2%2C1&start={start_param}"
                page.goto(search_url)
                human_delay(5, 8)

                jobs = page.locator(".job-card-container").all()
                if not jobs:
                    print("No more jobs found. Moving to next role.")
                    break
                    
                print(f"Found {len(jobs)} jobs for {role} on page {page_num + 1}")

                for job in jobs:
                    try:
                        job_id = job.get_attribute("data-job-id")
                        if not job_id or is_job_processed(f"linkedin_{job_id}"):
                            continue

                        job.scroll_into_view_if_needed()
                        random_mouse_move(page)
                        human_delay(2, 5)
                        job.click()
                        human_delay(3, 6)

                        page.wait_for_selector(".jobs-description", timeout=10000)
                        slow_scroll(page)

                        title_locator = page.locator("h2.jobs-details-top-card__job-title, .job-details-jobs-unified-top-card__job-title").first
                        title = title_locator.inner_text().strip() if title_locator.is_visible() else "Unknown Title"
                        
                        company_locator = page.locator(".job-details-jobs-unified-top-card__company-name")
                        company = company_locator.inner_text().strip() if company_locator.is_visible() else "Unknown Company"

                        description_locator = page.locator(".jobs-description")
                        description = description_locator.inner_text().strip() if description_locator.is_visible() else ""
                        job_link = page.url

                        result = analyze_job(title, description)
                        if not result:
                            continue

                        decision = result.get("decision", "SKIP")
                        reason = result.get("reason", "")
                        
                        if decision == "APPLY":
                            easy_apply_button = page.locator("button.jobs-apply-button")
                            if easy_apply_button.is_visible() and "Easy Apply" in easy_apply_button.inner_text():
                                process_easy_apply(page)
                                save_job(f"linkedin_{job_id}", "LinkedIn", company, title, job_link, "APPLIED", reason)
                            else:
                                save_job(f"linkedin_{job_id}", "LinkedIn", company, title, job_link, "SKIPPED", "No Easy Apply")
                        else:
                            save_job(f"linkedin_{job_id}", "LinkedIn", company, title, job_link, "SKIPPED", reason)

                    except Exception as e:
                        print(f"Error processing job: {e}")

        browser.close()