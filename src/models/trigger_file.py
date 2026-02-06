from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional
from enum import Enum
import yaml
import json
from src.utils.file_utils import sanitize_filename


class TriggerStatus(Enum):
    """Enumeration of possible trigger file statuses."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class TriggerFile:
    """Represents a detected file event that initiates processing."""

    # Corresponds to file metadata id
    id: str
    # Filename in TRIGGER_{timestamp}.md format
    filename: str
    # Always "file_drop" for this agent
    type: str
    # Path to the file that triggered this
    source_path: str
    # ISO-8601 formatted timestamp
    timestamp: datetime
    # Current processing status
    status: TriggerStatus
    # Path to the trigger file in /Needs_Action
    location: str

    @classmethod
    def create_from_file_event(
        cls,
        trigger_id: str,
        source_path: str,
        needs_action_dir: str
    ) -> 'TriggerFile':
        """
        Create TriggerFile instance from a file event.

        Args:
            trigger_id: ID for the trigger
            source_path: Path to the file that triggered this
            needs_action_dir: Directory for trigger files

        Returns:
            TriggerFile instance
        """
        timestamp = datetime.now()
        filename = f"TRIGGER_{timestamp.strftime('%Y%m%d%H%M%S%f')[:-3]}.md"
        location = str(Path(needs_action_dir) / filename)

        return cls(
            id=trigger_id,
            filename=filename,
            type="file_drop",
            source_path=source_path,
            timestamp=timestamp,
            status=TriggerStatus.PENDING,
            location=location
        )

    def to_file_content(self) -> str:
        """
        Generate the content for the trigger file in YAML front matter format.

        Returns:
            String content for the trigger file
        """
        yaml_frontmatter = f"""---
type: "{self.type}"
source_path: "{self.source_path}"
timestamp: "{self.timestamp.isoformat()}"
status: "{self.status.value}"
---
## Context
File detected in Inbox.
"""
        return yaml_frontmatter

    def save_to_disk(self) -> bool:
        """
        Save the trigger file to disk.

        Returns:
            Boolean indicating success of the operation
        """
        try:
            path = Path(self.location)
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(self.to_file_content())
            return True
        except Exception as e:
            print(f"Error saving trigger file {self.location}: {str(e)}")
            return False

    def update_status(self, new_status: TriggerStatus) -> bool:
        """
        Update the status of the trigger file and save it.

        Args:
            new_status: New status to set

        Returns:
            Boolean indicating success of the operation
        """
        try:
            self.status = new_status
            # Update the timestamp in the file content as well
            # Read existing content, update status, and rewrite
            path = Path(self.location)
            if path.exists():
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Update status in the YAML front matter
                lines = content.split('\n')
                updated_lines = []
                in_yaml_block = False
                for line in lines:
                    if line.strip() == '---' and not in_yaml_block:
                        in_yaml_block = True
                        updated_lines.append(line)
                    elif line.strip() == '---' and in_yaml_block:
                        in_yaml_block = False
                        updated_lines.append(line)
                    elif in_yaml_block and line.startswith('status:'):
                        updated_lines.append(f'status: "{new_status.value}"')
                    else:
                        updated_lines.append(line)

                with open(path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(updated_lines))

            return True
        except Exception as e:
            print(f"Error updating trigger file status {self.location}: {str(e)}")
            return False

    def to_dict(self) -> dict:
        """
        Convert TriggerFile to dictionary representation.

        Returns:
            Dictionary representation of the TriggerFile
        """
        return {
            'id': self.id,
            'filename': self.filename,
            'type': self.type,
            'source_path': self.source_path,
            'timestamp': self.timestamp.isoformat(),
            'status': self.status.value,
            'location': self.location
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'TriggerFile':
        """
        Create TriggerFile from dictionary representation.

        Args:
            data: Dictionary representation of TriggerFile

        Returns:
            TriggerFile instance
        """
        return cls(
            id=data['id'],
            filename=data['filename'],
            type=data['type'],
            source_path=data['source_path'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            status=TriggerStatus(data['status']),
            location=data['location']
        )

    @classmethod
    def load_from_file(cls, file_path: str) -> Optional['TriggerFile']:
        """
        Load TriggerFile from an existing trigger file.

        Args:
            file_path: Path to the trigger file

        Returns:
            TriggerFile instance or None if loading fails
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Extract YAML front matter
            lines = content.split('\n')
            if len(lines) < 3 or lines[0] != '---':
                return None

            # Find the end of YAML front matter
            yaml_end_idx = -1
            for i in range(1, len(lines)):
                if lines[i] == '---':
                    yaml_end_idx = i
                    break

            if yaml_end_idx == -1:
                return None

            yaml_content = '\n'.join(lines[1:yaml_end_idx])
            yaml_data = yaml.safe_load(yaml_content)

            # Create TriggerFile instance
            trigger_file = cls(
                id=yaml_data.get('id', ''),
                filename=Path(file_path).name,
                type=yaml_data.get('type', ''),
                source_path=yaml_data.get('source_path', ''),
                timestamp=datetime.fromisoformat(yaml_data.get('timestamp', datetime.now().isoformat())),
                status=TriggerStatus(yaml_data.get('status', 'pending')),
                location=file_path
            )

            return trigger_file
        except Exception as e:
            print(f"Error loading trigger file from {file_path}: {str(e)}")
            return None