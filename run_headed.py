from playwright.sync_api import sync_playwright
import time

def run():
    with sync_playwright() as p:
        print("Launching browser in Headed mode...")
        # Launch browser in Headed mode
        browser = p.chromium.launch(headless=False, slow_mo=500)
        page = browser.new_page()
        
        # Navigate to jobs.ge
        print("Navigating to jobs.ge...")
        page.goto("https://jobs.ge/?page=1&q=QA+Automation")
        page.wait_for_load_state("networkidle")
        
        # Keep the browser open for a few seconds so the user can see it
        time.sleep(5)
        
        print("Demo finished. Closing browser...")
        browser.close()

if __name__ == '__main__':
    run()
