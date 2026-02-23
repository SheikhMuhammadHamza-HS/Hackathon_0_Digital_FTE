import asyncio
import logging
import sys
import os
import warnings
from pathlib import Path
from datetime import datetime

# Setup path
sys.path.insert(0, str(Path(__file__).parent))

# Suppress warnings
warnings.filterwarnings("ignore", category=FutureWarning, module="google.generativeai")
warnings.filterwarnings("ignore", message=".*file_cache is only supported with oauth2client.*")
os.environ["GOOGLE_API_USE_CLIENT_CERTIFICATE"] = "false"

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
        gmail_watcher = GmailWatcher(poll_interval=15)
        logger.info("[OK] Gmail Watcher initialized")
    except Exception as e:
        logger.error(f"Failed to initialize Gmail Watcher: {e}")
        return

    # 2. Initialize Approval Watcher (to send approved emails)
    try:
        approval_watcher = ApprovalWatcher(poll_interval=10)
        logger.info("[OK] Approval Watcher initialized")
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
        # Use absolute path from project root
        approved_path = Path(settings.BASE_DIR) / settings.APPROVED_PATH
        approved_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"[SENDER] Looking in: {approved_path}")
        files = list(approved_path.glob("*.md"))
        logger.info(f"[SENDER] Found {len(files)} approved files")
        for path in files:
            if path.is_file() and path.suffix == ".md":
                logger.info(f"[SENDER] Found approved file: {path.name}")
                approval_watcher._process_file(path)

        logger.info(f"[INFO] Waiting 15 seconds for next cycle...")
        await asyncio.sleep(15)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Agent stopped by user.")
