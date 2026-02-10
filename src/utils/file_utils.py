import os
import mimetypes
from pathlib import Path
from typing import Tuple, Optional
import hashlib
import uuid
from datetime import datetime

def validate_file_size(file_path: Path, max_size: int) -> Tuple[bool, str]:
    """
    Validate file size against maximum allowed size.

    Args:
        file_path: Path to the file to validate
        max_size: Maximum allowed file size in bytes

    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        size = file_path.stat().st_size
        if size > max_size:
            return False, f"File size {size} bytes exceeds maximum {max_size} bytes ({max_size/1024/1024:.1f} MB)"
        return True, ""
    except FileNotFoundError:
        return False, f"File not found: {file_path}"
    except OSError as e:
        return False, f"Error accessing file {file_path}: {str(e)}"


def get_file_type(file_path: Path) -> str:
    """
    Determine file type based on extension and MIME type.

    Args:
        file_path: Path to the file

    Returns:
        String representing the file type
    """
    extension = file_path.suffix.lower()

    # Supported document types
    doc_types = {'.pdf': 'PDF', '.docx': 'DOCX', '.txt': 'TXT',
                 '.xlsx': 'XLSX', '.pptx': 'PPTX'}

    # Supported image types
    img_types = {'.jpg': 'JPG', '.jpeg': 'JPEG', '.png': 'PNG', '.gif': 'GIF'}

    if extension in doc_types:
        return doc_types[extension]
    elif extension in img_types:
        return img_types[extension]
    else:
        # Try to determine from MIME type
        mime_type, _ = mimetypes.guess_type(str(file_path))
        if mime_type:
            if mime_type.startswith('image/'):
                return 'IMAGE'
            elif mime_type.startswith('text/'):
                return 'TEXT'
            elif 'pdf' in mime_type:
                return 'PDF'

        return 'UNKNOWN'


def is_supported_file_type(file_path: Path) -> bool:
    """
    Check if the file type is supported by the agent.

    Args:
        file_path: Path to the file

    Returns:
        Boolean indicating if file type is supported
    """
    extension = file_path.suffix.lower()
    supported_extensions = {
        '.pdf', '.docx', '.txt', '.xlsx', '.pptx',
        '.jpg', '.jpeg', '.png', '.gif'
    }
    return extension in supported_extensions


def calculate_file_hash(file_path: Path) -> str:
    """
    Calculate MD5 hash of a file for integrity checking.

    Args:
        file_path: Path to the file

    Returns:
        Hex string of the file's MD5 hash
    """
    hash_md5 = hashlib.md5()
    try:
        with open(file_path, "rb") as f:
            # Read file in chunks to handle large files efficiently
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception as e:
        raise IOError(f"Could not calculate hash for {file_path}: {str(e)}")


def ensure_directory_exists(directory: Path) -> bool:
    """
    Ensure that a directory exists, creating it if necessary.

    Args:
        directory: Path to the directory

    Returns:
        Boolean indicating if directory exists/is created
    """
    try:
        Path(directory).mkdir(parents=True, exist_ok=True)
        return True
    except Exception as e:
        print(f"Error creating directory {directory}: {str(e)}")
        return False


def generate_unique_filename(base_name: str, directory: Path, extension: str) -> Path:
    """
    Generate a unique filename by appending a counter if file exists.

    Args:
        base_name: Base name for the file
        directory: Directory where file will be created
        extension: File extension including the dot (e.g., ".txt")

    Returns:
        Path object with a unique filename
    """
    counter = 1
    file_path = directory / f"{base_name}{extension}"

    while file_path.exists():
        file_path = directory / f"{base_name}_{counter}{extension}"
        counter += 1

    return file_path


def get_file_creation_time(file_path: Path) -> datetime:
    """
    Get the creation time of a file.

    Args:
        file_path: Path to the file

    Returns:
        datetime object representing the file creation time
    """
    stat = file_path.stat()
    # On Windows, st_ctime is creation time; on Unix, it's the last metadata change
    timestamp = stat.st_ctime
    return datetime.fromtimestamp(timestamp)


def read_file_head(file_path: Path, lines: int = 10) -> str:
    """Return the first *lines* lines of a file as a single string.

    Parameters
    ----------
    file_path: Path
        Path to the file.
    lines: int, optional
        Number of lines to return (default 10).
    """
    from itertools import islice
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return "".join(islice(f, lines))
    except Exception as e:
        raise IOError(f"Could not read file head from {file_path}: {e}")


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename by removing or replacing invalid characters.

    Args:
        filename: Original filename

    Returns:
        Sanitized filename
    """
    # Replace invalid characters for most filesystems
    invalid_chars = '<>:"/\\|?*'
    sanitized = filename

    for char in invalid_chars:
        sanitized = sanitized.replace(char, '_')

    # Limit length to prevent issues
    if len(sanitized) > 255:
        name, ext = os.path.splitext(sanitized)
        sanitized = name[:250] + ext

    return sanitized