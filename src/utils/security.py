import logging
from datetime import datetime
from pathlib import Path
from typing import Optional
import hashlib
import secrets
from ..config.logging_config import get_logger


logger = get_logger(__name__)


class SecurityLogger:
    """Handles security logging for file processing events."""

    def __init__(self, log_file_path: str = "./security.log"):
        """
        Initialize security logger.

        Args:
            log_file_path: Path to the security log file
        """
        self.log_file_path = Path(log_file_path)
        # Ensure parent directory exists
        self.log_file_path.parent.mkdir(parents=True, exist_ok=True)

    def log_file_access(self, file_path: str, user: str, action: str, result: str = "SUCCESS") -> bool:
        """
        Log file access event for security monitoring.

        Args:
            file_path: Path to the file accessed
            user: User who accessed the file (could be system user or agent ID)
            action: Action performed (READ, WRITE, MOVE, DELETE, etc.)
            result: Result of the action (SUCCESS, FAILURE, DENIED)

        Returns:
            Boolean indicating success of the logging operation
        """
        try:
            timestamp = datetime.now().isoformat()
            log_entry = f"[SECURITY] {timestamp} | USER:{user} | ACTION:{action} | RESULT:{result} | FILE:{file_path}\n"

            with open(self.log_file_path, 'a', encoding='utf-8') as f:
                f.write(log_entry)

            # Also log to standard application logger
            logger.info(f"Security event: {action} on {file_path} by {user}, result={result}")

            return True
        except Exception as e:
            logger.error(f"Failed to log security event: {str(e)}")
            return False

    def log_file_processing(self, file_path: str, processor: str, action: str = "PROCESS") -> bool:
        """
        Log file processing event.

        Args:
            file_path: Path to the file being processed
            processor: Name of the processor (e.g., Claude Code, internal processor)
            action: Specific action being taken

        Returns:
            Boolean indicating success of the logging operation
        """
        try:
            timestamp = datetime.now().isoformat()
            log_entry = f"[PROCESSING] {timestamp} | PROCESSOR:{processor} | ACTION:{action} | FILE:{file_path}\n"

            with open(self.log_file_path, 'a', encoding='utf-8') as f:
                f.write(log_entry)

            # Also log to standard application logger
            logger.info(f"Processing event: {action} on {file_path} by {processor}")

            return True
        except Exception as e:
            logger.error(f"Failed to log processing event: {str(e)}")
            return False

    def log_encryption_event(self, file_path: str, algorithm: str, key_strength: int, action: str = "ENCRYPT") -> bool:
        """
        Log encryption-related events.

        Args:
            file_path: Path to the encrypted file
            algorithm: Encryption algorithm used
            key_strength: Key strength in bits
            action: Encryption or decryption action

        Returns:
            Boolean indicating success of the logging operation
        """
        try:
            timestamp = datetime.now().isoformat()
            log_entry = f"[ENCRYPTION] {timestamp} | ALGORITHM:{algorithm} | KEY_STRENGTH:{key_strength} | ACTION:{action} | FILE:{file_path}\n"

            with open(self.log_file_path, 'a', encoding='utf-8') as f:
                f.write(log_entry)

            # Also log to standard application logger
            logger.info(f"Encryption event: {action} on {file_path} using {algorithm}-{key_strength}")

            return True
        except Exception as e:
            logger.error(f"Failed to log encryption event: {str(e)}")
            return False

    def calculate_file_checksum(self, file_path: str) -> Optional[str]:
        """
        Calculate SHA-256 checksum of a file for integrity verification.

        Args:
            file_path: Path to the file to calculate checksum for

        Returns:
            SHA-256 checksum as hex string, or None if calculation fails
        """
        try:
            sha256_hash = hashlib.sha256()
            with open(file_path, "rb") as f:
                # Read file in chunks to handle large files efficiently
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except Exception as e:
            logger.error(f"Failed to calculate checksum for {file_path}: {str(e)}")
            return None

    def log_integrity_check(self, file_path: str, expected_checksum: str, actual_checksum: str) -> bool:
        """
        Log file integrity check result.

        Args:
            file_path: Path to the file checked
            expected_checksum: Expected checksum value
            actual_checksum: Actual checksum calculated

        Returns:
            Boolean indicating success of the logging operation
        """
        try:
            timestamp = datetime.now().isoformat()
            status = "PASS" if expected_checksum == actual_checksum else "FAIL"
            log_entry = f"[INTEGRITY] {timestamp} | STATUS:{status} | EXPECTED:{expected_checksum[:16]}... | ACTUAL:{actual_checksum[:16]}... | FILE:{file_path}\n"

            with open(self.log_file_path, 'a', encoding='utf-8') as f:
                f.write(log_entry)

            # Also log to standard application logger
            logger.info(f"Integrity check: {status} for {file_path}")

            return True
        except Exception as e:
            logger.error(f"Failed to log integrity check: {str(e)}")
            return False


# Global security logger instance
security_logger = SecurityLogger()