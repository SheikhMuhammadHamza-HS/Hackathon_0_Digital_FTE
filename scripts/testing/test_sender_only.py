"""
  Simple test for WhatsApp sender only.
  Run this to test if Playwright sending works without the full workflow.
  """
import logging
from pathlib import Path
from src.agents.whatsapp_sender import WhatsAppSender

logging.basicConfig(
      level=logging.INFO,
      format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
  )

def test_send():
      # Create a test draft file
      draft_content = """Subject: WhatsApp Reply to Test Contact
  Platform: whatsapp
  To: Test Number 

  Hi! This is a test message from your AI assistant.
  """

      # Save to Approved folder
      approved_dir = Path("Approved")
      approved_dir.mkdir(exist_ok=True)

      draft_path = approved_dir / "TEST_SEND_2026-02-17.md"
      draft_path.write_text(draft_content, encoding='utf-8')

      print("=" * 60)
      print("TESTING WHATSAPP SENDER")
      print("=" * 60)
      print(f"Draft file created: {draft_path}")
      print()
      print("This will:")
      print("1. Open a browser window")
      print("2. Navigate to WhatsApp Web")
      print("3. Ask you to scan QR code (if not already logged in)")
      print("4. Search for contact: +1 (555) 170-9841")
      print("5. Send the test message")
      print()
      input("Press ENTER to start...")

      # Initialize sender in playwright mode
      sender = WhatsAppSender(mode="playwright")

      # Try to send
      result = sender.send_draft(draft_path)

      print()
      print("=" * 60)
      if result:
          print("✅ SUCCESS: Message sent!")
      else:
          print("❌ FAILED: Could not send message")
      print("=" * 60)

if __name__ == "__main__":
      test_send()