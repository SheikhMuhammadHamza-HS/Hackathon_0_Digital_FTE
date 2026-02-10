import argparse
import sys
from pathlib import Path
import threading
import signal
import time
from typing import Optional

from ..config.settings import settings
from ..services.file_mover import FileMover
from ..services.trigger_generator import TriggerGenerator
from ..models.agent_state import AgentStateManager, AgentStatus
from ..watchers.filesystem_watcher import FileWatcher
from ..watchers.gmail_watcher import GmailWatcher
from ..watchers.approval_watcher import ApprovalWatcher
from ..services.scheduler import Scheduler
from ..utils.file_utils import ensure_directory_exists
from ..config.logging_config import get_logger

logger = get_logger(__name__)


class AgentCLI:
    """Command-line interface for the agent."""

    def __init__(self, state_file: Optional[str] = None):
        self.watcher: Optional[FileWatcher] = None
        state_file_path = state_file or settings.AGENT_STATE_PATH
        self.agent_state_manager = AgentStateManager(state_file_path)
        self.running = False

    def setup(self, args):
        """Initialize the agent environment with required folder structure."""
        print("Setting up Minimum Viable Agent environment...")

        # Validate configuration
        errors = settings.validate()
        if errors:
            print("Configuration errors found:")
            for error in errors:
                print(f"  - {error}")
            return False

        # Create required directories
        required_dirs = [
            settings.INBOX_PATH,
            settings.NEEDS_ACTION_PATH,
            settings.DONE_PATH,
            settings.LOGS_PATH
        ]

        print("Creating directory structure...")
        dir_results = FileMover.ensure_directory_structure(required_dirs)

        all_success = True
        for dir_path, success in dir_results.items():
            status = "✓" if success else "✗"
            print(f"  {status} {dir_path}")
            if not success:
                all_success = False

        if not all_success:
            print("Some directories could not be created.")
            return False

        # Create initial dashboard file
        print("Creating initial dashboard...")
        success = TriggerGenerator.create_initial_dashboard(str(settings.DASHBOARD_PATH))
        if not success:
            print(f"✗ Failed to create dashboard at {settings.DASHBOARD_PATH}")
            return False
        print(f"✓ Dashboard created at {settings.DASHBOARD_PATH}")

        # Create company handbook
        print("Creating company handbook...")
        success = TriggerGenerator.create_company_handbook(str(settings.COMPANY_HANDBOOK_PATH))
        if not success:
            print(f"✗ Failed to create company handbook at {settings.COMPANY_HANDBOOK_PATH}")
            return False
        print(f"✓ Company handbook created at {settings.COMPANY_HANDBOOK_PATH}")

        print("\nAgent environment setup completed successfully!")
        return True

    def start(self, args):
        """Start the agent to begin monitoring Gmail and local files."""
        if self.running:
            print("Agent is already running.")
            return

        print("Starting agent...")

        # Update agent state
        self.agent_state_manager.update_status(AgentStatus.MONITORING)

        # Initialise Gmail and Approval watchers (run in background threads)
        try:
            gmail_watcher = GmailWatcher()
            gmail_thread = threading.Thread(target=gmail_watcher.start, daemon=True)
            gmail_thread.start()
            print("Gmail watcher started in background thread.")

            approval_watcher = ApprovalWatcher()
            approval_thread = threading.Thread(target=approval_watcher.start, daemon=True)
            approval_thread.start()
            print("Approval watcher started in background thread.")
        except Exception as e:
            logger.error(f"Failed to start background watchers: {str(e)}")
            print(f"Failed to start background watchers: {str(e)}")

        # Create and start the file watcher
        try:
            self.watcher = FileWatcher(
                watch_path=settings.INBOX_PATH,
                needs_action_path=settings.NEEDS_ACTION_PATH,
                done_path=settings.DONE_PATH,
                dashboard_path=settings.DASHBOARD_PATH,
                file_size_limit=settings.FILE_SIZE_LIMIT,
                max_retry_attempts=settings.MAX_RETRY_ATTEMPTS
            )

            self.running = True
            print("Agent started successfully. Monitoring for new files...")

            # Start the watcher (this blocks)
            try:
                self.watcher.start_watching()
            except KeyboardInterrupt:
                self.stop(None)
            except Exception as e:
                logger.error(f"Watcher error: {str(e)}")
                self.stop(None)

        except Exception as e:
            logger.error(f"Error starting agent: {str(e)}")
            print(f"Error starting agent: {str(e)}")
            return False

    def schedule_run(self, args):
        """Execute scheduled LinkedIn draft jobs.

        If ``--once`` is provided, run pending jobs once and exit.
        Otherwise, start the background scheduler thread.
        """
        scheduler = Scheduler()
        if getattr(args, 'once', False):
            print("Running scheduled jobs once...")
            scheduler.run_once()
            print('Scheduled jobs executed once.')
        else:
            print('Starting scheduler (background thread)...')
            scheduler.start()
            print('Scheduler started in background. Press Ctrl+C to stop.')
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print('Scheduler stopped by user.')

    def stop(self, args):
        """Stop the agent gracefully."""
        if not self.running:
            print("Agent is not running.")
            return
        print("\nStopping agent...")
        self.running = False
        if self.watcher:
            try:
                self.watcher.stop_watching()
            except Exception as e:
                logger.error(f"Error stopping watcher: {e}")
        try:
            self.agent_state_manager.update_status(AgentStatus.IDLE)
        except Exception:
            pass
        print("Agent stopped.")

    def start_with_graceful_shutdown(self, args):
        """Start the agent with ability to gracefully handle shutdown."""
        self.start(args)

    def status(self, args):
        """Show current agent status."""
        state = self.agent_state_manager.get_state()

        print("Agent Status:")
        print(f"  Status: {state.status.value}")
        print(f"  Last Processed: {state.last_processed}")
        print(f"  Files Processed Today: {state.files_processed_today}")
        print(f"  Error Count: {state.errors_count}")
        print(f"  Active Watchers: {state.active_watchers}")
        print(f"  Last Updated: {state.last_updated}")

    def process_trigger(self, args):
        """Manually process a specific trigger file."""
        if not hasattr(args, 'trigger_file_path') or not args.trigger_file_path:
            print("Error: Please specify a trigger file path with --trigger-file-path")
            return

        print(f"Manually processing trigger file: {args.trigger_file_path}")

        from ..services.trigger_generator import TriggerGenerator
        from ..agents.file_processor import FileProcessor

        trigger_file = TriggerGenerator.load_trigger_from_file(args.trigger_file_path)

        if not trigger_file:
            print(f"Error: Could not load trigger file: {args.trigger_file_path}")
            return

        processor = FileProcessor()
        success = processor.process_file_with_exponential_backoff(
            trigger_file,
            max_attempts=settings.MAX_RETRY_ATTEMPTS
        )

        if success:
            print(f"Successfully processed trigger file: {args.trigger_file_path}")
        else:
            print(f"Failed to process trigger file: {args.trigger_file_path}")


