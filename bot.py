import re
from playwright.sync_api import sync_playwright
from ai_brain import analyze_job, answer_questions
from utils import human_delay, random_mouse_move, slow_scroll
from tracker import is_job_processed, save_job

SEARCH_URL = "https://www.linkedin.com/jobs/search/?keywords=DevOps%20Engineer&location=India&f_WT=2%2C1"

def process_easy_apply(page):
    easy_apply_button = page.locator("button.jobs-apply-button")
    if not easy_apply_button.is_visible():
        print("No Easy Apply button found.")
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

            input_fields = page.locator(".jobs-easy-apply-form-element input, .jobs-easy-apply-form-element select").all()
            if input_fields:
                print("Found form elements, checking for custom questions...")
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
    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path="C:\\Program Files\\BraveSoftware\\Brave-Browser\\Application\\brave.exe",
            headless=False
        )

        context = browser.new_context(storage_state="linkedin_session.json")
        page = context.new_page()

        print("Opening LinkedIn jobs...")
        page.goto(SEARCH_URL)
        human_delay(5, 8)

        jobs = page.locator(".job-card-container").all()
        print(f"Found {len(jobs)} jobs on current page")

        for job in jobs:
            try:
                job_id = job.get_attribute("data-job-id")
                if not job_id:
                    continue

                if is_job_processed(job_id):
                    print(f"Skipping already processed job {job_id}")
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
                
                description_locator = page.locator(".jobs-description")
                description = description_locator.inner_text().strip() if description_locator.is_visible() else ""

                print("\n" + "="*50)
                print("Job Title:", title)

                result = analyze_job(title, description)
                
                if not result:
                    print("Could not get Gemini analysis. Skipping.")
                    continue

                decision = result.get("decision", "SKIP")
                reason = result.get("reason", "")
                
                print("Decision:", decision)
                print("Match:", result.get("match_percentage", 0), "%")
                print("Reason:", reason)

                if decision == "APPLY":
                    print("Pitch:", result.get("pitch", ""))
                    easy_apply_button = page.locator("button.jobs-apply-button")
                    
                    if easy_apply_button.is_visible() and "Easy Apply" in easy_apply_button.inner_text():
                        print("Starting Easy Apply flow...")
                        process_easy_apply(page)
                        save_job(job_id, title, "APPLIED", reason)
                    else:
                        print("Easy Apply not available. Skipping.")
                        save_job(job_id, title, "SKIPPED_NO_EASY_APPLY", "Easy apply not available")
                else:
                    save_job(job_id, title, "SKIPPED", reason)

            except Exception as e:
                print("Error processing job:", e)

        browser.close()

if __name__ == "__main__":
    run_bot()