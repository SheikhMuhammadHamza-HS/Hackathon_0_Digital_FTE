"""
File system monitoring for AI Employee system.

Watches directories for file changes and triggers appropriate
actions based on file types and locations.
"""

import asyncio
import logging
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Callable, Optional, Set, Any
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from enum import Enum
import hashlib
import json
import mimetypes
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent
from concurrent.futures import ThreadPoolExecutor

from ..core.event_bus import get_event_bus, Event
from ..core.config import get_config

logger = logging.getLogger(__name__)


class FileEventType(Enum):
    """File system event types."""
    CREATED = "created"
    MODIFIED = "modified"
    DELETED = "deleted"
    MOVED = "moved"


@dataclass
class FileEvent:
    """File system event data."""
    event_type: FileEventType
    file_path: Path
    is_directory: bool
    timestamp: datetime
    source_path: Optional[Path] = None  # For moved events
    file_size: Optional[int] = None
    file_hash: Optional[str] = None
    mime_type: Optional[str] = None


class FileCreatedEvent(Event):
    """Event fired when a file is created in monitored directory."""
    file_path: str
    file_size: int
    mime_type: str
    source: str = "file_monitor"


class FileModifiedEvent(Event):
    """Event fired when a file is modified in monitored directory."""
    file_path: str
    file_size: int
    mime_type: str
    source: str = "file_monitor"


class FileDeletedEvent(Event):
    """Event fired when a file is deleted from monitored directory."""
    file_path: str
    source: str = "file_monitor"


class FileMovedEvent(Event):
    """Event fired when a file is moved in monitored directory."""
    source_path: str
    destination_path: str
    source: str = "file_monitor"


class SupportedFileTypes:
    """Supported file types for processing."""

    # Document types
    DOCUMENTS = {
        '.pdf', '.doc', '.docx', '.txt', '.rtf', '.odt',
        '.xls', '.xlsx', '.csv', '.ods', '.ppt', '.pptx', '.odp'
    }

    # Image types
    IMAGES = {
        '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'
    }

    # Archive types
    ARCHIVES = {
        '.zip', '.rar', '.7z', '.tar', '.gz', '.bz2'
    }

    # All supported
    ALL = DOCUMENTS | IMAGES | ARCHIVES

    @classmethod
    def is_supported(cls, file_path: Path) -> bool:
        """Check if file type is supported.

        Args:
            file_path: File path to check

        Returns:
            True if supported
        """
        return file_path.suffix.lower() in cls.ALL

    @classmethod
    def get_category(cls, file_path: Path) -> str:
        """Get file category.

        Args:
            file_path: File path

        Returns:
            File category
        """
        suffix = file_path.suffix.lower()
        if suffix in cls.DOCUMENTS:
            return 'document'
        elif suffix in cls.IMAGES:
            return 'image'
        elif suffix in cls.ARCHIVES:
            return 'archive'
        else:
            return 'unknown'


class FileProcessor(ABC):
    """Base class for file processors."""

    def __init__(self, name: str, supported_extensions: Set[str]):
        """Initialize file processor.

        Args:
            name: Processor name
            supported_extensions: Set of supported file extensions
        """
        self.name = name
        self.supported_extensions = supported_extensions

    @abstractmethod
    async def process(self, file_event: FileEvent) -> Dict[str, Any]:
        """Process a file event.

        Args:
            file_event: File event to process

        Returns:
            Processing result
        """
        pass

    def can_process(self, file_path: Path) -> bool:
        """Check if processor can handle file.

        Args:
            file_path: File path

        Returns:
            True if can process
        """
        return file_path.suffix.lower() in self.supported_extensions


