"""Playwright service for posting to X (Twitter).

The service maintains a persistent browser context (stored under ``.playwright_session``)
so that login cookies survive across runs.  On the first run the user is prompted
to log in manually; the session state is saved for subsequent automated posts.

Key responsibilities:
- Load/create a persistent Playwright context.
- Navigate to the tweet composer, enter text (truncated to 280 characters),
  and click the post button.
- Insert small random delays to mimic human interaction.
- On any exception, capture a screenshot in the ``Logs`` directory and return
  ``False`` so that the calling agent can move the file to ``Failed/``.
"""

import random
import time
from pathlib import Path
from typing import Optional

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# Local project settings – import the global ``settings`` instance
from src.config.settings import settings, BASE_DIR


class PlaywrightXService:
    """Encapsulates browser automation for X (Twitter) posting.

    The class lazily creates a Playwright ``browser`` and ``context`` on the first
    call to :meth:`post_tweet`.  The context's storage state is saved under
    ``.playwright_session/state.json`` inside the project root.
    """

    def __init__(self) -> None:
        self.base_dir = BASE_DIR
        self.session_dir = self.base_dir / ".playwright_session"
        self.state_path = self.session_dir / "state.json"
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.browser = None
        self.context = None
        self.page = None

    # ---------------------------------------------------------------------
    # Helper: small random delay to look human‑like
    # ---------------------------------------------------------------------
    def _human_delay(self, min_ms: int = 300, max_ms: int = 1500) -> None:
        time.sleep(random.uniform(min_ms, max_ms) / 1000.0)

    # ---------------------------------------------------------------------
    # Browser / context creation
    # ---------------------------------------------------------------------
    def _ensure_browser(self) -> None:
        """Start Playwright, load or create a persistent context.

        If a saved ``state.json`` exists we attempt to reuse it.  If the login
        cookie is missing or the page does not indicate a logged‑in state, we
        fall back to a fresh login flow.
        """
        if self.browser is not None:
            return  # Already ready
        playwright = sync_playwright().start()
        # ``headless=True`` is required for server/agent environments without a display.
        self.browser = playwright.chromium.launch(headless=True)
        if self.state_path.exists():
            self.context = self.browser.new_context(storage_state=str(self.state_path))
        else:
            self.context = self.browser.new_context()
        self.page = self.context.new_page()

    # ---------------------------------------------------------------------
    # Login handling – simple detection based on presence of a known element
    # ---------------------------------------------------------------------
    def _ensure_logged_in(self, timeout: int = 120) -> bool:
        """Make sure we are logged into X.

        If not logged in, we attempt automated login using X_USERNAME and X_PASSWORD.
        """
        print("[PlaywrightXService] Checking logged-in state...")
        try:
            self.page.goto("https://x.com/home", wait_until="domcontentloaded", timeout=30000)
        except Exception as e:
            print(f"[PlaywrightXService] Warning: Navigation to home timed out/failed: {e}")
        
        # Detect logged-in by looking for the post/tweet textarea OR profile indicators
        logged_in_selectors = [
            '[data-testid="tweetTextarea_0"]',
            '[data-testid="AppTabBar_Profile_Link"]',
            '[data-testid="SideNav_AccountSwitcher_Button"]',
            '[role="textbox"]'
        ]
        
        try:
            # Check if any of the selectors appear
            combined_selector = ", ".join(logged_in_selectors)
            self.page.wait_for_selector(combined_selector, timeout=15000)
            print("[PlaywrightXService] Logged in state confirmed via selector.")
            return True
        except PlaywrightTimeoutError:
            # Capture screenshot to see where we are
            self._capture_debug_screenshot("login_check_failed")
            
            # Check if we are on the login page specifically
            if "/login" in self.page.url:
                print("[PlaywrightXService] On login page, attempting automated login...")
            else:
                print(f"[PlaywrightXService] Not on login page but logged-in state not detected. URL: {self.page.url}")
                # We might still want to try login if we see a login button
                login_button = self.page.query_selector('a[href="/login"]')
                if not login_button:
                    return False # Give up if we don't know where we are
            
            # Not logged in – check for credentials
            username = settings.X_USERNAME
            password = settings.X_PASSWORD
            
            if not username or not password:
                print("[PlaywrightXService] Login required but X_USERNAME/PASSWORD missing.")
                return False

            print(f"[PlaywrightXService] Attempting automated login for {username}...")
            self.page.goto("https://x.com/login", wait_until="networkidle")
            
            try:
                # Enter username
                self.page.wait_for_selector('input[autocomplete="username"]').fill(username)
                self.page.keyboard.press("Enter")
                
                # Wait for password field
                self._human_delay()
                
                # Check for suspicious login / email verification
                if self.page.query_selector('input[data-testid="ocfEnterTextTextInput"]'):
                    email = getattr(settings, "X_EMAIL", None)
                    if email:
                        print("[PlaywrightXService] Handling extra security prompt...")
                        self.page.fill('input[data-testid="ocfEnterTextTextInput"]', email)
                        self.page.keyboard.press("Enter")
                        self._human_delay()

                self.page.wait_for_selector('input[name="password"]').fill(password)
                self.page.keyboard.press("Enter")
                
                # Wait for home page with any of the valid selectors
                self.page.wait_for_selector(combined_selector, timeout=timeout * 1000)
                
                # Save the state for next runs
                self.context.storage_state(path=str(self.state_path))
                print("[PlaywrightXService] Login successful and session saved.")
                return True
            except Exception as e:
                self._capture_debug_screenshot("automated_login_failed")
                print(f"[PlaywrightXService] Automated login failed: {e}")
                return False

    def _capture_debug_screenshot(self, name: str) -> None:
        """Helper to capture a timestamped screenshot on failure."""
        try:
            time.sleep(1) # Small delay to let UI stabilize
            logs_dir = Path(settings.LOGS_PATH).resolve()
            logs_dir.mkdir(parents=True, exist_ok=True)
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            path = logs_dir / f"x_{name}_{timestamp}.png"
            print(f"[PlaywrightXService] Attempting to save screenshot to: {path}")
            if self.page:
                # Use bytes capture as it's sometimes more reliable in headless
                img_bytes = self.page.screenshot(timeout=10000)
                with open(path, "wb") as f:
                    f.write(img_bytes)
                print(f"[PlaywrightXService] Debug screenshot saved: {path}")
        except Exception as e:
            print(f"[PlaywrightXService] Failed to capture screenshot: {e}")

    # ---------------------------------------------------------------------
    # Public API – post a tweet
    # ---------------------------------------------------------------------
    def post_tweet(self, content: str) -> bool:
        """Post *content* to X.

        Returns ``True`` on success, ``False`` on any error.
        """
        try:
            self._ensure_browser()
            if not self._ensure_logged_in():
                raise RuntimeError("Unable to log in to X (Twitter) within the timeout period")

            # Navigate to compose page
            self.page.goto("https://x.com/compose/post", wait_until="networkidle")
            self._human_delay()

            # Locate the tweet textarea - X uses contenteditable divs
            composer_selectors = [
                'div[data-testid="tweetTextarea_0"]',
                'div[role="textbox"][aria-label="Post text"]',
                'div[role="textbox"][aria-label="Tweet text"]',
                'div[contenteditable="true"]',
                '[role="textbox"]'
            ]
            combined_selector = ", ".join(composer_selectors)
            
            try:
                # Wait for any of the composer selectors to be visible
                textarea = self.page.wait_for_selector(combined_selector, timeout=10000)
                print(f"[PlaywrightXService] Found composer box.")
            except Exception:
                # Capture screenshot to see what's wrong
                self._capture_debug_screenshot("composer_not_found")
                raise RuntimeError("Could not find the tweet composer box.")

            # Click to focus
            textarea.click(force=True)
            self._human_delay(500, 1000)
            
            tweet_text = content[:280]
            print(f"[PlaywrightXService] Typing content: {tweet_text}")
            
            # Clear if needed (though usually empty)
            self.page.keyboard.press("Control+KeyA")
            self.page.keyboard.press("Backspace")
            
            # Use type instead of fill as it triggers events properly on X
            self.page.keyboard.type(tweet_text, delay=50)
            self._human_delay(1000, 2000)
            
            # Verify text is actually in the box.
            text_in_box = textarea.inner_text()
            print(f"[PlaywrightXService] Text in box: '{text_in_box}'")
            
            if not text_in_box.strip() or text_in_box.strip() == "What's happening?":
                print("[PlaywrightXService] Warning: Box seems empty. Trying fill() as last resort...")
                textarea.fill(tweet_text)
                self._human_delay(500, 1000)
                text_in_box = textarea.inner_text()
                print(f"[PlaywrightXService] Text in box after fill: '{text_in_box}'")
            
            # 2. Aggressive Clicking: Wait for button to be enabled
            post_button_selectors = [
                'button[data-testid="tweetButton"]',
                'button[data-testid="tweetButtonInline"]',
                'div[role="button"]:has-text("Post")',
                'div[role="button"]:has-text("Tweet")'
            ]
            combined_button_selector = ", ".join(post_button_selectors)
            
            print("[PlaywrightXService] Waiting for post button to be enabled...")
            try:
                self.page.wait_for_selector(f'{combined_button_selector}:not([disabled])', timeout=5000)
            except Exception:
                print("[PlaywrightXService] Warning: Post button never seemed enabled.")
                # We still try to click it just in case our selector is too strict
            
            # 3. Try to post using keyboard shortcut (Ctrl+Enter) first
            print("[PlaywrightXService] Sending tweet using Ctrl+Enter shortcut...")
            self.page.keyboard.press("Control+Enter")
            
            # 4. Fallback: Click the post button 
            try:
                self._human_delay(1500, 2500)
                post_button = self.page.query_selector(combined_button_selector)
                if post_button and post_button.is_visible() and post_button.is_enabled():
                    print("[PlaywrightXService] Falling back to button click...")
                    post_button.click(force=True)
            except Exception:
                pass
            
            # 3. Wait for success toast or redirection, OR detect known errors
            success_selectors = [
                'div[role="status"]:has-text("Your post was sent")',
                'div[role="status"]:has-text("Your Tweet was sent")',
                'div[role="status"]:has-text("sent")',
                'div[role="status"]:has-text("Sent")'
            ]
            
            found_success = False
            for _ in range(30): # 15 seconds approx
                # Check for success
                if any(self.page.query_selector(s) for s in success_selectors):
                    found_success = True
                    break
                # Check for "Something went wrong" error
                error_label = self.page.query_selector('div[role="alert"], [data-testid="toast"]')
                error_text = error_label.inner_text() if error_label else ""
                
                if "Something went wrong" in error_text:
                    print(f"[PlaywrightXService] Error detected: {error_text}. Retrying click...")
                    self._capture_debug_screenshot("something_went_wrong_detected")
                    try:
                        # Try to find and click the post button again
                        post_button = self.page.query_selector(combined_button_selector)
                        if post_button and post_button.is_visible() and post_button.is_enabled():
                            post_button.click(force=True)
                            self._human_delay(2000, 3000)
                    except Exception:
                        pass
                
                # Check if composer is still there
                if not self.page.query_selector(combined_selector):
                    # If composer is gone, it's very likely it was sent
                    found_success = True
                    break
                time.sleep(1)
            
            # Final fallback: If still stuck, try one more time or give up
            if not found_success and self.page.query_selector(combined_selector):
                 print("[PlaywrightXService] Final attempt: Clicking post button one last time...")
                 try:
                    post_button = self.page.query_selector(combined_button_selector)
                    if post_button:
                        post_button.click(force=True)
                        self._human_delay(3000, 5000)
                        if not self.page.query_selector(combined_selector):
                            found_success = True
                 except Exception:
                     pass
            
            if found_success:
                print("[PlaywrightXService] Post confirmed.")
                return True
            
            print("[PlaywrightXService] Success could not be confirmed within timeout.")
            self._capture_debug_screenshot("post_confirmation_timeout")
            return False
        except Exception as exc:
            # Capture a screenshot for debugging using our absolute path helper.
            self._capture_debug_screenshot("posting_failed_exception")
            print(f"[PlaywrightXService] Error posting tweet: {exc}")
            return False
        # Removed finally block to allow post-check screenshots in the test script
    
    def close(self):
        """Clean up resources."""
        if self.context:
            self.context.close()
            self.context = None
        if self.browser:
            self.browser.close()
            self.browser = None
