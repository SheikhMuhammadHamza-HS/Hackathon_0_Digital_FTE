from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional
from enum import Enum
import uuid

class FileStatus(Enum):
    """Enumeration of possible file processing statuses."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class FileMetadata:
    """Represents metadata about files being processed by the agent."""

    # Primary identifier
    id: str
    # Absolute path to original file
    original_path: Path
    # Folder where file originated
    source_folder: Path
    # Where file will be moved upon completion
    destination_folder: Path
    # Size in bytes
    file_size: int
    # Determined file type
    file_type: str
    # Current processing status
    status: FileStatus
    # Timestamp when file was detected
    created_at: datetime
    # Timestamp when processing completed (optional)
    processed_at: Optional[datetime] = None
    # Path to corresponding trigger file (optional)
    trigger_file_path: Optional[Path] = None
    # Duration of processing in seconds (optional)
    processing_duration: Optional[float] = None

    @classmethod
    def create_from_file(
        cls,
        original_path: Path,
        source_folder: Path,
        destination_folder: Path,
        trigger_file_path: Optional[Path] = None
    ) -> 'FileMetadata':
        """
        Create FileMetadata instance from a file path.

        Args:
            original_path: Path to the original file
            source_folder: Folder where file originated
            destination_folder: Folder where file will be moved upon completion
            trigger_file_path: Optional path to corresponding trigger file

        Returns:
            FileMetadata instance
        """
        # Calculate file size
        file_size = original_path.stat().st_size

        # Determine file type
        from src.utils.file_utils import get_file_type
        file_type = get_file_type(original_path)

        # Create new ID
        file_id = str(uuid.uuid4())

        # Get creation time
        created_at = datetime.now()

        return cls(
            id=file_id,
            original_path=original_path,
            source_folder=source_folder,
            destination_folder=destination_folder,
            file_size=file_size,
            file_type=file_type,
            status=FileStatus.PENDING,
            created_at=created_at,
            trigger_file_path=trigger_file_path
        )

    def mark_processing(self) -> None:
        """Update status to processing."""
        self.status = FileStatus.PROCESSING

    def mark_completed(self, processing_duration: Optional[float] = None) -> None:
        """Update status to completed."""
        self.status = FileStatus.COMPLETED
        self.processed_at = datetime.now()
        if processing_duration is not None:
            self.processing_duration = processing_duration

    def mark_failed(self) -> None:
        """Update status to failed."""
        self.status = FileStatus.FAILED
        self.processed_at = datetime.now()

    def validate_size(self, max_size: int) -> bool:
        """
        Validate if file size is within the allowed limit.

        Args:
            max_size: Maximum allowed file size in bytes

        Returns:
            Boolean indicating if file size is valid
        """
        return self.file_size <= max_size

    def to_dict(self) -> dict:
        """
        Convert FileMetadata to dictionary representation.

        Returns:
            Dictionary representation of the FileMetadata
        """
        return {
            'id': self.id,
            'original_path': str(self.original_path),
            'source_folder': str(self.source_folder),
            'destination_folder': str(self.destination_folder),
            'file_size': self.file_size,
            'file_type': self.file_type,
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'processed_at': self.processed_at.isoformat() if self.processed_at else None,
            'trigger_file_path': str(self.trigger_file_path) if self.trigger_file_path else None,
            'processing_duration': self.processing_duration
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'FileMetadata':
        """
        Create FileMetadata from dictionary representation.

        Args:
            data: Dictionary representation of FileMetadata

        Returns:
            FileMetadata instance
        """
        return cls(
            id=data['id'],
            original_path=Path(data['original_path']),
            source_folder=Path(data['source_folder']),
            destination_folder=Path(data['destination_folder']),
            file_size=data['file_size'],
            file_type=data['file_type'],
            status=FileStatus(data['status']),
            created_at=datetime.fromisoformat(data['created_at']),
            processed_at=datetime.fromisoformat(data['processed_at']) if data['processed_at'] else None,
            trigger_file_path=Path(data['trigger_file_path']) if data['trigger_file_path'] else None,
            processing_duration=data.get('processing_duration')
        )