class DocumentProcessor(FileProcessor):
    """Processor for document files."""

    def __init__(self):
        """Initialize document processor."""
        super().__init__("document_processor", SupportedFileTypes.DOCUMENTS)

    async def process(self, file_event: FileEvent) -> Dict[str, Any]:
        """Process document file.

        Args:
            file_event: File event

        Returns:
            Processing result
        """
        result = {
            'processor': self.name,
            'file_path': str(file_event.file_path),
            'category': 'document',
            'size': file_event.file_size,
            'mime_type': file_event.mime_type,
            'processed_at': datetime.now(timezone.utc).isoformat()
        }

        # Extract text content based on file type
        try:
            content = await self._extract_text(file_event.file_path)
            result['content'] = content
            result['content_length'] = len(content)
        except Exception as e:
            logger.warning(f"Failed to extract text from {file_event.file_path}: {e}")
            result['extraction_error'] = str(e)

        return result

    async def _extract_text(self, file_path: Path) -> str:
        """Extract text from document.

        Args:
            file_path: Document path

        Returns:
            Extracted text
        """
        # This is a placeholder - actual implementation would use libraries like:
        # - PyPDF2 for PDF files
        # - python-docx for DOCX files
        # - openpyxl for Excel files
        # - etc.

        suffix = file_path.suffix.lower()

        if suffix == '.txt':
            return file_path.read_text(encoding='utf-8')
        elif suffix == '.pdf':
            # Placeholder for PDF text extraction
            return f"[PDF content from {file_path.name}]"
        elif suffix in ['.doc', '.docx']:
            # Placeholder for Word document text extraction
            return f"[Word document content from {file_path.name}]"
        elif suffix in ['.xls', '.xlsx', '.csv']:
            # Placeholder for spreadsheet content
            return f"[Spreadsheet content from {file_path.name}]"
        else:
            return f"[Unsupported document type: {suffix}]"


class ImageProcessor(FileProcessor):
    """Processor for image files."""

    def __init__(self):
        """Initialize image processor."""
        super().__init__("image_processor", SupportedFileTypes.IMAGES)

    async def process(self, file_event: FileEvent) -> Dict[str, Any]:
        """Process image file.

        Args:
            file_event: File event

        Returns:
            Processing result
        """
        result = {
            'processor': self.name,
            'file_path': str(file_event.file_path),
            'category': 'image',
            'size': file_event.file_size,
            'mime_type': file_event.mime_type,
            'processed_at': datetime.now(timezone.utc).isoformat()
        }

        # Extract image metadata
        try:
            metadata = await self._extract_metadata(file_event.file_path)
            result.update(metadata)
        except Exception as e:
            logger.warning(f"Failed to extract metadata from {file_event.file_path}: {e}")
            result['metadata_error'] = str(e)

        return result

    async def _extract_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Extract metadata from image.

        Args:
            file_path: Image path

        Returns:
            Image metadata
        """
        # This is a placeholder - actual implementation would use libraries like:
        # - Pillow (PIL) for basic image info
        # - exifread for EXIF data

        return {
            'width': 1920,  # Placeholder
            'height': 1080,  # Placeholder
            'format': file_path.suffix.upper(),
            'color_mode': 'RGB'  # Placeholder
        }


class FileSystemEventHandler(FileSystemEventHandler):
    """Handler for watchdog file system events."""

    def __init__(self, monitor: 'FileMonitor'):
        """Initialize event handler.

        Args:
            monitor: File monitor instance
        """
        super().__init__()
        self.monitor = monitor
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def on_created(self, event: FileSystemEvent) -> None:
        """Handle file creation.

        Args:
            event: File system event
        """
        if not event.is_directory:
            asyncio.create_task(self._handle_file_event(
                FileEventType.CREATED,
                Path(event.src_path)
            ))

    def on_modified(self, event: FileSystemEvent) -> None:
        """Handle file modification.

        Args:
            event: File system event
        """
        if not event.is_directory:
            asyncio.create_task(self._handle_file_event(
                FileEventType.MODIFIED,
                Path(event.src_path)
            ))

    def on_deleted(self, event: FileSystemEvent) -> None:
        """Handle file deletion.

        Args:
            event: File system event
        """
        if not event.is_directory:
            asyncio.create_task(self._handle_file_event(
                FileEventType.DELETED,
                Path(event.src_path)
            ))

    def on_moved(self, event: FileSystemEvent) -> None:
        """Handle file move.

        Args:
            event: File system event
        """
        if not event.is_directory:
            asyncio.create_task(self._handle_file_event(
                FileEventType.MOVED,
                Path(event.dest_path),
                Path(event.src_path)
            ))

    async def _handle_file_event(
        self,
        event_type: FileEventType,
        file_path: Path,
        source_path: Optional[Path] = None
    ) -> None:
        """Handle file system event.

        Args:
            event_type: Type of event
            file_path: File path
            source_path: Source path for moved events
        """
        try:
            # Create file event
            file_event = await self._create_file_event(event_type, file_path, source_path)

            # Send to monitor for processing
            await self.monitor.handle_file_event(file_event)

        except Exception as e:
            self.logger.error(f"Error handling file event {event_type} for {file_path}: {e}")

    async def _create_file_event(
        self,
        event_type: FileEventType,
        file_path: Path,
        source_path: Optional[Path] = None
    ) -> FileEvent:
        """Create file event object.

        Args:
            event_type: Type of event
            file_path: File path
            source_path: Source path for moved events

        Returns:
            File event object
        """
        file_size = None
        file_hash = None
        mime_type = None

        if event_type != FileEventType.DELETED and file_path.exists():
            file_size = file_path.stat().st_size
            mime_type, _ = mimetypes.guess_type(str(file_path))

            # Calculate hash for small files
            if file_size and file_size < 10 * 1024 * 1024:  # 10MB limit
                file_hash = await self._calculate_file_hash(file_path)

        return FileEvent(
            event_type=event_type,
            file_path=file_path,
            is_directory=file_path.is_dir(),
            timestamp=datetime.now(timezone.utc),
            source_path=source_path,
            file_size=file_size,
            file_hash=file_hash,
            mime_type=mime_type
        )

    async def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of file.

        Args:
            file_path: File path

        Returns:
            File hash
        """
        hash_sha256 = hashlib.sha256()

        def _read_chunks():
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)

        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _read_chunks)

        return hash_sha256.hexdigest()


