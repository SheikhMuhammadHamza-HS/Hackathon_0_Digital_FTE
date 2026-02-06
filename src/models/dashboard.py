from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
from pathlib import Path
import uuid


@dataclass
class DashboardEntry:
    """Represents a processed file in the dashboard."""

    # Reference to original file metadata
    id: str
    # Filename for display purposes
    display_name: str
    # Time when processing completed
    timestamp: datetime
    # Status (Done, Processing, Failed)
    status: str
    # Time taken to process in seconds (optional)
    duration: Optional[float] = None
    # File extension/type
    file_type: Optional[str] = None

    @classmethod
    def create_from_metadata(
        cls,
        file_id: str,
        display_name: str,
        timestamp: datetime,
        status: str,
        duration: Optional[float] = None,
        file_type: Optional[str] = None
    ) -> 'DashboardEntry':
        """
        Create DashboardEntry from file metadata.

        Args:
            file_id: Reference ID to original file
            display_name: Name to display in dashboard
            timestamp: Time when processing completed
            status: Processing status
            duration: Time taken to process (optional)
            file_type: File type (optional)

        Returns:
            DashboardEntry instance
        """
        return cls(
            id=file_id,
            display_name=display_name,
            timestamp=timestamp,
            status=status,
            duration=duration,
            file_type=file_type
        )

    def to_markdown_row(self) -> str:
        """
        Convert dashboard entry to markdown table row.

        Returns:
            String representation as markdown table row
        """
        time_str = self.timestamp.strftime("%H:%M")
        duration_str = f" ({self.duration:.1f}s)" if self.duration else ""

        # Clean the display name to avoid breaking the markdown table
        safe_display_name = self.display_name.replace('|', '/')
        safe_status = self.status.replace('|', '/')

        return f"| {time_str} | {safe_display_name}{duration_str} | {safe_status} |"

    def to_dict(self) -> dict:
        """
        Convert DashboardEntry to dictionary representation.

        Returns:
            Dictionary representation of the DashboardEntry
        """
        return {
            'id': self.id,
            'display_name': self.display_name,
            'timestamp': self.timestamp.isoformat(),
            'status': self.status,
            'duration': self.duration,
            'file_type': self.file_type
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'DashboardEntry':
        """
        Create DashboardEntry from dictionary representation.

        Args:
            data: Dictionary representation of DashboardEntry

        Returns:
            DashboardEntry instance
        """
        return cls(
            id=data['id'],
            display_name=data['display_name'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            status=data['status'],
            duration=data.get('duration'),
            file_type=data.get('file_type')
        )


class DashboardManager:
    """Manages the collection of dashboard entries."""

    def __init__(self, dashboard_path: str = "./Dashboard.md"):
        """
        Initialize dashboard manager.

        Args:
            dashboard_path: Path to the dashboard markdown file
        """
        self.dashboard_path = Path(dashboard_path)
        self.entries: List[DashboardEntry] = []
        # Load any existing entries from the file
        self.load_entries()

    def add_entry(self, entry: DashboardEntry) -> None:
        """
        Add a new entry to the dashboard.

        Args:
            entry: DashboardEntry to add
        """
        self.entries.append(entry)
        # Sort entries by timestamp to keep them in chronological order
        self.entries.sort(key=lambda x: x.timestamp)
        # Update the dashboard file in real-time
        self.update_dashboard_file()

    def update_entry(self, entry_id: str, new_status: str) -> bool:
        """
        Update an existing entry's status.

        Args:
            entry_id: ID of the entry to update
            new_status: New status for the entry

        Returns:
            Boolean indicating success of the operation
        """
        for entry in self.entries:
            if entry.id == entry_id:
                entry.status = new_status
                # Sort entries to maintain chronological order
                self.entries.sort(key=lambda x: x.timestamp)
                # Update the dashboard file in real-time
                return self.update_dashboard_file()

        return False  # Entry not found

    def remove_entry(self, entry_id: str) -> bool:
        """
        Remove an entry from the dashboard.

        Args:
            entry_id: ID of the entry to remove

        Returns:
            Boolean indicating success of the operation
        """
        for i, entry in enumerate(self.entries):
            if entry.id == entry_id:
                del self.entries[i]
                # Update the dashboard file in real-time
                return self.update_dashboard_file()

        return False  # Entry not found

    def get_entry_by_id(self, entry_id: str) -> Optional[DashboardEntry]:
        """
        Get an entry by its ID.

        Args:
            entry_id: ID of the entry to retrieve

        Returns:
            DashboardEntry if found, None otherwise
        """
        for entry in self.entries:
            if entry.id == entry_id:
                return entry
        return None

    def update_dashboard_file(self) -> bool:
        """
        Update the dashboard markdown file with current entries.

        Returns:
            Boolean indicating success of the operation
        """
        try:
            # Ensure the parent directory exists
            self.dashboard_path.parent.mkdir(parents=True, exist_ok=True)

            with open(self.dashboard_path, 'w', encoding='utf-8') as f:
                f.write("# Agent Dashboard\n\n")
                f.write("| Time | Task | Status |\n")
                f.write("|------|------|--------|\n")

                # Write entries in chronological order (oldest first)
                for entry in self.entries:
                    f.write(entry.to_markdown_row() + "\n")

            return True
        except Exception as e:
            print(f"Error updating dashboard file {self.dashboard_path}: {str(e)}")
            return False

    def load_entries(self) -> List[DashboardEntry]:
        """
        Load existing dashboard entries from the file.

        Returns:
            List of existing dashboard entries
        """
        try:
            if not hasattr(self, 'entries'):
                self.entries = []

            # Try to read existing dashboard file to preserve entries
            if self.dashboard_path and Path(self.dashboard_path).exists():
                with open(self.dashboard_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Parse the markdown table to extract existing entries
                lines = content.split('\n')
                entries_found = False

                for line in lines:
                    line = line.strip()
                    # Look for table rows (skip header rows)
                    if line.startswith('|') and not line.startswith('| Time ') and not line.startswith('|------'):
                        parts = [part.strip() for part in line.split('|')]
                        if len(parts) >= 4:  # At least | Time | Task | Status |
                            time_part = parts[1] if len(parts) > 1 else ""
                            task_part = parts[2] if len(parts) > 2 else ""
                            status_part = parts[3] if len(parts) > 3 else ""

                            # Extract file name from task part (remove duration info if present)
                            display_name = task_part
                            if ' (' in task_part and ')' in task_part:
                                display_name = task_part.split(' (')[0]

                            # Create a simple entry with current timestamp if parsing fails
                            # In a real implementation, we'd have more sophisticated parsing
                            entry = DashboardEntry(
                                id=str(uuid.uuid4()),
                                display_name=display_name,
                                timestamp=datetime.now(),
                                status=status_part
                            )
                            self.entries.append(entry)

            return self.entries
        except Exception as e:
            print(f"Error loading dashboard entries from {self.dashboard_path}: {str(e)}")
            return []

    def get_latest_entries(self, count: int = 10) -> List[DashboardEntry]:
        """
        Get the latest N entries from the dashboard.

        Args:
            count: Number of latest entries to return

        Returns:
            List of latest dashboard entries
        """
        sorted_entries = sorted(self.entries, key=lambda x: x.timestamp, reverse=True)
        return sorted_entries[:count]