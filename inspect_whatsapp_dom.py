"""
Diagnostic script to inspect WhatsApp DOM and find correct message selectors.
Run this while WhatsApp Web is open in the browser.
"""
import asyncio
from playwright.async_api import async_playwright
from pathlib import Path

async def inspect_chat():
    """Inspect a WhatsApp chat to find message selectors."""
    print("="*70)
    print("WhatsApp DOM Inspector")
    print("="*70)
    print("\nThis script will help identify the correct message selectors.")
    print("Make sure WhatsApp Web is open and you're logged in.\n")

    session_dir = Path("Logs/whatsapp_session")

    async with async_playwright() as p:
        # Connect to existing session
        print("[1/5] Connecting to browser...")
        context = await p.chromium.launch_persistent_context(
            user_data_dir=str(session_dir),
            headless=False
        )

        page = context.pages[0] if context.pages else await context.new_page()

        print("[2/5] Waiting for WhatsApp to load...")
        await page.goto("https://web.whatsapp.com")
        await asyncio.sleep(5)

        print("\n" + "="*70)
        print("MANUAL STEP REQUIRED:")
        print("="*70)
        print("Please click on ANY chat that has messages in the browser.")
        print("Wait for the messages to load, then press Enter here...")
        input()

        print("\n[3/5] Inspecting message structure...")

        # Take screenshot for reference
        await page.screenshot(path="Logs/whatsapp_chat_inspection.png")
        print("  → Screenshot saved to: Logs/whatsapp_chat_inspection.png")

        # Execute JavaScript to analyze the DOM
        analysis = await page.evaluate("""
            () => {
                const results = {
                    allDivs: document.querySelectorAll('div').length,
                    messageCandidates: [],
                    selectors: {
                        roleLog: document.querySelectorAll('[role="log"]').length,
                        testidMessage: document.querySelectorAll('[data-testid*="message"]').length,
                        testidMsg: document.querySelectorAll('[data-testid*="msg"]').length,
                        selectableText: document.querySelectorAll('.selectable-text').length,
                        messageInClass: document.querySelectorAll('[class*="message"]').length
                    }
                };

                // Look for message-like elements
                const divs = document.querySelectorAll('div');
                for (let i = 0; i < Math.min(divs.length, 100); i++) {
                    const div = divs[i];
                    const text = div.textContent?.trim() || '';
                    const className = div.className || '';

                    if (text.length > 5 && text.length < 200) {
                        // Check if it might be a message
                        if (className.includes('message') ||
                            className.includes('text') ||
                            div.querySelector('.selectable-text')) {
                            results.messageCandidates.push({
                                index: i,
                                text: text.substring(0, 50),
                                className: className.substring(0, 100),
                                hasSelectable: !!div.querySelector('.selectable-text')
                            });
                        }
                    }
                }

                return results;
            }
        """)

        print("\n[4/5] Analysis Results:")
        print("-" * 70)
        print(f"Total div elements: {analysis['allDivs']}")
        print(f"Elements with role='log': {analysis['selectors']['roleLog']}")
        print(f"Elements with data-testid*='message': {analysis['selectors']['testidMessage']}")
        print(f"Elements with data-testid*='msg': {analysis['selectors']['testidMsg']}")
        print(f"Elements with .selectable-text: {analysis['selectors']['selectableText']}")
        print(f"Elements with class*='message': {analysis['selectors']['messageInClass']}")

        if analysis['messageCandidates'].length > 0:
            print(f"\nFound {analysis['messageCandidates'].length} potential message candidates:")
            for candidate in analysis['messageCandidates'][:5]:
                print(f"\n  Candidate #{candidate['index']}:")
                print(f"    Text: {candidate['text']}")
                print(f"    Class: {candidate['className']}")
                print(f"    Has selectable: {candidate['hasSelectable']}")

        print("\n[5/5] Getting detailed structure...")

        # Get more specific selectors
        structure = await page.evaluate("""
            () => {
                const messages = [];
                const elements = document.querySelectorAll('div');

                // Find elements that likely contain messages
                for (let el of elements) {
                    const text = el.textContent?.trim() || '';
                    if (text.length > 10 && text.length < 500) {
                        const classes = el.className || '';
                        const role = el.getAttribute('role') || '';
                        const testid = el.getAttribute('data-testid') || '';

                        // Check for WhatsApp patterns
                        if (classes.includes('_') || testid || role === 'log') {
                            messages.push({
                                classes: classes.substring(0, 100),
                                role: role,
                                testid: testid,
                                textPreview: text.substring(0, 50)
                            });
                        }
                    }
                }

                return messages.slice(0, 10); // Return first 10
            }
        """)

        print("Potential message structures found:")
        for idx, msg in enumerate(structure):
            print(f"\n  Structure #{idx + 1}:")
            print(f"    Classes: {msg['classes']}")
            print(f"    Role: {msg['role']}")
            print(f"    Test ID: {msg['testid']}")
            print(f"    Text: {msg['textPreview']}")

        print("\n" + "="*70)
        print("RECOMMENDED NEXT STEPS:")
        print("="*70)
        print("Based on this analysis, you should:")
        print("1. Update the selectors in src/watchers/whatsapp_watcher.py")
        print("2. Test the new selectors with: python test_whatsapp_watcher.py")

        await asyncio.sleep(2)
        await context.close()

if __name__ == "__main__":
    asyncio.run(inspect_chat())
