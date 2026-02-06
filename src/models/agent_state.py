from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
from enum import Enum
import json
import threading
from pathlib import Path


class AgentStatus(Enum):
    """Enumeration of possible agent statuses."""
    IDLE = "idle"
    MONITORING = "monitoring"
    PROCESSING = "processing"
    PAUSED = "paused"
    ERROR = "error"


@dataclass
class AgentState:
    """Tracks the current operational state of the agent."""

    # Singleton identifier
    id: str = "current_state"
    # Current agent status
    status: AgentStatus = AgentStatus.IDLE
    # Timestamp of last processed file
    last_processed: Optional[datetime] = None
    # Count of files processed today
    files_processed_today: int = 0
    # Count of errors since last restart
    errors_count: int = 0
    # Currently monitored directories
    active_watchers: List[str] = None
    # Timestamp of state creation/update
    last_updated: datetime = None

    def __post_init__(self):
        """Initialize mutable defaults."""
        if self.active_watchers is None:
            self.active_watchers = []
        if self.last_updated is None:
            self.last_updated = datetime.now()

    def update_status(self, new_status: AgentStatus) -> None:
        """Update the agent status."""
        self.status = new_status
        self.last_updated = datetime.now()

    def increment_processed_count(self) -> None:
        """Increment the files processed count."""
        self.files_processed_today += 1
        self.last_processed = datetime.now()
        self.last_updated = datetime.now()

    def increment_error_count(self) -> None:
        """Increment the error count."""
        self.errors_count += 1
        self.last_updated = datetime.now()

    def add_watcher(self, directory: str) -> None:
        """Add a directory to the list of active watchers."""
        if directory not in self.active_watchers:
            self.active_watchers.append(directory)
        self.last_updated = datetime.now()

    def remove_watcher(self, directory: str) -> None:
        """Remove a directory from the list of active watchers."""
        if directory in self.active_watchers:
            self.active_watchers.remove(directory)
        self.last_updated = datetime.now()

    def reset_daily_counter(self) -> None:
        """Reset the daily processed file counter."""
        self.files_processed_today = 0
        self.last_updated = datetime.now()

    def to_dict(self) -> dict:
        """
        Convert AgentState to dictionary representation.

        Returns:
            Dictionary representation of the AgentState
        """
        return {
            'id': self.id,
            'status': self.status.value,
            'last_processed': self.last_processed.isoformat() if self.last_processed else None,
            'files_processed_today': self.files_processed_today,
            'errors_count': self.errors_count,
            'active_watchers': self.active_watchers,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'AgentState':
        """
        Create AgentState from dictionary representation.

        Args:
            data: Dictionary representation of AgentState

        Returns:
            AgentState instance
        """
        return cls(
            id=data['id'],
            status=AgentStatus(data['status']),
            last_processed=datetime.fromisoformat(data['last_processed']) if data['last_processed'] else None,
            files_processed_today=data['files_processed_today'],
            errors_count=data['errors_count'],
            active_watchers=data['active_watchers'],
            last_updated=datetime.fromisoformat(data['last_updated']) if data['last_updated'] else datetime.now()
        )

    def save_to_file(self, state_file_path: str) -> bool:
        """
        Save the agent state to a file.

        Args:
            state_file_path: Path to the state file

        Returns:
            Boolean indicating success of the operation
        """
        try:
            # Ensure directory exists
            path = Path(state_file_path)
            path.parent.mkdir(parents=True, exist_ok=True)

            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self.to_dict(), f, indent=2)

            return True
        except Exception as e:
            print(f"Error saving agent state to {state_file_path}: {str(e)}")
            return False

    @classmethod
    def load_from_file(cls, state_file_path: str) -> Optional['AgentState']:
        """
        Load agent state from a file.

        Args:
            state_file_path: Path to the state file

        Returns:
            AgentState instance or None if loading fails
        """
        try:
            with open(state_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            return cls.from_dict(data)
        except FileNotFoundError:
            # Return a default state if file doesn't exist
            return cls()
        except Exception as e:
            print(f"Error loading agent state from {state_file_path}: {str(e)}")
            return None


class AgentStateManager:
    """Thread-safe manager for the agent state."""

    def __init__(self, state_file: str = "./agent_state.json"):
        """
        Initialize the agent state manager.

        Args:
            state_file: Path to persist the agent state
        """
        self.state_file = state_file
        self.lock = threading.Lock()
        self.state = AgentState.load_from_file(self.state_file) or AgentState()

    def get_state(self) -> AgentState:
        """Get the current agent state (thread-safe)."""
        with self.lock:
            return self.state

    def update_status(self, new_status: AgentStatus) -> bool:
        """Update the agent status (thread-safe)."""
        with self.lock:
            self.state.update_status(new_status)
            return self.state.save_to_file(self.state_file)

    def increment_processed_count(self) -> bool:
        """Increment the processed file count (thread-safe)."""
        with self.lock:
            self.state.increment_processed_count()
            return self.state.save_to_file(self.state_file)

    def increment_error_count(self) -> bool:
        """Increment the error count (thread-safe)."""
        with self.lock:
            self.state.increment_error_count()
            return self.state.save_to_file(self.state_file)

    def add_watcher(self, directory: str) -> bool:
        """Add a watcher to the state (thread-safe)."""
        with self.lock:
            self.state.add_watcher(directory)
            return self.state.save_to_file(self.state_file)

    def remove_watcher(self, directory: str) -> bool:
        """Remove a watcher from the state (thread-safe)."""
        with self.lock:
            self.state.remove_watcher(directory)
            return self.state.save_to_file(self.state_file)

    def reset_daily_counter(self) -> bool:
        """Reset the daily counter (thread-safe)."""
        with self.lock:
            self.state.reset_daily_counter()
            return self.state.save_to_file(self.state_file)

    def save_state(self) -> bool:
        """Save the current state to file (thread-safe)."""
        with self.lock:
            return self.state.save_to_file(self.state_file)