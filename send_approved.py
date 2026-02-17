#!/usr/bin/env python3
"""
Simple WhatsApp Sender - Uses existing saved session.
Just reads Approved folder and sends messages.
"""
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

APPROVED = Path("Approved")
DONE = Path("Done")
SESSION = Path("Logs/whatsapp_session")

def send_message(recipient: str, message: str):
    """Send WhatsApp message using saved session."""
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(SESSION),
            headless=False,
            args=['--window-size=1400,900']
        )
        page = context.pages[0] if context.pages else context.new_page()

        try:
            page.goto("https://web.whatsapp.com", wait_until="networkidle")
            time.sleep(3)

            # Search contact
            page.click('div[contenteditable="true"]')
            time.sleep(1)
            page.keyboard.press("Control+a")
            page.keyboard.press("Delete")
            page.type('div[contenteditable="true"]', recipient, delay=50)
            time.sleep(2)

            # Click first result
            page.press('div[contenteditable="true"]', "Enter")
            time.sleep(2)

            # Type message
            page.type('div[contenteditable="true"][data-tab="1"]', message, delay=30)
            time.sleep(1)

            # Send
            page.press('div[contenteditable="true"][data-tab="1"]', "Enter")
            time.sleep(2)

            print(f"[OK] Sent to {recipient}")
            context.close()
            return True

        except Exception as e:
            print(f"[ERROR] {e}")
            context.close()
            return False

def process_approved():
    """Process all files in Approved folder."""
    for draft in APPROVED.glob("*.md"):
        print(f"\nProcessing: {draft.name}")

        # Parse - SIMPLE VERSION
        content = draft.read_text(encoding='utf-8')
        lines = content.split('\n')
        to = ""
        body_lines = []
        found_to = False

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue

            # Find To: line
            if stripped.lower().startswith('to:'):
                to = stripped.split(':', 1)[1].strip()
                found_to = True
                continue

            # Everything after To: is body (if not empty)
            if found_to:
                body_lines.append(stripped)

        body = ' '.join(body_lines).strip()

        if to and body:
            if send_message(to, body):
                # Move to Done
                done_path = DONE / draft.name
                draft.rename(done_path)
                print(f"[OK] Moved to Done")
        else:
            print(f"[ERROR] Missing to or body")

if __name__ == "__main__":
    print("WhatsApp Sender - Using saved session")
    print("="*50)

    while True:
        process_approved()
        print("\nWaiting... (Ctrl+C to stop)")
        time.sleep(5)
