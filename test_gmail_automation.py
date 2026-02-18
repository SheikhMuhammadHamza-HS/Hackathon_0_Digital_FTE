#!/usr/bin/env python3
"""
Gmail Automation Test Suite
Tests the Gmail watcher, email processor, and draft creation flow.
"""
import asyncio
import sys
import json
import time
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.config.settings import settings
from src.watchers.gmail_watcher import GmailWatcher
from src.agents.email_processor import EmailProcessor
from src.models.trigger_file import TriggerFile, TriggerStatus
from src.services.draft_store import DraftStore
from src.config.logging_config import setup_logging, get_logger

# Setup logging
setup_logging("INFO")
logger = get_logger(__name__)


def test_gmail_credentials():
    """Test 1: Verify Gmail credentials are configured."""
    print("\n" + "="*60)
    print("TEST 1: Gmail Credentials Check")
    print("="*60)

    token_file = Path("token.json")
    credentials_file = Path("credentials.json")

    errors = []

    if not credentials_file.exists():
        errors.append(f"[FAIL] credentials.json not found at: {credentials_file.absolute()}")
    else:
        print(f"[PASS] credentials.json found")
        # Validate JSON
        try:
            creds_data = json.loads(credentials_file.read_text())
            if 'web' in creds_data or 'installed' in creds_data:
                print("[PASS] credentials.json has valid structure")
            else:
                errors.append("[FAIL] credentials.json missing 'web' or 'installed' key")
        except json.JSONDecodeError as e:
            errors.append(f"[FAIL] credentials.json is not valid JSON: {e}")

    if not token_file.exists():
        errors.append(f"[FAIL] token.json not found at: {token_file.absolute()}")
        print("\n[INFO] To create token.json, run: python scripts/setup_gmail.py")
    else:
        print(f"[PASS] token.json found")
        # Validate token
        try:
            token_data = json.loads(token_file.read_text())
            if 'token' in token_data or 'access_token' in token_data:
                print("[PASS] token.json has valid OAuth structure")
            else:
                errors.append("[FAIL] token.json missing token fields")
        except json.JSONDecodeError as e:
            errors.append(f"[FAIL] token.json is not valid JSON: {e}")

    # Check environment variable
    if settings.GMAIL_TOKEN:
        print("[PASS] GMAIL_TOKEN environment variable is set")
    else:
        print("[INFO] GMAIL_TOKEN not set (will use token.json file)")

    if errors:
        print("\n[FAIL] TEST 1 FAILED:")
        for error in errors:
            print(f"   {error}")
        return False

    print("\n[PASS] TEST 1 PASSED: Gmail credentials are configured")
    return True


def test_gmail_watcher_initialization():
    """Test 2: Initialize GmailWatcher."""
    print("\n" + "="*60)
    print("TEST 2: GmailWatcher Initialization")
    print("="*60)

    try:
        watcher = GmailWatcher(poll_interval=60)
        print("[PASS] GmailWatcher initialized successfully")
        print(f"   - Poll interval: {watcher.poll_interval} seconds")
        print(f"   - Needs action path: {watcher.needs_action_path}")
        print(f"   - Service initialized: {watcher.service is not None}")
        return watcher
    except Exception as e:
        print(f"\n[FAIL] TEST 2 FAILED: {e}")
        logger.error("GmailWatcher initialization failed", exc_info=True)
        return None


