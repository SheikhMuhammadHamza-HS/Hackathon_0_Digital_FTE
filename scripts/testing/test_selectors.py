"""
Quick test of updated selectors - uses simplified approach.
"""
import asyncio
import sys
import io
from pathlib import Path

# Fix Windows encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

async def test_selectors():
    """Test the updated message selectors."""
    print("="*70)
    print("Testing Updated WhatsApp Selectors")
    print("="*70)
    print("\nSteps:")
    print("1. Script will open browser")
    print("2. Scan QR code if needed")
    print("3. Test message extraction with new selectors")
    print("4. Show results\n")

    try:
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            print("[1/4] Launching browser...")
            browser = await p.chromium.launch(headless=False)
            page = await browser.new_page()

            print("[2/4] Loading WhatsApp Web...")
            await page.goto("https://web.whatsapp.com")

            # Wait for login
            print("[3/4] Waiting for login...")
            for i in range(90):
                await asyncio.sleep(1)
                logged_in = await page.evaluate("""
                    () => !!(document.querySelector('[data-testid="chat-list"]') ||
                             document.querySelector('div[role="grid"]'))
                """)
                if logged_in:
                    print(f"    Logged in after {i+1} seconds!")
                    break
                if i % 10 == 0:
                    print(f"    Waiting... {i}s")

            await asyncio.sleep(5)

            print("\n[4/4] Testing new selectors...")

            # Get chat items
            chat_items = await page.query_selector_all('div[role="grid"] > div')
            print(f"    Found {len(chat_items)} chat items")

            if chat_items:
                # Click first chat
                await chat_items[0].click()
                await asyncio.sleep(2)

                # Test new selectors
                print("\n    Testing message selectors:")

                # NEW SELECTORS from our analysis
                new_selectors = [
                    'div[class*="_ak9"]',
                    'div[class*="_ak7"]',
                    'div[class*="_ao"]',
                    'div[class*="_am"]'
                ]

                messages_found = []
                for selector in new_selectors:
                    try:
                        elements = await page.query_selector_all(selector)
                        if elements:
                            # Check if they have text
                            texts = []
                            for el in elements[:5]:  # Check first 5
                                text = await el.text_content()
                                if text and len(text.strip()) > 10:
                                    texts.append(text.strip()[:50])

                            if texts:
                                messages_found.append({
                                    'selector': selector,
                                    'count': len(elements),
                                    'samples': texts
                                })
                                print(f"      ✓ {selector}: {len(elements)} elements")
                                for sample in texts[:2]:
                                    print(f"        - {sample}")
                    except Exception as e:
                        print(f"      ✗ {selector}: Error - {e}")

                if messages_found:
                    print(f"\n    SUCCESS! Found {len(messages_found)} working selectors")
                    print("\n" + "="*70)
                    print("RECOMMENDED UPDATE")
                    print("="*70)
                    print("\nUpdate src/watchers/whatsapp_watcher.py with:")
                    print("\n'message_container': [")
                    for m in messages_found[:3]:
                        print(f"    '{m['selector']}',")
                    print("],")
                else:
                    print("\n    No messages found with new selectors. Trying fallback...")

                    # Fallback: try to get all divs and find messages
                    all_divs = await page.query_selector_all('div')
                    print(f"    Checking {len(all_divs)} divs...")

                    for i, div in enumerate(all_divs[-30:]):
                        try:
                            text = await div.text_content()
                            if text and len(text.strip()) > 20:
                                classes = await div.get_attribute('class') or ''
                                print(f"    Div {i}: classes={classes[:50]}, text={text.strip()[:60]}")
                        except:
                            pass

            print("\nPress Enter to close browser...")
            input()
            await browser.close()

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_selectors())
