#!/usr/bin/env python3
"""
Simple WhatsApp Sender - One message at a time.
Usage: python whatsapp_send_simple.py "Papa" "Salam Papa"
"""
import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

SESSION = Path("Logs/whatsapp_session")

def send_message(recipient: str, message: str):
    """Send WhatsApp message."""
    print(f"Sending to {recipient}...")

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(SESSION),
            headless=False,
            args=['--window-size=1400,900', '--disable-blink-features=AutomationControlled']
        )
        page = context.pages[0] if context.pages else context.new_page()

        try:
            # Open WhatsApp Web
            print("Opening WhatsApp Web...")
            page.goto("https://web.whatsapp.com", wait_until="domcontentloaded")

            # Wait for chat list (means logged in)
            print("Waiting for login...")
            try:
                page.wait_for_selector('[data-testid="chat-list"]', timeout=30000)
                print("Logged in!")
            except PlaywrightTimeout:
                print("ERROR: Not logged in. Please scan QR code first.")
                context.close()
                return False

            time.sleep(2)

            # Search for contact
            print(f"Searching for {recipient}...")

            # Click search box (first contenteditable)
            search_box = page.query_selector('div[contenteditable="true"]')
            if not search_box:
                print("ERROR: Search box not found")
                context.close()
                return False

            search_box.click()
            time.sleep(0.5)

            # Clear and type
            page.keyboard.press("Control+a")
            page.keyboard.press("Delete")
            search_box.type(recipient, delay=100)
            time.sleep(2)

            # Press Enter to select first result
            page.keyboard.press("Enter")
            time.sleep(3)

            # Find message input
            print("Typing message...")
            inputs = page.query_selector_all('div[contenteditable="true"]')
            msg_input = None
            for inp in inputs:
                if inp.get_attribute('data-tab') == '1':
                    msg_input = inp
                    break

            if not msg_input:
                # Try any contenteditable
                msg_input = page.query_selector('footer div[contenteditable="true"]')

            if not msg_input:
                print("ERROR: Message input not found")
                context.close()
                return False

            # Type and send
            msg_input.click()
            time.sleep(0.5)
            msg_input.type(message, delay=50)
            time.sleep(1)

            # Send
            page.keyboard.press("Enter")
            time.sleep(2)

            print(f"✓ Message sent to {recipient}")
            context.close()
            return True

        except Exception as e:
            print(f"ERROR: {e}")
            # Take screenshot for debugging
            try:
                page.screenshot(path="error_screenshot.png")
                print("Screenshot saved: error_screenshot.png")
            except:
                pass
            context.close()
            return False

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python whatsapp_send_simple.py 'Recipient Name' 'Your message'")
        print("Example: python whatsapp_send_simple.py 'Papa' 'Salam Papa, kaise hain?'")
        sys.exit(1)

    recipient = sys.argv[1]
    message = sys.argv[2]

    success = send_message(recipient, message)
    sys.exit(0 if success else 1)