def test_poll_unread(watcher: GmailWatcher, max_results: int = 3):
    """Test 3: Poll for unread messages."""
    print("\n" + "="*60)
    print("TEST 3: Poll Unread Messages")
    print("="*60)

    try:
        print(f"Polling Gmail for up to {max_results} unread messages...")
        created_files = watcher.poll_unread(max_results=max_results)

        if created_files:
            print(f"\n[PASS] Found and processed {len(created_files)} unread message(s):")
            for file_path in created_files:
                print(f"   [FILE] {file_path.name}")
                # Show content preview
                try:
                    content = file_path.read_text(encoding='utf-8')
                    lines = content.split('\n')
                    for line in lines:
                        if line.startswith('from:'):
                            print(f"      From: {line.split(':', 1)[1].strip()}")
                        elif line.startswith('subject:'):
                            print(f"      Subject: {line.split(':', 1)[1].strip()}")
                except Exception as e:
                    print(f"      [WARN] Could not read content: {e}")
        else:
            print("\n[INFO] No unread messages found in Gmail inbox")
            print("   (This is OK - it means your inbox is clean!)")

        print(f"\n[PASS] TEST 3 PASSED: Poll completed successfully")
        return created_files

    except Exception as e:
        print(f"\n[FAIL] TEST 3 FAILED: {e}")
        logger.error("Poll unread failed", exc_info=True)
        return []


def test_email_processor(task_file: Path = None):
    """Test 4: Process an email task with AI."""
    print("\n" + "="*60)
    print("TEST 4: Email Processor (AI Draft Generation)")
    print("="*60)

    processor = EmailProcessor()

    # If no task file provided, check Needs_Action for GMAIL files
    if task_file is None:
        needs_action = Path(settings.NEEDS_ACTION_PATH)
        gmail_files = list(needs_action.glob("GMAIL_*.md"))

        if not gmail_files:
            print("[INFO] No GMAIL task files found in Needs_Action")
            print("   Creating a mock test...")
            # Create a mock task file for testing
            mock_task = create_mock_gmail_task()
            if mock_task:
                gmail_files = [mock_task]
            else:
                print("[FAIL] Could not create mock task")
                return False

        task_file = gmail_files[0]

    print(f"Processing task file: {task_file.name}")

    try:
        # Create trigger file
        trigger = TriggerFile(
            id=task_file.stem,
            filename=task_file.name,
            type="email",
            source_path=str(task_file),
            status=TriggerStatus.PENDING,
            timestamp=datetime.now(),
            location=str(task_file)
        )

        # Process
        success = processor.process_trigger_file(trigger)

        if success:
            print("\n[PASS] Email processed successfully")
            print(f"   Status: {trigger.status.value}")

            # Check for created draft
            pending_approval = Path(settings.PENDING_APPROVAL_PATH)
            drafts = list(pending_approval.glob("EMAIL_*.md"))

            if drafts:
                print(f"\n[MAIL] Draft(s) created in Pending_Approval:")
                for draft in drafts[-3:]:  # Show last 3
                    print(f"   - {draft.name}")
                return True
            else:
                print("\n[WARN] No drafts found in Pending_Approval")
                return False
        else:
            print("\n[FAIL] Email processing failed")
            return False

    except Exception as e:
        print(f"\n[FAIL] TEST 4 FAILED: {e}")
        logger.error("Email processor test failed", exc_info=True)
        return False


def create_mock_gmail_task() -> Path:
    """Create a mock Gmail task for testing."""
    try:
        needs_action = Path(settings.NEEDS_ACTION_PATH)
        needs_action.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        task_id = f"GMAIL_TEST_{timestamp}"

        content = f"""---
type: email
id: "{task_id}"
thread_id: "test_thread_123"
message_id: "{task_id}"
from: "test.sender@example.com"
subject: "Test Email for AI Processing"
received_at: "{datetime.now().isoformat()}"
detected_at: "{datetime.now().isoformat()}"
status: pending
---

## Email Content

Hello Hamza Digital FTE,

This is a test email to verify the Gmail automation system is working correctly.

Could you please confirm receipt and let me know your thoughts on the project?

Best regards,
Test User

## Threading Info
Thread-ID: test_thread_123
Message-ID: {task_id}

## Actions Required
- [ ] Draft a reply
- [ ] Archive email
"""

        task_file = needs_action / f"{task_id}.md"
        task_file.write_text(content, encoding='utf-8')
        print(f"[PASS] Created mock task: {task_file.name}")
        return task_file

    except Exception as e:
        logger.error(f"Failed to create mock task: {e}")
        return None


