"""
File locking mechanism for distributed Agent-to-Agent architecture.
Implements the "Claim-by-move" rule for Platinum Tier synchronization.
"""

import os
import shutil
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

class FileLocker:
    """Handles file locking using atomic move operations."""
    
    def __init__(self, vault_path: Path, agent_id: str):
        """
        Initialize the file locker.
        
        Args:
            vault_path: Path to the Obsidian vault root
            agent_id: Unique identifier for this agent instance
        """
        self.vault_path = Path(vault_path)
        self.agent_id = agent_id
        
        # Ensure In_Progress folder exists for this agent
        self.in_progress_dir = self.vault_path / "In_Progress" / self.agent_id
        self.in_progress_dir.mkdir(parents=True, exist_ok=True)
        
    def claim_file(self, target_file: Path) -> Optional[Path]:
        """
        Attempt to claim a file by moving it to the agent's In_Progress folder.
        This is an atomic operation on most filesystems.
        
        Args:
            target_file: The path of the file to claim
            
        Returns:
            The new path if claimed successfully, None if already claimed or missing.
        """
        try:
            if not target_file.exists():
                logger.debug(f"File {target_file.name} no longer exists. Likely claimed by another agent.")
                return None
                
            destination_file = self.in_progress_dir / target_file.name
            
            # Atomic rename (move)
            target_file.rename(destination_file)
            logger.info(f"Agent '{self.agent_id}' claimed {target_file.name}")
            return destination_file
            
        except FileNotFoundError:
            # File was moved by another process between exists() check and rename()
            logger.debug(f"Failed to claim {target_file.name}: File moved by another agent.")
            return None
        except Exception as e:
            logger.error(f"Error claiming file {target_file.name}: {e}")
            return None

    def release_to_done(self, claimed_file: Path) -> Optional[Path]:
        """
        Move a completed file from In_Progress to Done.
        
        Args:
            claimed_file: The file currently in In_Progress
            
        Returns:
            The new path in Done
        """
        done_dir = self.vault_path / "Done"
        done_dir.mkdir(parents=True, exist_ok=True)
        return self._move_file(claimed_file, done_dir)
        
    def release_to_folder(self, claimed_file: Path, folder_name: str) -> Optional[Path]:
        """
        Move a file from In_Progress to a specific folder.
        
        Args:
            claimed_file: The file currently in In_Progress
            folder_name: The target folder name relative to vault root
            
        Returns:
            The new path
        """
        target_dir = self.vault_path / folder_name
        target_dir.mkdir(parents=True, exist_ok=True)
        return self._move_file(claimed_file, target_dir)

    def _move_file(self, source: Path, destination_dir: Path) -> Optional[Path]:
        """Helper to move file."""
        try:
            if not source.exists():
                logger.error(f"Missing claimed file: {source}")
                return None
            
            new_path = destination_dir / source.name
            source.rename(new_path)
            logger.info(f"Moved {source.name} to {destination_dir.name}")
            return new_path
        except Exception as e:
            logger.error(f"Failed to move file {source.name}: {e}")
            return None
