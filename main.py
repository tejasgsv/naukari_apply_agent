from linkedin_bot import run_bot as run_linkedin
from naukri_bot import run_bot as run_naukri
from indeed_bot import run_bot as run_indeed

def main():
    print("Starting all platforms...")
    run_linkedin()
    run_naukri()
    run_indeed()

if __name__ == "__main__":
    main()