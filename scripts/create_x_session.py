import os
import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

# Add project root to sys.path to access settings if needed
sys.path.append(os.getcwd())

def create_manual_session():
    """Opens a visible browser for the user to log in manually and saves the session state."""
    session_dir = Path(".playwright_session")
    session_dir.mkdir(exist_ok=True)
    state_path = session_dir / "state.json"

    print("\n--- X Manual Session Creator ---")
    print("1. A browser window will open.")
    print("2. Log in to X (Twitter) using Google, Apple, or your preferred method.")
    print("3. Once you see your home feed, wait a few seconds.")
    print("4. Return here and press Enter to save the session.\n")

    with sync_playwright() as p:
        # Launch headed browser with stealth arguments
        browser = p.chromium.launch(
            headless=False,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox'
            ]
        )
        
        # Create context with a realistic user agent
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        context = browser.new_context(user_agent=user_agent)
        
        # Inject script to hide navigator.webdriver
        page = context.new_page()
        page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        page.goto("https://x.com/login")
        
        input("Press [Enter] AFTER you have successfully logged in and are on the home page...")
        
        # Save storage state
        context.storage_state(path=str(state_path))
        print(f"\nSUCCESS: Session state saved to {state_path}")
        print("You can now close the browser and run the agent in headless mode.\n")
        
        browser.close()

if __name__ == "__main__":
    create_manual_session()
