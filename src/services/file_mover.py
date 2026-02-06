import shutil
from pathlib import Path
from typing import Optional
import os
from ..exceptions import FileMoveException, FileSystemException
from ..utils.file_utils import ensure_directory_exists


class FileMover:
    """Handles moving files between folders."""

    @staticmethod
    def move_file(source_path: Path, destination_path: Path, create_dest_dirs: bool = True) -> bool:
        """
        Move a file from source to destination.

        Args:
            source_path: Path to the source file
            destination_path: Path to the destination
            create_dest_dirs: Whether to create destination directories if they don't exist

        Returns:
            Boolean indicating success of the operation
        """
        try:
            # Validate source file exists
            if not source_path.exists():
                raise FileMoveException(f"Source file does not exist: {source_path}")

            # Ensure destination directory exists
            if create_dest_dirs:
                ensure_directory_exists(destination_path.parent)

            # Move the file
            shutil.move(str(source_path), str(destination_path))

            return True
        except FileMoveException:
            raise
        except Exception as e:
            raise FileMoveException(f"Error moving file from {source_path} to {destination_path}: {str(e)}")

    @staticmethod
    def copy_file(source_path: Path, destination_path: Path, create_dest_dirs: bool = True) -> bool:
        """
        Copy a file from source to destination.

        Args:
            source_path: Path to the source file
            destination_path: Path to the destination
            create_dest_dirs: Whether to create destination directories if they don't exist

        Returns:
            Boolean indicating success of the operation
        """
        try:
            # Validate source file exists
            if not source_path.exists():
                raise FileMoveException(f"Source file does not exist: {source_path}")

            # Ensure destination directory exists
            if create_dest_dirs:
                ensure_directory_exists(destination_path.parent)

            # Copy the file
            shutil.copy2(str(source_path), str(destination_path))

            return True
        except Exception as e:
            raise FileMoveException(f"Error copying file from {source_path} to {destination_path}: {str(e)}")

    @staticmethod
    def ensure_directory_structure(directories: list) -> dict:
        """
        Ensure that a list of directories exist, creating them if necessary.

        Args:
            directories: List of directory paths to ensure

        Returns:
            Dictionary mapping directory paths to success status
        """
        results = {}
        for directory in directories:
            try:
                path = Path(directory)
                path.mkdir(parents=True, exist_ok=True)
                results[str(path)] = True
            except Exception as e:
                print(f"Error creating directory {directory}: {str(e)}")
                results[str(directory)] = False

        return results

    @staticmethod
    def delete_file(file_path: Path) -> bool:
        """
        Delete a file (without permanently deleting as per requirements).

        Args:
            file_path: Path to the file to delete

        Returns:
            Boolean indicating success of the operation
        """
        try:
            if file_path.exists():
                # Following the requirement not to permanently delete files
                # We'll move the file to a trash-like directory instead
                trash_dir = file_path.parent / ".trash"
                trash_dir.mkdir(exist_ok=True)

                # Create unique filename in trash
                dest_path = trash_dir / f"{file_path.name}.deleted"
                counter = 1
                while dest_path.exists():
                    name_parts = file_path.stem, file_path.suffix
                    dest_path = trash_dir / f"{name_parts[0]}_{counter}{name_parts[1]}.deleted"
                    counter += 1

                shutil.move(str(file_path), str(dest_path))
                return True
            else:
                raise FileSystemException(f"File does not exist: {file_path}")
        except Exception as e:
            raise FileSystemException(f"Error deleting file {file_path}: {str(e)}")

    @staticmethod
    def is_safe_path(path: Path, base_path: Path) -> bool:
        """
        Check if a path is safe (not attempting to access outside base path).

        Args:
            path: Path to check
            base_path: Base path to restrict to

        Returns:
            Boolean indicating if path is safe
        """
        try:
            # Resolve both paths to absolute form
            abs_path = path.resolve()
            abs_base_path = base_path.resolve()

            # Check if the path is within the base path
            abs_path.relative_to(abs_base_path)
            return True
        except ValueError:
            # Path is outside base path
            return False