def main():
    """Main entry point for the CLI."""
    cli = AgentCLI()

    parser = argparse.ArgumentParser(description="Minimum Viable Agent CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Setup command
    setup_parser = subparsers.add_parser("setup", help="Initialize agent environment")
    setup_parser.set_defaults(func=cli.setup)

    # Start command
    start_parser = subparsers.add_parser("start", help="Start the agent")
    start_parser.set_defaults(func=cli.start)

    # Stop command
    stop_parser = subparsers.add_parser("stop", help="Stop the agent")
    stop_parser.set_defaults(func=cli.stop)

    status_parser = subparsers.add_parser("status", help="Show agent status")
    status_parser.set_defaults(func=cli.status)

    # Schedule run command
    schedule_parser = subparsers.add_parser("schedule-run", help="Run scheduled jobs (LinkedIn drafts) now or start scheduler")
    schedule_parser.add_argument("--once", action="store_true", help="Execute pending jobs once and exit (useful for testing)")
    schedule_parser.set_defaults(func=cli.schedule_run)

    # Approval watch command (new)
    approval_parser = subparsers.add_parser("approval-watch", help="Watch Approved folder and execute drafts")
    approval_parser.set_defaults(func=lambda args: ApprovalWatcher().start())
    process_trigger_parser = subparsers.add_parser("process-trigger", help="Manually process a trigger file")
    process_trigger_parser.add_argument("--trigger-file-path", type=str, help="Path to the trigger file to process")
    process_trigger_parser.set_defaults(func=cli.process_trigger)

    # Parse arguments
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()