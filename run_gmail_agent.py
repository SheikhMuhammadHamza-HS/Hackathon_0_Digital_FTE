import asyncio
import logging
import sys
import os
from pathlib import Path
from datetime import datetime

# Setup path
sys.path.insert(0, str(Path(__file__).parent))

from src.watchers.gmail_watcher import GmailWatcher
from src.watchers.approval_watcher import ApprovalWatcher
from src.agents.email_processor import EmailProcessor
from src.config.settings import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("GmailAgent")

async def main():
    logger.info("="*60)
    logger.info("GMAIL AUTOMATION AGENT STARTING")
    logger.info("="*60)

    # 1. Initialize Gmail Watcher
    try:
        gmail_watcher = GmailWatcher(poll_interval=30)
        logger.info("✓ Gmail Watcher initialized")
    except Exception as e:
        logger.error(f"Failed to initialize Gmail Watcher: {e}")
        return

    # 2. Initialize Approval Watcher (to send approved emails)
    try:
        approval_watcher = ApprovalWatcher(poll_interval=10)
        logger.info("✓ Approval Watcher initialized")
    except Exception as e:
        logger.error(f"Failed to initialize Approval Watcher: {e}")
        return

    # 3. Running loop
    cycle = 0
    while True:
        cycle += 1
        logger.info(f"\n--- CYCLE #{cycle} ---")
        
        # Poll for new unread emails
        logger.info("[WATCHER] Polling for unread emails...")
        new_emails = gmail_watcher.poll_unread()
        if new_emails:
            logger.info(f"[WATCHER] Found and processed {len(new_emails)} new emails.")

        # Check for approved drafts to send
        logger.info("[SENDER] Checking for approved drafts...")
        # ApprovalWatcher.start is blocking, so we'll run its core logic manually here
        # to keep it in a single loop for this test agent.
        for path in Path(settings.APPROVED_PATH).iterdir():
            if path.is_file() and path.suffix == ".md":
                logger.info(f"[SENDER] Found approved file: {path.name}")
                approval_watcher._process_file(path)

        await asyncio.sleep(30)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Agent stopped by user.")
