import time
import threading
from pathlib import Path
from typing import Callable, Optional
from watchdog.observers.polling import PollingObserver as Observer
from watchdog.events import FileSystemEventHandler
import logging
from datetime import datetime
import os

from ..config.settings import settings
from ..models.file_metadata import FileMetadata, FileStatus
from ..models.trigger_file import TriggerFile, TriggerStatus
from ..services.file_mover import FileMover
from ..services.trigger_generator import TriggerGenerator
from ..utils.file_utils import (
    validate_file_size, is_supported_file_type,
    get_file_type, ensure_directory_exists
)
from ..exceptions import (
    FileProcessingException, FileSizeLimitException,
    UnsupportedFileTypeException, TriggerCreationException
)
from ..agents.file_processor import FileProcessor
from ..models.agent_state import AgentStateManager, AgentStatus
from ..models.dashboard import DashboardManager, DashboardEntry
from ..config.logging_config import get_logger


logger = get_logger(__name__)


class FileWatchHandler(FileSystemEventHandler):
    """Handles file system events for the watched directory."""

    def __init__(
        self,
        needs_action_path: Path,
        done_path: Path,
        dashboard_path: Path,
        file_size_limit: int,
        max_retry_attempts: int
    ):
        """
        Initialize the file watch handler.

        Args:
            needs_action_path: Path to the Needs_Action directory
            done_path: Path to the Done directory
            dashboard_path: Path to the dashboard file
            file_size_limit: Maximum file size allowed
            max_retry_attempts: Maximum number of retry attempts for failed processing
        """
        self.needs_action_path = Path(needs_action_path)
        self.done_path = Path(done_path)
        self.dashboard_path = Path(dashboard_path)
        self.file_size_limit = file_size_limit
        self.max_retry_attempts = max_retry_attempts
        self.file_processor = FileProcessor()
        self.dashboard_manager = DashboardManager(str(dashboard_path))
        self.agent_state_manager = AgentStateManager()

        # Ensure required directories exist
        ensure_directory_exists(self.needs_action_path)
        ensure_directory_exists(self.done_path)

    def on_created(self, event):
        """Handle file creation events."""
        import time
        time.sleep(0.5) # Wait for file to settle
        if event.is_directory:
            return

        file_path = Path(event.src_path)

        try:
            logger.info(f"Detected new file: {file_path}")

            # Validate file size
            is_valid, error_msg = validate_file_size(file_path, self.file_size_limit)
            if not is_valid:
                logger.error(f"File size validation failed: {error_msg}")
                raise FileSizeLimitException(error_msg)

            # Check if file type is supported
            if not is_supported_file_type(file_path):
                file_type = get_file_type(file_path)
                error_msg = f"Unsupported file type: {file_type} for file {file_path}"
                logger.error(error_msg)
                raise UnsupportedFileTypeException(error_msg)

            # Create file metadata
            file_metadata = FileMetadata.create_from_file(
                original_path=file_path,
                source_folder=file_path.parent,
                destination_folder=self.done_path
            )

            # Mark as processing
            file_metadata.mark_processing()
            self.agent_state_manager.increment_processed_count()

            # Create trigger file
            trigger_file = TriggerGenerator.create_trigger_file(
                source_path=str(file_path),
                needs_action_dir=str(self.needs_action_path),
                trigger_id=file_metadata.id
            )

            if trigger_file is None:
                raise TriggerCreationException(f"Failed to create trigger for {file_path}")

            logger.info(f"Created trigger file: {trigger_file.location}")

            # Process the file using Claude Code
            success = self.process_file_with_claude(file_metadata, trigger_file)

            if success:
                # Update status and move file
                file_metadata.mark_completed()

                # Create dashboard entry
                dashboard_entry = DashboardEntry.create_from_metadata(
                    file_id=file_metadata.id,
                    display_name=file_path.name,
                    timestamp=datetime.now(),
                    status="Done",
                    duration=file_metadata.processing_duration,
                    file_type=file_metadata.file_type
                )

                self.dashboard_manager.add_entry(dashboard_entry)
                self.dashboard_manager.update_dashboard_file()

                # Move the original file to Done folder
                done_file_path = self.done_path / file_path.name
                FileMover.move_file(file_path, done_file_path)

                logger.info(f"Successfully processed and moved file: {file_path} -> {done_file_path}")
            else:
                logger.error(f"Failed to process file: {file_path}")
                file_metadata.mark_failed()

        except FileSizeLimitException as e:
            logger.error(f"File size limit exceeded: {str(e)}")
        except UnsupportedFileTypeException as e:
            logger.error(f"Unsupported file type: {str(e)}")
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {str(e)}")

    def process_file_with_claude(self, file_metadata: FileMetadata, trigger_file: TriggerFile) -> bool:
        """
        Process the file using Claude Code integration.

        Args:
            file_metadata: Metadata for the file being processed
            trigger_file: Trigger file to process

        Returns:
            Boolean indicating success of the processing
        """
        try:
            # Initialize the file processor
            file_processor = FileProcessor()

            # Process the trigger file with Claude Code
            success = file_processor.process_file_with_exponential_backoff(
                trigger_file,
                max_attempts=self.max_retry_attempts
            )

            if success:
                # Update trigger status to completed
                trigger_file.update_status(TriggerStatus.COMPLETED)
            else:
                # Update trigger status to failed
                trigger_file.update_status(TriggerStatus.FAILED)

            return success
        except Exception as e:
            logger.error(f"Error in Claude Code processing: {str(e)}")
            try:
                # Update trigger status to failed in case of error
                trigger_file.update_status(TriggerStatus.FAILED)
            except Exception:
                pass  # Ignore errors when updating status if original processing failed
            return False


