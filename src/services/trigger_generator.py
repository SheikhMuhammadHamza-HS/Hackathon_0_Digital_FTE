import os
from pathlib import Path
from datetime import datetime
from typing import Optional
import uuid
from ..models.trigger_file import TriggerFile, TriggerStatus
from ..exceptions import TriggerCreationException


class TriggerGenerator:
    """Creates trigger files in /Needs_Action."""

    @staticmethod
    def create_trigger_file(
        source_path: str,
        needs_action_dir: str,
        trigger_id: Optional[str] = None
    ) -> Optional[TriggerFile]:
        """
        Create a trigger file in the Needs_Action directory.

        Args:
            source_path: Path to the original file that triggered this
            needs_action_dir: Directory where trigger files should be created
            trigger_id: Optional ID for the trigger (generated if not provided)

        Returns:
            TriggerFile instance or None if creation fails
        """
        try:
            # Ensure the needs_action directory exists
            Path(needs_action_dir).mkdir(parents=True, exist_ok=True)

            # Generate trigger ID if not provided
            if trigger_id is None:
                trigger_id = str(uuid.uuid4())

            # Create the trigger file object
            trigger_file = TriggerFile.create_from_file_event(
                trigger_id=trigger_id,
                source_path=source_path,
                needs_action_dir=needs_action_dir
            )

            # Save the trigger file to disk
            success = trigger_file.save_to_disk()
            if not success:
                raise TriggerCreationException(f"Failed to save trigger file to {trigger_file.location}")

            return trigger_file
        except Exception as e:
            raise TriggerCreationException(f"Error creating trigger file for {source_path}: {str(e)}")

    @staticmethod
    def update_trigger_status(trigger_file: TriggerFile, new_status: TriggerStatus) -> bool:
        """
        Update the status of an existing trigger file.

        Args:
            trigger_file: TriggerFile object to update
            new_status: New status to set

        Returns:
            Boolean indicating success of the operation
        """
        try:
            return trigger_file.update_status(new_status)
        except Exception as e:
            raise TriggerCreationException(f"Error updating trigger file status: {str(e)}")

    @staticmethod
    def generate_timestamped_filename(prefix: str = "TRIGGER") -> str:
        """
        Generate a timestamped filename in the format PREFIX_yyyymmddhhmmssfff.md.

        Args:
            prefix: Prefix for the filename (default: "TRIGGER")

        Returns:
            Generated filename
        """
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S%f')[:-3]  # Include milliseconds
        return f"{prefix}_{timestamp}.md"

    @staticmethod
    def validate_trigger_file_path(file_path: str) -> tuple[bool, str]:
        """
        Validate that a file path is a valid trigger file path.

        Args:
            file_path: Path to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            path = Path(file_path)
            if not path.exists():
                return False, f"File does not exist: {file_path}"

            # Check if it's a markdown file
            if path.suffix.lower() != '.md':
                return False, f"Not a markdown file: {file_path}"

            # Check if it has the trigger pattern
            if not path.name.startswith('TRIGGER_'):
                return False, f"Not a trigger file (doesn't start with TRIGGER_): {file_path}"

            # Check if it has a valid timestamp pattern (should be TRIGGER_yyyymmddhhmmssfff.md)
            name_parts = path.name.split('_')
            if len(name_parts) < 2:
                return False, f"Invalid trigger file name format: {file_path}"

            timestamp_part = name_parts[1].split('.')[0]  # Remove .md extension
            # Try to parse the timestamp part
            try:
                # Expected format: yyyymmddhhmmssfff
                parsed_date = datetime.strptime(timestamp_part, '%Y%m%d%H%M%S%f')
            except ValueError:
                try:
                    # Try shorter format: yyyymmddhhmmss
                    parsed_date = datetime.strptime(timestamp_part, '%Y%m%d%H%M%S')
                except ValueError:
                    return False, f"Invalid timestamp format in trigger file: {file_path}"

            return True, ""
        except Exception as e:
            return False, f"Error validating trigger file path {file_path}: {str(e)}"

    @staticmethod
    def load_trigger_from_file(file_path: str) -> Optional[TriggerFile]:
        """
        Load a TriggerFile from an existing file.

        Args:
            file_path: Path to the trigger file

        Returns:
            TriggerFile instance or None if loading fails
        """
        return TriggerFile.load_from_file(file_path)

    @staticmethod
    def create_initial_dashboard(dashboard_path: str) -> bool:
        """
        Create an initial dashboard file if it doesn't exist.

        Args:
            dashboard_path: Path where dashboard should be created

        Returns:
            Boolean indicating success of the operation
        """
        try:
            path = Path(dashboard_path)
            if not path.exists():
                path.parent.mkdir(parents=True, exist_ok=True)

                initial_content = """# Agent Dashboard

| Time | Task | Status |
|------|------|--------|
"""
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(initial_content)

            return True
        except Exception as e:
            print(f"Error creating initial dashboard at {dashboard_path}: {str(e)}")
            return False

    @staticmethod
    def create_company_handbook(company_handbook_path: str) -> bool:
        """
        Create a default company handbook file if it doesn't exist.

        Args:
            company_handbook_path: Path where handbook should be created

        Returns:
            Boolean indicating success of the operation
        """
        try:
            path = Path(company_handbook_path)
            if not path.exists():
                path.parent.mkdir(parents=True, exist_ok=True)

                handbook_content = """# Company Handbook

## Agent Behaviors

This document defines the rules and behaviors for the Digital FTE agent.

### File Processing Rules

1. **File Detection**: Monitor `/Inbox` for new files every 5 seconds
2. **File Types**: Process only supported file types (PDF, DOCX, TXT, XLSX, PPTX, JPG, PNG, GIF)
3. **Size Limit**: Reject files larger than 10MB
4. **Processing**: Create trigger in `/Needs_Action`, update dashboard, move to `/Done`
5. **Error Handling**: Retry failed processing up to 3 times with exponential backoff
6. **Security**: Log all file access for audit purposes

### Dashboard Updates

- Update dashboard in real-time when files are processed
- Show timestamp, filename, and processing status
- Track processing duration for performance monitoring

### Fallback Procedures

- If Claude Code API is unavailable, queue files for later processing
- Log all errors for diagnostic purposes
- Notify user if processing fails repeatedly
"""
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(handbook_content)

            return True
        except Exception as e:
            print(f"Error creating company handbook at {company_handbook_path}: {str(e)}")
            return False