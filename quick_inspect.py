"""
Quick WhatsApp DOM analysis - works with existing or new browser.
"""
import asyncio
from pathlib import Path
import json

async def quick_inspect():
    """Quick inspection to find correct selectors."""
    print("="*70)
    print("Quick WhatsApp Selectors Finder")
    print("="*70)
    print("\nChecking what's available...\n")

    try:
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            print("[1/3] Launching browser (new instance)...")

            # Try regular browser instead of persistent
            browser = await p.chromium.launch(
                headless=False,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            context = await browser.new_context(
                viewport={'width': 1600, 'height': 900}
            )
            page = await context.new_page()

            print("[2/3] Loading WhatsApp Web...")
            await page.goto("https://web.whatsapp.com", wait_until="domcontentloaded", timeout=60000)

            print("\n" + "!"*70)
            print("ACTION NEEDED:")
            print("!"*70)
            print("Please:")
            print("1. Scan the QR code in the browser if needed")
            print("2. Wait for WhatsApp to load completely")
            print("3. Click on ANY chat that has messages")
            print("4. Wait for messages to appear in the chat view")
            print("5. Press Enter in this terminal")
            print("!"*70)
            input("\nPress Enter when ready...")

            print("\n[3/3] Analyzing message structure...")

            # Take screenshot
            await page.screenshot(path="Logs/whatsapp_inspection.png")
            print("  → Screenshot saved: Logs/whatsapp_inspection.png")

            # Get detailed DOM analysis
            result = await page.evaluate("""
                () => {
                    const analysis = {
                        timestamp: new Date().toISOString(),
                        total_divs: document.querySelectorAll('div').length,
                        selectors: {},
                        potential_messages: []
                    };

                    // Test standard selectors
                    const testSelectors = [
                        '[data-testid="msg-container"]',
                        '[data-testid="message-container"]',
                        '[role="log"]',
                        '.selectable-text',
                        'div[class*="message-container"]',
                        'div[class*="msg-container"]',
                        'div[class*="_ao"]',
                        'div[class*="_ak"]'
                    ];

                    testSelectors.forEach(sel => {
                        try {
                            const elements = document.querySelectorAll(sel);
                            analysis.selectors[sel] = elements.length;
                        } catch (e) {
                            analysis.selectors[sel] = `ERROR: ${e.message}`;
                        }
                    });

                    // Look for WhatsApp-specific patterns
                    const allDivs = document.querySelectorAll('div');
                    const whatsappPatterns = [];

                    for (let div of allDivs) {
                        const className = div.className || '';
                        const text = div.textContent?.trim() || '';
                        const hasTextContent = div.querySelector('.selectable-text');

                        // WhatsApp uses _ao, _ak, _am class prefixes
                        if (className.match(/_(ao|ak|am|ac)/) && text.length > 5) {
                            whatsappPatterns.push({
                                className: className.substring(0, 80),
                                textPreview: text.substring(0, 60),
                                hasSelectable: !!hasTextContent,
                                testId: div.getAttribute('data-testid') || 'none'
                            });
                        }
                    }

                    // Get unique patterns
                    const uniquePatterns = [];
                    const seenClasses = new Set();

                    whatsappPatterns.slice(0, 200).forEach(pattern => {
                        const baseClass = pattern.className.split(' ')[0];
                        if (!seenClasses.has(baseClass) && uniquePatterns.length < 10) {
                            seenClasses.add(baseClass);
                            uniquePatterns.push(pattern);
                        }
                    });

                    analysis.potential_messages = uniquePatterns;

                    return analysis;
                }
            """)

            print("\n" + "="*70)
            print("ANALYSIS RESULTS")
            print("="*70)

            print(f"\nTotal div elements in page: {result['total_divs']}")

            print("\n--- Selector Test Results ---")
            for selector, count in result['selectors'].items():
                status = "✓ FOUND" if count > 0 else "✗ NOT FOUND"
                print(f"{count:>4} | {selector:<50} {status}")

            if result['potential_messages'].length > 0:
                print("\n--- Potential Message Elements ---")
                print("(These look like WhatsApp message containers)\n")

                for idx, msg in enumerate(result['potential_messages']):
                    print(f"Candidate #{idx + 1}:")
                    print(f"  Classes: {msg['className']}")
                    print(f"  Has .selectable-text: {msg['hasSelectable']}")
                    if (msg['testId'] != 'none'):
                        print(f"  data-testid: {msg['testId']}")
                    print(f"  Text preview: {msg['textPreview']}")
                    print()

            # Save detailed results
            with open("Logs/whatsapp_selector_analysis.json", "w") as f:
                json.dump(result, f, indent=2)
            print("→ Full analysis saved to: Logs/whatsapp_selector_analysis.json")

            print("\n" + "="*70)
            print("RECOMMENDATIONS")
            print("="*70)
            print("\nBased on this analysis, update these selectors in:")
            print("  src/watchers/whatsapp_watcher.py (around line 73-88)\n")

            if result['potential_messages'].length > 0:
                best_candidate = result['potential_messages'][0]
                base_class = best_candidate['className'].split(' ')[0]
                print(f"SUGGESTED MESSAGE CONTAINER SELECTOR:")
                print(f"  'div.{base_class}'")
                print(f"  or: 'div[class*=\"{base_class[:6]}\"]'")

                if best_candidate['hasSelectable']:
                    print(f"\nSUGGESTED TEXT SELECTOR (inside message):")
                    print(f"  '.selectable-text'")

            await asyncio.sleep(2)
            await browser.close()

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(quick_inspect())