class FileWatcher:
    """Watches a directory for new files and processes them."""

    def __init__(
        self,
        watch_path: Path,
        needs_action_path: Path,
        done_path: Path,
        dashboard_path: Path,
        file_size_limit: int,
        max_retry_attempts: int
    ):
        """
        Initialize the file watcher.

        Args:
            watch_path: Directory to watch for new files
            needs_action_path: Directory for trigger files
            done_path: Directory for processed files
            dashboard_path: Path to dashboard file
            file_size_limit: Maximum file size allowed
            max_retry_attempts: Maximum number of retry attempts
        """
        self.watch_path = watch_path
        self.needs_action_path = needs_action_path
        self.done_path = done_path
        self.dashboard_path = dashboard_path
        self.file_size_limit = file_size_limit
        self.max_retry_attempts = max_retry_attempts

        # Ensure directories exist
        ensure_directory_exists(self.watch_path)
        ensure_directory_exists(self.needs_action_path)
        ensure_directory_exists(self.done_path)

        self.observer = Observer()
        self.handler = FileWatchHandler(
            needs_action_path=self.needs_action_path,
            done_path=self.done_path,
            dashboard_path=self.dashboard_path,
            file_size_limit=file_size_limit,
            max_retry_attempts=max_retry_attempts
        )
        self.running = False

    def start_watching(self):
        """Start watching the directory for new files."""
        if self.running:
            logger.warning("File watcher is already running")
            return

        # Schedule the event handler
        self.observer.schedule(self.handler, str(self.watch_path), recursive=False)

        # Process any existing files present at start
        for existing_file in Path(self.watch_path).iterdir():
            if existing_file.is_file():
                class DummyEvent:
                    def __init__(self, path):
                        self.src_path = str(path)
                        self.is_directory = False
                self.handler.on_created(DummyEvent(existing_file))

        # Process any existing files in the watch directory before starting observer
        if Path(self.watch_path).exists():
            for existing_path in Path(self.watch_path).iterdir():
                if existing_path.is_file():
                    class SimpleEvent:
                        def __init__(self, src_path):
                            self.src_path = str(src_path)
                            self.is_directory = False
                    event = SimpleEvent(existing_path)
                    self.handler.on_created(event)
        # Process any existing files in the watch directory before starting observer
        if Path(self.watch_path).exists():
            for existing_path in Path(self.watch_path).iterdir():
                if existing_path.is_file():
                    class SimpleEvent:
                        def __init__(self, src_path):
                            self.src_path = str(src_path)
                            self.is_directory = False
                    event = SimpleEvent(existing_path)
                    self.handler.on_created(event)
        # Start the observer
        try:
            self.observer.start()
        except FileNotFoundError:
            logger.warning(f"Watch path {self.watch_path} not found; observer not started.")
        self.running = True

        logger.info(f"Started watching directory: {self.watch_path}")

        try:
            # Keep the watcher running
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Received interrupt signal, stopping watcher...")
            self.stop_watching()

    def stop_watching(self):
        """Stop watching the directory."""
        if not self.running:
            return

        logger.info("Stopping file watcher...")
        self.running = False
        self.observer.stop()
        self.observer.join(timeout=5)  # Wait up to 5 seconds for clean shutdown

        logger.info("File watcher stopped")