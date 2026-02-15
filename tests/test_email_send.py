import asyncio
import logging
import sys
import json
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from src.services.mcp_client import get_mcp_manager
from src.config.logging_config import setup_logging
from src.config.settings import settings

# Configure logging
setup_logging("INFO")
logger = logging.getLogger(__name__)

TEST_EMAIL = "apkydaddy897@gmail.com"

async def test_email_reply():
    print(f"\n=== Testing Email Reply Feature for {TEST_EMAIL} ===\n")
    
    manager = get_mcp_manager()
    if not manager:
        print("❌ Failed to initialize MCP Manager")
        return

    email_client = manager.get_client("email-mcp")
    if not email_client:
        print("❌ Failed to initialize email-mcp client")
        return

    try:
        # Step 1: Send Initial Email
        print("1️⃣ Sending initial email...")
        result_1 = email_client.call_tool("send_email", {
            "to": TEST_EMAIL,
            "subject": "MCP Reply Test",
            "body": "This is the first message. Please do not reply manually, this is an automated test."
        })
        
        if not result_1 or result_1.get('isError'):
            print(f"❌ Failed to send initial email: {result_1}")
            return
            
        content_1 = result_1['content'][0]['text']
        print(f"✅ Initial email sent: {content_1}")
        
        # Extract Message ID (Note: The response usually contains the ID, but depending on implementation we might need to parse it)
        # Assuming format "Email sent successfully! Message ID: <ID>"
        import re
        match = re.search(r"Message ID: (\S+)", content_1)
        if not match:
             # If we can't get ID from simple send, we can't reply immediately in this test without fetching.
             # But let's assume valid ID is returned for now or try to fetch list if needed.
             # Actually, Gmail API returns an ID object. Let's see if we can use that.
             print("⚠️ Could not extract Message ID from response string to test reply immediately.")
             print("Skipping reply test for now, but initial send worked.")
             return

        message_id = match.group(1)
        # For a new thread, threadId is often same as messageId or included in response.
        # But we need threadId for reply. Let's assume we can reply to this messageId as threadId for now (often works)
        # Or better, fetch the message details to get the threadId.
        
        # We don't have a 'get_message' tool yet, so we will try using message_id as thread_id (risky but often works for first message)
        # or we just stop here since we proved sending works.
        
        print("\n(Note: To test 'reply', we need the Thread ID which requires Reading capability which we haven't added yet.)")
        print("✅ Send Email Test Complete!")

    except Exception as e:
        print(f"❌ Exception: {e}")
    finally:
        email_client.stop()

if __name__ == "__main__":
    asyncio.run(test_email_reply())
