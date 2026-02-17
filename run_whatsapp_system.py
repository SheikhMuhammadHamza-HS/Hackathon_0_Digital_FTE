#!/usr/bin/env python3
"""
Complete WhatsApp AI Employee System

Runs both:
1. WhatsApp Watcher - Detects incoming messages
2. Persistence Loop - Processes tasks and sends responses

Usage:
    python run_whatsapp_system.py
"""
import sys
import time
import threading
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('Logs/whatsapp_system.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


def run_watcher():
    """Run WhatsApp watcher in background."""
    from src.watchers.whatsapp_watcher_simple import WhatsAppWatcherSimple

    logger.info("Starting WhatsApp Watcher...")
    watcher = WhatsAppWatcherSimple()

    try:
        watcher.run_continuous(interval=30)  # Scan every 30 seconds
    except Exception as e:
        logger.error(f"Watcher error: {e}")


def run_processor():
    """Run persistence loop for processing."""
    from src.services.persistence_loop import PersistenceLoop

    logger.info("Starting Persistence Loop...")
    loop = PersistenceLoop(poll_interval=30)

    try:
        loop.start()
    except Exception as e:
        logger.error(f"Processor error: {e}")


def main():
    """Main entry point."""
    print("="*70)
    print(" WhatsApp AI Employee System")
    print("="*70)
    print()
    print("This system will:")
    print("1. Monitor your WhatsApp for incoming messages")
    print("2. Create plans and draft responses")
    print("3. Wait for your approval (move to /Approved)")
    print("4. Send approved responses automatically")
    print()
    print("Requirements:")
    print("- WhatsApp Web login (scan QR on first run)")
    print("- Files in /Pending_Approval need manual approval")
    print("- Move approved files to /Approved folder")
    print()
    print("="*70)
    print()

    # Ensure directories exist
    from src.config.settings import settings
    from src.utils.file_utils import ensure_directory_exists

    for path in [settings.NEEDS_ACTION_PATH, settings.PENDING_APPROVAL_PATH,
                 settings.APPROVED_PATH, settings.DONE_PATH, settings.LOGS_PATH]:
        ensure_directory_exists(Path(path))

    # Start both threads
    watcher_thread = threading.Thread(target=run_watcher, daemon=True)
    processor_thread = threading.Thread(target=run_processor, daemon=True)

    watcher_thread.start()
    time.sleep(2)  # Let watcher start first
    processor_thread.start()

    logger.info("Both services started!")
    logger.info("- Watcher: Monitoring WhatsApp messages")
    logger.info("- Processor: Handling tasks and approvals")
    logger.info("")
    logger.info("Workflow:")
    logger.info("1. New message → Needs_Action")
    logger.info("2. AI creates Plan → Plans/")
    logger.info("3. AI creates Draft → Pending_Approval/")
    logger.info("4. YOU move to Approved/")
    logger.info("5. AI sends message → Done/")
    logger.info("")
    logger.info("Press Ctrl+C to stop")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n")
        logger.info("Shutting down...")
        sys.exit(0)


if __name__ == "__main__":
    main()
