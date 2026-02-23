"""
WhatsApp DOM Analyzer - Fixed
"""
import asyncio
from pathlib import Path
import json

def print_results(results):
    """Print analysis results."""
    print("\n" + "="*70)
    print("ANALYSIS RESULTS")
    print("="*70)

    print(f"\nTotal div elements: {results['total_divs']}")

    print("\n--- Selector Test Results ---")
    successful = {k: v for k, v in results['selectors_tried'].items() if isinstance(v, int) and v > 0}
    for selector, count in sorted(successful.items(), key=lambda x: x[1], reverse=True):
        print(f"{count:>4} | {selector}")

    if results['best_matches']:
        print("\n--- Potential Message Elements ---")
        print("Found patterns that look like WhatsApp messages:\n")

        for idx, msg in enumerate(results['best_matches'][:5]):
            print(f"Pattern {idx + 1}:")
            print(f"  Classes: {msg['classes'][:80]}")
            print(f"  Text: {msg['textPreview']}")
            print()

async def auto_inspect():
    """Auto-inspect WhatsApp DOM."""
    print("="*70)
    print("WhatsApp DOM Auto-Analyzer")
    print("="*70)
    print("\nWill scan WhatsApp structure automatically...\n")

    try:
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            print("[1/3] Starting browser...")
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context(viewport={'width': 1600, 'height': 900})
            page = await context.new_page()

            print("[2/3] Loading WhatsApp...")
            await page.goto("https://web.whatsapp.com", wait_until="domcontentloaded", timeout=90000)

            print("\n" + "!"*70)
            print("SCAN QR CODE IN THE BROWSER WHEN IT APPEARS")
            print("!"*70 + "\n")

            # Wait for login
            for i in range(90):
                await asyncio.sleep(1)
                logged_in = await page.evaluate("""
                    () => !!(document.querySelector('[data-testid="chat-list"]') ||
                             document.querySelector('div[role="grid"]'))
                """)
                if logged_in:
                    print(f"[OK] Logged in detected!")
                    break
                if i % 10 == 0:
                    print(f"  Waiting... {i}s")

            await asyncio.sleep(5)

            # Click first chat
            await page.evaluate("""
                () => {
                    const chat = document.querySelector('div[role="grid"] > div') ||
                               document.querySelector('div._ak8q') ||
                               document.querySelector('[role="listitem"]');
                    if (chat) chat.click();
                }
            """)
            await asyncio.sleep(3)

            # Analyze
            analysis = await page.evaluate("""
                () => {
                    const result = {
                        total_divs: document.querySelectorAll('div').length,
                        selectors_tried: {},
                        best_matches: []
                    };

                    const selectors = [
                        'div[role="log"]',
                        'div[data-testid="msg-container"]',
                        'div[data-testid="message-container"]',
                        '[class*="_ao"]',
                        '[class*="_ak"]',
                        '[class*="_am"]',
                        '.selectable-text'
                    ];

                    selectors.forEach(sel => {
                        try {
                            result.selectors_tried[sel] = document.querySelectorAll(sel).length;
                        } catch(e) {
                            result.selectors_tried[sel] = 0;
                        }
                    });

                    // Find message candidates
                    const messages = [];
                    document.querySelectorAll('div, span').forEach(el => {
                        const className = el.className || '';
                        const text = el.textContent?.trim() || '';
                        if (text.length > 5 && /_(ao|ak|am)/.test(className)) {
                            messages.push({
                                classes: className,
                                textPreview: text.substring(0, 60)
                            });
                        }
                    });

                    // Get unique patterns
                    const seen = new Set();
                    messages.slice(0, 100).forEach(msg => {
                        const key = msg.classes.split(' ')[0];
                        if (!seen.has(key) && result.best_matches.length < 10) {
                            seen.add(key);
                            result.best_matches.push(msg);
                        }
                    });

                    return result;
                }
            """)

            # Print results
            print_results(analysis)

            # Save to file
            Path("Logs").mkdir(exist_ok=True)
            with open("Logs/whatsapp_analysis.json", "w") as f:
                json.dump(analysis, f, indent=2)
            print("\n[OK] Analysis saved to Logs/whatsapp_analysis.json")

            await page.screenshot(path="Logs/whatsapp_inspection.png")
            print("[OK] Screenshot saved to Logs/whatsapp_inspection.png")

            await asyncio.sleep(2)
            await browser.close()

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(auto_inspect())
