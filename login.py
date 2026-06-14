import sys
from playwright.sync_api import sync_playwright

def login(platform):
    urls = {
        "linkedin": "https://www.linkedin.com/login",
        "naukri": "https://login.naukri.com/nLogin/Login.php",
        "indeed": "https://secure.indeed.com/auth"
    }
    
    if platform not in urls:
        print(f"Unknown platform: {platform}")
        return

    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path="C:\\Program Files\\BraveSoftware\\Brave-Browser\\Application\\brave.exe",
            headless=False
        )
        page = browser.new_page()
        page.goto(urls[platform])
        print(f"Login manually to {platform}...")
        input("After login press Enter...")
        page.context.storage_state(path=f"{platform}_session.json")
        print(f"Session saved for {platform}!")
        browser.close()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        login(sys.argv[1].lower())
    else:
        print("Usage: python login.py <linkedin|naukri|indeed>")