"""
Ralph Wiggum Persistence Loop - Continuous autonomous task completion.

Monitors /Needs_Action and /Approved folders continuously, automatically
processing pending items until /Needs_Action is empty. Updates Dashboard.md
for every action.

Name Origin: Ralph Wiggum from The Simpsons - known for persistence
("I'm helping!") despite challenges.

Safety Rules:
- Never performs "Sensitive Actions" without human approval
- All outbound actions require HITL via /Pending_Approval -> /Approved
- Updates Dashboard.md for every action taken
- Logs all actions to audit trail
"""
import asyncio
import logging
import threading
from pathlib import Path
from datetime import datetime
from typing import Optional, Set
import time

from ..config.settings import settings
from ..utils.file_utils import ensure_directory_exists
from ..utils.security import is_safe_path
from .dashboard_updater import DashboardUpdater
from .logging_service import AuditLogger
from ..models.agent_state import AgentStatus
from ..models.trigger_file import TriggerFile, TriggerStatus

logger = logging.getLogger(__name__)


class PersistenceLoop:
    """Ralph Wiggum persistence loop for autonomous task completion.

    Continuously monitors task folders and processes items until Needs_Action
    is empty. This is the "persistence daemon" that keeps the AI employee
    working autonomously within safe boundaries.

    Safety: This loop only processes tasks in /Needs_Action (input monitoring)
    and /Approved (approved actions). It NEVER creates actions that bypass
    the human approval workflow.
    """

    def __init__(
        self,
        poll_interval: int = 30,
        needs_action_dir: Optional[Path] = None,
        approved_dir: Optional[Path] = None,
        done_dir: Optional[Path] = None,
        dashboard_path: Optional[Path] = None
    ):
        """Initialize the persistence loop.

        Args:
            poll_interval: Seconds between poll cycles (default: 30)
            needs_action_dir: Path to /Needs_Action folder
            approved_dir: Path to /Approved folder
            done_dir: Path to /Done folder
            dashboard_path: Path to Dashboard.md
        """
        self.poll_interval = poll_interval
        self.needs_action_dir = Path(needs_action_dir or settings.NEEDS_ACTION_PATH)
        self.approved_dir = Path(approved_dir or settings.APPROVED_PATH)
        self.done_dir = Path(done_dir or settings.DONE_PATH)
        self.failed_dir = Path(settings.FAILED_PATH)
        self.dashboard_path = Path(dashboard_path or settings.DASHBOARD_PATH)

        # Ensure directories exist
        ensure_directory_exists(self.needs_action_dir)
        ensure_directory_exists(self.approved_dir)
        ensure_directory_exists(self.done_dir)
        ensure_directory_exists(self.failed_dir)

        # Tracking
        self.processed_items: Set[str] = set()
        self.running = False
        self.stats = {
            'needs_action_count': 0,
            'approved_count': 0,
            'done_count': 0,
            'total_processed': 0,
            'last_update': None
        }

        # Services
        self.dashboard_updater = DashboardUpdater()
        self.audit_logger = AuditLogger()

        logger.info(
            "Ralph Wiggum persistence loop initialized (poll every %s sec)",
            poll_interval
        )

    def _count_files(self, directory: Path) -> int:
        """Count markdown files in directory."""
        try:
            return len(list(directory.glob("*.md")))
        except Exception:
            return 0

    def _get_needs_action_items(self) -> list[Path]:
        """Get list of pending task files."""
        try:
            return sorted(self.needs_action_dir.glob("*.md"), key=lambda p: p.stat().st_mtime)
        except Exception as e:
            logger.error("Error listing Needs_Action: %s", e)
            return []

    def _get_approved_items(self) -> list[Path]:
        """Get list of approved action files."""
        try:
            return sorted(self.approved_dir.glob("*.md"), key=lambda p: p.stat().st_mtime)
        except Exception as e:
            logger.error("Error listing Approved: %s", e)
            return []

    def _process_needs_action_item(self, item_path: Path) -> bool:
        """Process a single item from /Needs_Action.

        For items in /Needs_Action, we create drafts for approval.
        This is NOT a sensitive action - it's preparing work for human review.

        Args:
            item_path: Path to the task file

        Returns:
            True if processing succeeded, False otherwise
        """
        try:
            # Read the task file
            content = item_path.read_text(encoding='utf-8')
            item_id = item_path.stem

            # Determine task type from frontmatter or filename
            task_type = "unknown"
            if "GMAIL_" in item_id:
                task_type = "email"
            elif "WHATSAPP_" in item_id or "WhatsApp" in content:
                task_type = "whatsapp"
            elif "TRIGGER_" in item_id:
                task_type = "file"
            elif "type: email" in content:
                task_type = "email"
            elif "type: whatsapp" in content:
                task_type = "whatsapp"

            logger.info("Processing %s task: %s", task_type, item_id)

            # Import appropriate processor
            if task_type == "email":
                from ..agents.email_processor import EmailProcessor
                processor = EmailProcessor()
            elif task_type == "whatsapp":
                from ..agents.email_processor import EmailProcessor
                processor = EmailProcessor()  # Use email processor as base
            else:
                from ..agents.file_processor import FileProcessor
                processor = FileProcessor()

            # Create trigger file
            trigger_file = TriggerFile(
                id=item_id,
                filename=item_path.name,
                type=task_type,
                source_path=str(item_path),
                status=TriggerStatus.PENDING,
                timestamp=datetime.now(),
                location=str(item_path)
            )

            # Process the trigger
            success = processor.process_trigger_file(trigger_file)

            # Move to Done if successful (to prevent re-processing)
            if success:
                from .file_mover import FileMover
                file_mover = FileMover()
                done_path = self.done_dir / item_path.name
                
                # Check for existing file to avoid name collision
                if done_path.exists():
                    timestamp = datetime.now().strftime("%H%M%S")
                    done_path = self.done_dir / f"{item_path.stem}_{timestamp}{item_path.suffix}"
                
                try:
                    item_path.rename(done_path)
                    logger.info("Moved processed item to Done: %s", item_path.name)
                except Exception as me:
                    logger.error("Failed to move processed item to Done: %s", me)
            else:
                # Move to Failed if processing failed but didn't throw exception
                try:
                    failed_path = self.failed_dir / item_path.name
                    item_path.rename(failed_path)
                    logger.warning("Moved unsuccessful item to Failed: %s", item_path.name)
                except Exception as fe:
                    logger.error("Could not move unsuccessful item to Failed: %s", fe)

            # Log the action
            if success:
                 print(f"✅ Drafted reply for {item_path.name} → Moved to Pending_Approval.")
                 logger.info(f"✅ Drafted reply for {item_path.name} → Moved to Pending_Approval.")
            else:
                 print(f"❌ Failed to process {item_path.name} → Moved to Failed.")
                 logger.error(f"❌ Failed to process {item_path.name} → Moved to Failed.")

            self.audit_logger.log(
                event="process_needs_action",
                data={
                    "resource": str(item_path),
                    "status": "success" if success else "failure",
                    "task_type": task_type,
                    "item_id": item_id,
                    "moved_to_done": success
                }
            )

            # Update dashboard
            try:
                status = "DONE" if success else "FAILED"
                self.dashboard_updater.append_entry(
                    f"Processed {task_type} task: {item_id}",
                    status
                )
            except Exception as de:
                logger.warning("Failed to update dashboard: %s", de)

            return success

        except Exception as e:
            logger.error("Error processing Needs_Action item %s: %s", item_path, e)
            
            # Move to Failed to prevent infinite retry loop
            try:
                failed_path = self.failed_dir / item_path.name
                item_path.rename(failed_path)
                logger.warning("Moved failing item to Failed: %s", item_path.name)
            except Exception as fe:
                logger.error("Critical: Could not move failing item to Failed: %s", fe)

            self.audit_logger.log(
                event="process_needs_action",
                data={
                    "resource": str(item_path),
                    "status": "error",
                    "error": str(e)
                }
            )
            return False

    def _process_approved_item(self, item_path: Path) -> bool:
        """Process a single approved action from /Approved.

        For items in /Approved, we execute the approved action.
        This IS a sensitive action, but it has been pre-approved by human.

        Args:
            item_path: Path to the approved draft file

        Returns:
            True if execution succeeded, False otherwise
        """
        try:
            # Read the approved draft
            content = item_path.read_text(encoding='utf-8')
            item_id = item_path.stem

            logger.info("Executing approved action: %s", item_id)

            # Use action executor to process approved actions
            from ..services.action_executor import ActionExecutor
            from ..services.file_mover import FileMover

            executor = ActionExecutor()
            file_mover = FileMover()

            # Execute the action
            success = executor.execute(item_path)

            # Move to Done if successful
            if success:
                done_path = self.done_dir / item_path.name
                if is_safe_path(str(done_path), str(self.done_dir)):
                    item_path.rename(done_path)
                    logger.info("Moved approved item to Done: %s", item_id)

            # Log the action
            if success:
                print(f"🚀 Executed Action for {item_path.name} → SUCCESS")
                logger.info(f"🚀 Executed Action for {item_path.name} → SUCCESS")
            else:
                print(f"❌ Failed to execute {item_path.name}")
                logger.error(f"❌ Failed to execute {item_path.name}")

            self.audit_logger.log(
                event="execute_approved",
                data={
                    "resource": str(item_path),
                    "status": "success" if success else "failure",
                    "item_id": item_id,
                    "moved_to_done": success
                }
            )

            # Update dashboard
            try:
                status = "EXECUTED" if success else "FAILED"
                action_type = "Approved action"
                if "email" in content.lower():
                    action_type = "Email sent"
                elif "linkedin" in content.lower():
                    action_type = "LinkedIn post published"
                elif "whatsapp" in content.lower():
                    action_type = "WhatsApp message sent"

                self.dashboard_updater.append_entry(
                    f"{action_type}: {item_id}",
                    status
                )
            except Exception as de:
                logger.warning("Failed to update dashboard: %s", de)

            return success

        except Exception as e:
            logger.error("Error executing approved item %s: %s", item_path, e)
            self.audit_logger.log(
                event="execute_approved",
                data={
                    "resource": str(item_path),
                    "status": "error",
                    "error": str(e)
                }
            )
            return False

    def _update_stats(self) -> None:
        """Update statistics counters."""
        self.stats['needs_action_count'] = self._count_files(self.needs_action_dir)
        self.stats['approved_count'] = self._count_files(self.approved_dir)
        self.stats['done_count'] = self._count_files(self.done_dir)
        self.stats['last_update'] = datetime.now()

        logger.debug(
            "Stats - Needs_Action: %d, Approved: %d, Done: %d, Total Processed: %d",
            self.stats['needs_action_count'],
            self.stats['approved_count'],
            self.stats['done_count'],
            self.stats['total_processed']
        )

    def _update_dashboard_summary(self) -> None:
        """Update Dashboard.md with current system state."""
        try:
            # Create or update dashboard summary section
            summary = f"""## System Summary
**Last Updated**: {self.stats['last_update'].strftime('%Y-%m-%d %H:%M:%S')}

| Folder | Count | Status |
|--------|-------|--------|
| /Needs_Action | {self.stats['needs_action_count']} | {'⚠️ Items pending' if self.stats['needs_action_count'] > 0 else '✓ Empty'} |
| /Approved | {self.stats['approved_count']} | {'⏳ Awaiting execution' if self.stats['approved_count'] > 0 else '✓ Empty'} |
| /Done | {self.stats['done_count']} | Completed |

**Total Processed**: {self.stats['total_processed']}

---

"""

            # Check if dashboard exists
            if self.dashboard_path.exists():
                existing = self.dashboard_path.read_text(encoding='utf-8')

                if "## System Summary" in existing:
                    # Split into parts: before summary, summary, and after summary
                    parts = existing.split("## System Summary")
                    before_summary = parts[0]
                    rest = parts[1]
                    
                    # Find where the next section starts (if any)
                    # We look for the next "## " that isn't part of the summary table
                    summary_end_marker = "---"
                    if summary_end_marker in rest:
                        after_summary_parts = rest.split(summary_end_marker, 1)
                        after_summary = summary_end_marker + after_summary_parts[1]
                    else:
                        # Fallback: if no marker, check if there's another header
                        header_index = rest.find("\n## ")
                        if header_index != -1:
                            after_summary = rest[header_index:]
                        else:
                            after_summary = "\n\n## Recent Activity\n" # Default if everything was lost
                    
                    new_content = before_summary + "## System Summary\n" + summary + after_summary
                    self.dashboard_path.write_text(new_content, encoding='utf-8')
                else:
                    # Add summary at top and ensure we have an activity section
                    new_content = "# AI Employee Dashboard\n\n" + "## System Summary\n" + summary + "\n## Recent Activity\n" + existing
                    self.dashboard_path.write_text(new_content, encoding='utf-8')
            else:
                # Create new dashboard
                self.dashboard_path.write_text(
                    f"""# AI Employee Dashboard

{summary}
## Recent Activity
"""
                )

            logger.debug("Dashboard summary updated")

        except Exception as e:
            logger.error("Failed to update dashboard summary: %s", e)

    def _run_one_cycle(self) -> None:
        """Run one complete cycle of the persistence loop."""
        logger.info("Ralph Wiggum cycle started...")

        # Process Needs_Action items
        needs_action_items = self._get_needs_action_items()
        processed_count = 0

        for item_path in needs_action_items:
            if str(item_path) not in self.processed_items:
                if self._process_needs_action_item(item_path):
                    self.processed_items.add(str(item_path))
                    processed_count += 1
                    self.stats['total_processed'] += 1

        # Process Approved items
        approved_items = self._get_approved_items()
        executed_count = 0

        for item_path in approved_items:
            if str(item_path) not in self.processed_items:
                if self._process_approved_item(item_path):
                    self.processed_items.add(str(item_path))
                    executed_count += 1
                    self.stats['total_processed'] += 1

        # Update stats and dashboard
        self._update_stats()
        self._update_dashboard_summary()

        # Log cycle completion
        if processed_count > 0 or executed_count > 0:
            logger.info(
                "Cycle complete - Processed: %d drafts created, %d actions executed",
                processed_count,
                executed_count
            )
        else:
            # Silent heartbeat or simplified log if nothing happened
            pass

        # Check if Needs_Action is empty
        if self.stats['needs_action_count'] == 0 and self.stats['approved_count'] == 0:
             # Only log this occasionally or if verbose to reduce noise
             pass

    def start(self) -> None:
        """Start the persistence loop.

        This is a blocking call that runs until self.running is False.
        For background operation, run in a separate thread.
        """
        self.running = True

        logger.info("Ralph Wiggum persistence loop started")
        logger.info("   Monitoring: %s", self.needs_action_dir)
        logger.info("   Executing: %s", self.approved_dir)
        logger.info("   Updating: %s", self.dashboard_path)

        # Initial update
        self._update_stats()
        self._update_dashboard_summary()

        # Main loop
        while self.running:
            try:
                self._run_one_cycle()
            except Exception as e:
                logger.error("Persistence loop error: %s", e)

            time.sleep(self.poll_interval)

        logger.info("Ralph Wiggum persistence loop stopped")

    def stop(self) -> None:
        """Stop the persistence loop."""
        logger.info("Stopping Ralph Wiggum persistence loop...")
        self.running = False

    def get_status(self) -> dict:
        """Get current status of the persistence loop."""
        return {
            'running': self.running,
            'stats': self.stats,
            'processed_items_count': len(self.processed_items)
        }


def _run_in_thread(poll_interval: int = 30) -> threading.Thread:
    """Run the persistence loop in a background thread.

    Args:
        poll_interval: Seconds between poll cycles

    Returns:
        Thread object
    """
    loop = PersistenceLoop(poll_interval=poll_interval)
    thread = threading.Thread(target=loop.start, daemon=True)
    thread.start()
    return thread


if __name__ == "__main__":
    # Run persistence loop synchronously for testing
    import argparse

    parser = argparse.ArgumentParser(description="Ralph Wiggum Persistence Loop")
    parser.add_argument(
        "--interval",
        type=int,
        default=30,
        help="Poll interval in seconds (default: 30)"
    )
    args = parser.parse_args()

    logger.info("Starting Ralph Wiggum persistence loop with %d second interval", args.interval)
    loop = PersistenceLoop(poll_interval=args.interval)

    try:
        loop.start()
    except KeyboardInterrupt:
        logger.info("Persistence loop stopped by user")
        loop.stop()