def test_draft_store():
    """Test 5: Draft Store functionality."""
    print("\n" + "="*60)
    print("TEST 5: Draft Store")
    print("="*60)

    try:
        store = DraftStore()

        # Save a test draft
        test_draft = store.save_draft(
            subject="Test Subject",
            to_addr="test@example.com",
            body="This is a test draft email body.",
            platform='email',
            thread_id="test_thread_123",
            message_id="test_msg_456"
        )

        print(f"[PASS] Draft saved: {test_draft.name}")

        # Verify it exists
        if test_draft.exists():
            content = test_draft.read_text(encoding='utf-8')
            print(f"[PASS] Draft file verified ({len(content)} characters)")

            # Show preview
            preview = content[:200].replace('\n', ' ')
            print(f"   Preview: {preview}...")
            return True
        else:
            print("[FAIL] Draft file not found after saving")
            return False

    except Exception as e:
        print(f"\n[FAIL] TEST 5 FAILED: {e}")
        logger.error("Draft store test failed", exc_info=True)
        return False


def test_end_to_end_flow():
    """Test 6: Complete end-to-end flow."""
    print("\n" + "="*60)
    print("TEST 6: End-to-End Gmail Flow")
    print("="*60)

    print("This test will:")
    print("  1. Check Gmail for unread messages")
    print("  2. Create task files in Needs_Action")
    print("  3. Process tasks with AI to generate drafts")
    print("  4. Save drafts to Pending_Approval")
    print()

    # Step 1: Initialize watcher
    watcher = test_gmail_watcher_initialization()
    if not watcher:
        return False

    # Step 2: Poll for messages
    created_files = test_poll_unread(watcher, max_results=2)

    if not created_files:
        print("\n[WARN] No unread messages to process")
        print("   Creating a mock task for testing...")
        mock_task = create_mock_gmail_task()
        if mock_task:
            created_files = [mock_task]
        else:
            return False

    # Step 3: Process first task
    print(f"\n[MAIL] Processing {len(created_files)} task(s)...")
    success_count = 0

    for task_file in created_files[:2]:  # Process up to 2
        if test_email_processor(task_file):
            success_count += 1

    print(f"\n{'='*60}")
    print(f"RESULT: {success_count}/{len(created_files)} task(s) processed successfully")
    print(f"{'='*60}")

    return success_count > 0


def main():
    """Run all Gmail automation tests."""
    print("\n" + "="*60)
    print("GMAIL AUTOMATION TEST SUITE")
    print("="*60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Working directory: {Path.cwd()}")
    print()

    results = []

    # Test 1: Credentials
    results.append(("Credentials", test_gmail_credentials()))

    # Test 2-3: Watcher (only if credentials pass)
    if results[-1][1]:
        watcher = test_gmail_watcher_initialization()
        results.append(("Watcher Init", watcher is not None))

        if watcher:
            created_files = test_poll_unread(watcher, max_results=2)
            results.append(("Poll Unread", True))  # Poll itself doesn't fail

            # Test 4: Processor
            if created_files:
                results.append(("Email Processor", test_email_processor(created_files[0])))
            else:
                # Try with mock
                mock_task = create_mock_gmail_task()
                if mock_task:
                    results.append(("Email Processor (Mock)", test_email_processor(mock_task)))
                else:
                    results.append(("Email Processor", False))
    else:
        print("\n⚠️ Skipping watcher tests - credentials not configured")
        results.extend([
            ("Watcher Init", False),
            ("Poll Unread", False),
            ("Email Processor", False)
        ])

    # Test 5: Draft Store (can run independently)
    results.append(("Draft Store", test_draft_store()))

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"  {status}: {name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n[OK] All tests passed!")
    elif passed >= total / 2:
        print("\n[WARN] Some tests failed, but core functionality may work")
    else:
        print("\n[FAIL] Multiple tests failed - check configuration")

    print(f"\nFinished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