class FileMonitor:
    """File system monitor for watching directories."""

    def __init__(self):
        """Initialize file monitor."""
        self.config = get_config()
        self.event_bus = get_event_bus()
        self.observers: Dict[Path, Observer] = {}
        self.processors: List[FileProcessor] = []
        self.executor = ThreadPoolExecutor(max_workers=4)
        self._running = False

        # Initialize default processors
        self._initialize_processors()

    def _initialize_processors(self) -> None:
        """Initialize default file processors."""
        self.processors = [
            DocumentProcessor(),
            ImageProcessor(),
        ]

    def add_processor(self, processor: FileProcessor) -> None:
        """Add a file processor.

        Args:
            processor: File processor to add
        """
        self.processors.append(processor)
        logger.info(f"Added file processor: {processor.name}")

    def remove_processor(self, processor_name: str) -> bool:
        """Remove a file processor.

        Args:
            processor_name: Name of processor to remove

        Returns:
            True if removed
        """
        original_length = len(self.processors)
        self.processors = [p for p in self.processors if p.name != processor_name]
        removed = len(self.processors) < original_length

        if removed:
            logger.info(f"Removed file processor: {processor_name}")

        return removed

    async def start_monitoring(self, paths: List[Path]) -> None:
        """Start monitoring directories.

        Args:
            paths: List of paths to monitor
        """
        if self._running:
            logger.warning("File monitor is already running")
            return

        self._running = True

        for path in paths:
            await self._monitor_path(path)

        logger.info(f"Started monitoring {len(paths)} directories")

    async def _monitor_path(self, path: Path) -> None:
        """Start monitoring a single path.

        Args:
            path: Path to monitor
        """
        if not path.exists():
            logger.warning(f"Path does not exist: {path}")
            return

        if path in self.observers:
            logger.warning(f"Already monitoring path: {path}")
            return

        # Create observer
        observer = Observer()
        event_handler = FileSystemEventHandler(self)

        # Schedule monitoring
        observer.schedule(event_handler, str(path), recursive=True)

        # Start observer
        observer.start()
        self.observers[path] = observer

        logger.info(f"Started monitoring path: {path}")

    async def stop_monitoring(self) -> None:
        """Stop all monitoring."""
        if not self._running:
            return

        self._running = False

        # Stop all observers
        for observer in self.observers.values():
            observer.stop()
            observer.join()

        self.observers.clear()

        # Shutdown executor
        self.executor.shutdown(wait=True)

        logger.info("Stopped file monitoring")

    async def handle_file_event(self, file_event: FileEvent) -> None:
        """Handle a file event.

        Args:
            file_event: File event to handle
        """
        try:
            # Check if file type is supported
            if not SupportedFileTypes.is_supported(file_event.file_path):
                logger.debug(f"Skipping unsupported file: {file_event.file_path}")
                return

            # Process file
            result = await self._process_file(file_event)

            # Emit appropriate event
            await self._emit_file_event(file_event, result)

        except Exception as e:
            logger.error(f"Error processing file event {file_event.file_path}: {e}")

    async def _process_file(self, file_event: FileEvent) -> Dict[str, Any]:
        """Process file with appropriate processor.

        Args:
            file_event: File event

        Returns:
            Processing result
        """
        # Find appropriate processor
        processor = None
        for p in self.processors:
            if p.can_process(file_event.file_path):
                processor = p
                break

        if not processor:
            return {
                'error': f'No processor found for {file_event.file_path.suffix}',
                'file_path': str(file_event.file_path)
            }

        # Process file
        return await processor.process(file_event)

    async def _emit_file_event(self, file_event: FileEvent, result: Dict[str, Any]) -> None:
        """ emit appropriate event to event bus.

        Args:
            file_event: File event
            result: Processing result
        """
        if file_event.event_type == FileEventType.CREATED:
            event = FileCreatedEvent(
                file_path=str(file_event.file_path),
                file_size=file_event.file_size or 0,
                mime_type=file_event.mime_type or 'unknown'
            )
        elif file_event.event_type == FileEventType.MODIFIED:
            event = FileModifiedEvent(
                file_path=str(file_event.file_path),
                file_size=file_event.file_size or 0,
                mime_type=file_event.mime_type or 'unknown'
            )
        elif file_event.event_type == FileEventType.DELETED:
            event = FileDeletedEvent(file_path=str(file_event.file_path))
        elif file_event.event_type == FileEventType.MOVED:
            event = FileMovedEvent(
                source_path=str(file_event.source_path),
                destination_path=str(file_event.file_path)
            )
        else:
            return

        # Add processing result to event
        event.metadata.update(result)

        # Emit event
        await self.event_bus.publish(event)

    def get_monitored_paths(self) -> List[Path]:
        """Get list of currently monitored paths.

        Returns:
            List of monitored paths
        """
        return list(self.observers.keys())

    def get_processor_names(self) -> List[str]:
        """Get list of processor names.

        Returns:
            List of processor names
        """
        return [p.name for p in self.processors]

    async def get_statistics(self) -> Dict[str, Any]:
        """Get monitoring statistics.

        Returns:
            Statistics dictionary
        """
        return {
            'running': self._running,
            'monitored_paths': len(self.observers),
            'monitored_locations': [str(p) for p in self.observers.keys()],
            'processors': len(self.processors),
            'processor_names': self.get_processor_names(),
            'supported_extensions': list(SupportedFileTypes.ALL)
        }


# Global file monitor instance
file_monitor = FileMonitor()


def get_file_monitor() -> FileMonitor:
    """Get the global file monitor instance.

    Returns:
        Global file monitor
    """
    return file_monitor