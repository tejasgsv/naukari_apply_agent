import urllib.parse
import os
from playwright.sync_api import sync_playwright, TimeoutError
from ai_brain import analyze_job, answer_questions
from utils import human_delay, random_mouse_move, slow_scroll
from tracker import is_job_processed, save_job
from config import SEARCH_ROLES, RESUME_PATH, MAX_PAGES


def safe_goto(page, url, retries=3):
    for attempt in range(retries):
        try:
            print(f"Loading: {url} (Attempt {attempt+1})")
            page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=90000
            )
            page.wait_for_timeout(5000)
            return True
        except TimeoutError:
            print(f"Timeout on attempt {attempt+1}")
            if attempt == retries - 1:
                return False
    return False


def process_easy_apply(page):
    easy_apply_button = page.locator("button.jobs-apply-button")

    if not easy_apply_button.is_visible():
        return False

    easy_apply_button.click()
    human_delay(2, 5)

    while True:
        try:
            submit_button = page.locator(
                "button[aria-label='Submit application'], button[aria-label='Submit']"
            )

            if submit_button.is_visible():
                print("Reached final submit step.")
                input("Press Enter to submit manually...")
                return True

            next_button = page.locator(
                "button[aria-label='Continue to next step']"
            )
            review_button = page.locator(
                "button[aria-label='Review your application']"
            )

            file_input = page.locator("input[type='file']")
            if file_input.is_visible() and os.path.exists(RESUME_PATH):
                print("Uploading resume...")
                file_input.set_input_files(RESUME_PATH)
                human_delay(2, 4)

            input_fields = page.locator(
                ".jobs-easy-apply-form-element input, .jobs-easy-apply-form-element select"
            ).all()

            if input_fields:
                labels = page.locator(
                    ".jobs-easy-apply-form-element label"
                ).all()

                questions = []
                for label in labels:
                    questions.append(label.inner_text().strip())

                if questions:
                    answers = answer_questions(questions)
                    print("AI Answers:", answers)

            random_mouse_move(page)
            human_delay(2, 4)

            if next_button.is_visible():
                next_button.click()
            elif review_button.is_visible():
                review_button.click()
            else:
                print("Manual action required...")
                input("Press Enter after completing manually...")

            human_delay(3, 6)

        except Exception as e:
            print(f"Easy Apply Error: {e}")
            break

    return False


def run_bot():
    if not os.path.exists("linkedin_session.json"):
        print("Run login first: python login.py linkedin")
        return

    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
            headless=False,
            slow_mo=800
        )

        context = browser.new_context(
            storage_state="linkedin_session.json"
        )

        page = context.new_page()
        page.set_default_timeout(90000)

        for role in SEARCH_ROLES:
            print(f"\nSearching for {role}")

            query = urllib.parse.quote(role)

            for page_num in range(MAX_PAGES):
                start_param = page_num * 25

                search_url = (
                    f"https://www.linkedin.com/jobs/search/"
                    f"?keywords={query}"
                    f"&location=India"
                    f"&f_WT=2%2C1"
                    f"&f_TPR=r86400"
                    f"&start={start_param}"
                )

                if not safe_goto(page, search_url):
                    print("Skipping page due to timeout...")
                    continue

                human_delay(4, 7)

                jobs = page.locator(
                    "[data-job-id]"
                ).all()

                if not jobs:
                    print("No jobs found.")
                    break

                print(f"Found {len(jobs)} jobs")

                for job in jobs:
                    try:
                        job_id = job.get_attribute("data-job-id")

                        if not job_id:
                            continue

                        if is_job_processed(f"linkedin_{job_id}"):
                            continue

                        job.scroll_into_view_if_needed()
                        random_mouse_move(page)
                        human_delay(2, 4)

                        job.click()
                        human_delay(4, 7)

                        try:
                            page.wait_for_selector(
                                ".jobs-description",
                                timeout=15000
                            )
                        except:
                            continue

                        slow_scroll(page)

                        title = page.locator(
                            "h2.jobs-details-top-card__job-title, .job-details-jobs-unified-top-card__job-title"
                        ).first.inner_text().strip()

                        company = page.locator(
                            ".job-details-jobs-unified-top-card__company-name"
                        ).first.inner_text().strip()

                        description = page.locator(
                            ".jobs-description"
                        ).first.inner_text().strip()

                        job_link = page.url

                        result = analyze_job(title, description)

                        if not result:
                            continue

                        decision = result.get("decision", "SKIP")
                        reason = result.get("reason", "")

                        if decision == "APPLY":
                            easy_apply_button = page.locator(
                                "button.jobs-apply-button"
                            )

                            if (
                                easy_apply_button.is_visible()
                                and "Easy Apply" in easy_apply_button.inner_text()
                            ):
                                process_easy_apply(page)

                                save_job(
                                    f"linkedin_{job_id}",
                                    "LinkedIn",
                                    company,
                                    title,
                                    job_link,
                                    "APPLIED",
                                    reason
                                )
                            else:
                                save_job(
                                    f"linkedin_{job_id}",
                                    "LinkedIn",
                                    company,
                                    title,
                                    job_link,
                                    "SKIPPED",
                                    "No Easy Apply"
                                )
                        else:
                            save_job(
                                f"linkedin_{job_id}",
                                "LinkedIn",
                                company,
                                title,
                                job_link,
                                "SKIPPED",
                                reason
                            )

                    except Exception as e:
                        print(f"Job Error: {e}")

        browser.close()