import sys
import time
import json
import os
import argparse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

def setup_driver():
    """Sets up the Chrome WebDriver with options."""
    options = webdriver.ChromeOptions()
    options.add_argument("--disable-notifications")
    options.add_argument("--start-maximized")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    return driver

def load_netscape_cookies(driver, filepath):
    """Loads cookies from a Netscape HTTP Cookie File (cookies.txt)."""
    if not os.path.exists(filepath):
        print(f"[ERROR] Cookie file not found: {filepath}")
        return False

    count = 0
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                if line.startswith('#') or not line.strip():
                    continue
                
                parts = line.strip().split('\t')
                if len(parts) >= 7:
                    domain = parts[0]
                    # Selenium strictly matches domains. Ensure it matches x.com or .x.com or twitter.com
                    # We will filter for relevant domains to avoid putting garbage
                    if "x.com" not in domain and "twitter.com" not in domain:
                        continue

                    cookie = {
                        'domain': domain,
                        'name': parts[5],
                        'value': parts[6],
                        'path': parts[2],
                        'secure': parts[3].lower() == 'true'
                    }
                    # Handle expiration if present
                    if parts[4] and parts[4] != "0":
                         cookie['expiry'] = int(parts[4])

                    try:
                        driver.add_cookie(cookie)
                        count += 1
                    except Exception as e:
                        # Ignore specific cookie errors (some sophisticated cookies might fail)
                        pass
        
        print(f"[INFO] Loaded {count} cookies from {filepath}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to parase cookie file: {e}")
        return False

def get_video_urls(driver, target_username):
    """Scrapes video URLs from the user's media tab."""
    base_url = f"https://x.com/{target_username}/media"
    driver.get(base_url)
    
    print(f"[INFO] Navigating to {base_url}...")
    time.sleep(5) 

    video_urls = set()
    last_height = driver.execute_script("return document.body.scrollHeight")
    retries = 0
    max_retries = 5 

    print(f"[INFO] Starting scan. Use Ctrl+C to stop early.")
    
    try:

        while True:
            # Find all status links directly
            # The media tab uses grid layout where each item is an anchor tag
            links = driver.find_elements(By.XPATH, "//a[contains(@href, '/status/')]")
            print(f"[DEBUG] Found {len(links)} status links in current view.")
            
            for link in links:
                try:
                    url = link.get_attribute("href")
                    if url and "/status/" in url:
                        # Clean URL
                        clean_url = url.split("?")[0]
                        # Filter out non-video/analytics noise if needed, 
                        # but /status/ usually implies a post.
                        # Sometimes these links might be strictly to the post.
                        
                        if clean_url not in video_urls:
                            video_urls.add(clean_url)
                            print(f"[FOUND] {clean_url}")
                            retries = 0 
                except Exception:
                    continue

            scroll_to_bottom(driver)
            
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                retries += 1
                print(f"[INFO] Loading... ({retries}/{max_retries})")
                if retries >= max_retries:
                    print("[INFO] No more new content found.")
                    break
            else:
                last_height = new_height
                retries = 0
                
    except KeyboardInterrupt:
        print("\n[INFO] Stopped by user command.")
    
    return list(video_urls)

def scroll_to_bottom(driver, wait_time=2.5):
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(wait_time)

def main():
    # Determine the directory where the script/exe is located
    if getattr(sys, 'frozen', False):
        application_path = os.path.dirname(sys.executable)
    else:
        application_path = os.path.dirname(os.path.abspath(__file__))
        
    default_cookies_path = os.path.join(application_path, "cookies.txt")

    parser = argparse.ArgumentParser(description="Scrape X (Twitter) video URLs.")
    parser.add_argument("username", nargs="?", help="The X username (without @)")
    parser.add_argument("-c", "--cookies", default=default_cookies_path, help="Path to cookies.txt")
    parser.add_argument("-o", "--output", default="urls.txt", help="Output file")
    args = parser.parse_args()
    
    # Interactive mode if no args provided
    target_user = args.username
    if not target_user:
        print("=========================================")
        print("      X (Twitter) Video URL Scraper      ")
        print("=========================================")
        target_user = input("Enter target username (without @): ").strip()
        if not target_user:
            print("No username provided. Exiting.")
            return

    # Check provided path or fallback to CWD if specific arg wasn't absolute?
    # Actually argparse default is absolute now.
    
    if not os.path.exists(args.cookies):
        # Fallback check: look in CWD just in case user expected it there
        cwd_cookie = "cookies.txt"
        if os.path.exists(cwd_cookie):
             args.cookies = cwd_cookie
        else:
            print(f"[ERROR] Cookie file not found at: {args.cookies}")
            print(f"       (Also checked current directory: {os.getcwd()})")
            print("Please run 'get_cookies.exe' to generate it in the application folder.")
            input("Press Enter to exit...")
            return

    driver = setup_driver()

    try:
        # Navigate to domain first to set cookie context
        driver.get("https://x.com")
        time.sleep(2)
        
        # Load Cookies
        if load_netscape_cookies(driver, args.cookies):
            driver.refresh()
            time.sleep(3)
        else:
            print("[WARN] No cookies loaded. You might see a login wall.")

        # Check Login Status (Simple check)
        if "login" in driver.current_url:
             print("[ERROR] Login failed. Please ensure cookies.txt is valid and exported from a logged-in session.")
             # We don't exit, we blindly try just in case, but it likely fails.
        
        # Scrape
        urls = get_video_urls(driver, args.username)
        
        # Export
        if urls:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write("\n".join(urls))
            print(f"\n[SUCCESS] Completed. Found {len(urls)} videos.")
        else:
            print("\n[RESULT] No videos found.")

    except Exception as e:
        print(f"[ERROR] Main crashed: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
