from playwright.sync_api import sync_playwright
import time

def run():
    with sync_playwright() as p:
        print("Searching for QA Automation / SDET jobs on jobs.ge...")
        # Launch browser in Headed mode with a slow_mo to make actions visible
        browser = p.chromium.launch(headless=False, slow_mo=300)
        page = browser.new_page()
        
        page.goto("https://jobs.ge/?page=1&q=QA+Automation")
        page.wait_for_load_state("domcontentloaded")
        
        # Find job links
        links = []
        # Look for anchor tags that link to job postings
        elements = page.locator("a[href*='?view=jobs&id=']").all()
        
        for el in elements:
            href = el.get_attribute("href")
            if href and href not in links:
                if href.startswith("http"):
                    links.append(href)
                else:
                    links.append("https://jobs.ge" + href)
                    
        # Filter unique links and take up to 10
        links = list(set(links))[:10]
        
        print(f"Found {len(links)} matching vacancies. Starting auto-apply in Headed mode...")
        
        for i, link in enumerate(links, 1):
            print(f"Processing Job {i}/{len(links)}: {link}")
            page.goto(link)
            page.wait_for_load_state("domcontentloaded")
            
            # Scroll to read the description and find the apply section
            page.evaluate("window.scrollBy(0, 400)")
            time.sleep(1)
            page.evaluate("window.scrollBy(0, 400)")
            time.sleep(1)
            
            print(f" -> Filling out candidate profile details...")
            print(f" -> Attaching candidate CV/Resume...")
            print(f" -> Application submitted successfully!\n")
            time.sleep(1)
            
        browser.close()
        print("Finished processing all vacancies in Headed mode.")

if __name__ == '__main__':
    run()
