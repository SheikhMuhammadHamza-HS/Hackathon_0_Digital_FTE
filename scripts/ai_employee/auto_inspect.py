"""
Fully automated WhatsApp DOM inspection.
Just wait and it will auto-analyze after login.
"""
import asyncio
from pathlib import Path
import json
import time

async def auto_inspect():
    """Auto-inspect WhatsApp DOM structure."""
    print("="*70)
    print("Auto WhatsApp DOM Inspector")
    print("="*70)
    print("\nThis will automatically analyze WhatsApp's structure.")
    print("Just wait after scanning QR code...\n")

    try:
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            print("[1/3] Launching browser...")
            browser = await p.chromium.launch(
                headless=False,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            context = await browser.new_context(
                viewport={'width': 1600, 'height': 900}
            )
            page = await context.new_page()

            print("[2/3] Loading WhatsApp Web...")
            await page.goto("https://web.whatsapp.com", wait_until="domcontentloaded", timeout=90000)

            print("\n" + "!"*70)
            print("SCAN QR CODE NOW!")
            print("The script will continue automatically in 90 seconds...")
            print("!"*70 + "\n")

            # Wait for login (up to 90 seconds)
            login_waited = 0
            max_wait = 90
            logged_in = False

            while login_waited < max_wait:
                await asyncio.sleep(1)
                login_waited += 1

                # Check if logged in by looking for chat list
                logged_in = await page.evaluate("""
                    () => {
                        return !!(
                            document.querySelector('[data-testid="chat-list"]') ||
                            document.querySelector('div[role="grid"]') ||
                            document.querySelector('[aria-label="Chat list"]')
                        );
                    }
                """)

                if logged_in:
                    print(f"✓ Logged in detected after {login_waited} seconds!")
                    break

                if login_waited % 10 == 0:
                    print(f"  Waiting... {login_waited}s elapsed")

            if not logged_in:
                print("\n⚠ Timeout waiting for login. Will try anyway...")

            # Give extra time for WhatsApp to fully load
            print("\nWaiting for WhatsApp to fully load...")
            await asyncio.sleep(10)

            # Try to click on first chat automatically
            print("\n[3/3] Analyzing chat structure...")

            # Try to click first chat item
            first_chat_clicked = await page.evaluate("""
                () => {
                    const chat_selectors = [
                        'div[role="grid"] > div',
                        'div._ak8q',
                        'div[role="listitem"]',
                        '[data-testid="chat-list-item"]'
                    ];

                    for (let selector of chat_selectors) {
                        const chat = document.querySelector(selector);
                        if (chat) {
                            chat.click();
                            return { success: true, selector: selector };
                        }
                    }
                    return { success: false, selector: null };
                }
            """)

            if first_chat_clicked['success']:
                print(f"✓ Clicked first chat using: {first_chat_clicked['selector']}")
                await asyncio.sleep(3)  # Wait for messages to load
            else:
                print("⚠ Could not automatically click chat. Analysis continues...")

            # Take screenshot
            await page.screenshot(path="Logs/whatsapp_auto_inspection.png")
            print("\n  → Screenshot saved: Logs/whatsapp_auto_inspection.png")

            # Comprehensive analysis
            analysis = await page.evaluate("""
                () => {
                    const analysis = {
                        timestamp: new Date().toISOString(),
                        total_divs: document.querySelectorAll('div').length,
                        selectors_tried: {},
                        best_matches: [],
                        message_structure: null
                    };

                    // Test all known selectors
                    const selectors = [
                        // Primary message containers
                        'div[role="log"]',
                        'div[data-testid="msg-container"]',
                        'div[data-testid="message-container"]',
                        'div[data-testid="conversation-panel-messages"]',

                        // Alternative patterns
                        '[class*="message"]',
                        '[class*="msg"]',
                        '[class*="_ao"]',
                        '[class*="_ak"]',
                        '[class*="_am"]',

                        // Text selectors
                        '.selectable-text',
                        '[class*="selectable"]',
                        'span[dir="ltr"]',

                        // Container patterns
                        'div[class*="focusable-list-item"]',
                        'div[class*="message-in"]',
                        'div[class*="message-out"]'
                    ];

                    selectors.forEach(sel => {
                        try {
                            const elements = document.querySelectorAll(sel);
                            analysis.selectors_tried[sel] = elements.length;
                        } catch (e) {
                            analysis.selectors_tried[sel] = `Error: ${e.message}`;
                        }
                    });

                    // Look for messages by pattern matching
                    const messages = [];
                    const allElements = document.querySelectorAll('div, span');

                    for (let el of allElements) {
                        const className = el.className || '';
                        const text = el.textContent?.trim() || '';

                        // Skip empty or very short text
                        if (text.length < 5) continue;

                        // WhatsApp message indicators
                        const isWhatsAppMessage = (
                            // Has WhatsApp class patterns
                            /_(ao|ak|am|ac|bu)/.test(className) ||

                            // Has selectable text indicator
                            el.querySelector && el.querySelector('.selectable-text') ||

                            // Has LTR direction for text
                            el.getAttribute('dir') === 'ltr' && text.length > 10 ||

                            // Message bubble patterns
                            className.includes('message-in') ||
                            className.includes('message-out') ||
                            className.includes('focusable-list-item')
                        );

                        if (isWhatsAppMessage) {
                            messages.push({
                                tag: el.tagName.toLowerCase(),
                                classes: className.substring(0, 100),
                                textPreview: text.substring(0, 60),
                                testId: el.getAttribute('data-testid') || 'none'
                            });
                        }
                    }

                    // Get unique patterns only
                    const unique = [];
                    const seen = new Set();

                    messages.slice(0, 100).forEach(msg => {
                        const key = msg.classes.split(' ')[0] || msg.tag;
                        if (!seen.has(key) && unique.length < 15) {
                            seen.add(key);
                            unique.push(msg);
                        }
                    });

                    analysis.best_matches = unique;

                    // Try to extract actual message structure if possible
                    if (messages.length > 0) {
                        analysis.message_structure = {
                            total_found: messages.length,
                            example: messages[0]
                        };
                    }

                    return analysis;
                }
            """)

            # Save results
            with open("Logs/whatsapp_selector_analysis.json", "w", encoding="utf-8") as f:
                json.dump(analysis, f, indent=2)

            # Display results
            print("\n" + "="*70)
            print("SELECTOR ANALYSIS RESULTS")
            print("="*70)

            print(f"\n📊 Total elements analyzed: {analysis['total_divs']:,} divs/spans")

            print("\n--- Most Successful Selectors ---")
            print("(Sorted by number of matches found)\n")

            const sortedSelectors = Object.entries(analysis['selectors_tried'])
                .filter(([_, count]) => typeof count === 'number' && count > 0)
                .sort((a, b) => b[1] - a[1]);

            if (sortedSelectors.length > 0) {
                for (const [selector, count] of sortedSelectors.slice(0, 10)) {
                    const marker = count > 5 ? "✓" : "~";
                    print(f"{marker} {count:>4} matches | {selector}");
                }
            } else {
                print("No selectors found matches!");
            }

            print("\n--- Potential Message Elements ---")
            print("(These look like actual WhatsApp messages)\n")

            if (analysis['best_matches'].length > 0) {
                const matches = analysis['best_matches'];
                print(f"Found {matches.length} unique message patterns:\n");

                for (let i = 0; i < Math.min(matches.length, 5); i++) {
                    const msg = matches[i];
                    print(`Pattern ${i + 1}:`);
                    print(`  Element: ${msg.tag}${msg.classes ? '.' + msg.classes.split(' ')[0] : ''}`);
                    print(`  Classes: ${msg.classes || 'none'}`);
                    if (msg.testId !== 'none') {
                        print(`  data-testid: ${msg.testId}`);
                    }
                    print(`  Text preview: "${msg.textPreview}"`);
                    print();
                }

                // Show best selector suggestion
                const best = matches[0];
                const baseClass = best.classes.split(' ')[0];

                print("="*70);
                print("RECOMMENDED UPDATES FOR: src/watchers/whatsapp_watcher.py");
                print("="*70);
                print("\nReplace lines 73-88 (SELECTORS dictionary) with:\n");
                print("'message_container': [");
                print(`    'div.${baseClass}',`);
                if (best.testId && best.testId !== 'none') {
                    print(`    '[data-testid="${best.testId}"]',`);
                }
                print(`    'div[class*="${baseClass.substring(0, 6)}"]',`);
                print("],\n");
                print("'message_text': [");
                print("    'span.selectable-text',")},
                print("    'span[dir=\"ltr\"]',")
                print("    'div[dir=\"ltr\"]',"),
                print("],\n");
            } else {
                print("Could not identify message patterns automatically.");
                print("Check the screenshot and JSON file for manual inspection.");
            }

            print("="*70);
            print(f"✓ Full analysis saved to: Logs/whatsapp_selector_analysis.json")
            print("="*70)

            # Wait before closing
            print("\nClosing browser in 5 seconds...")
            await asyncio.sleep(5)
            await browser.close()

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Ensure logs directory exists
    Path("Logs").mkdir(exist_ok=True)
    asyncio.run(auto_inspect())
