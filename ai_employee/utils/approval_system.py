"""
File-based approval system for AI Employee system.

Manages human-in-the-loop approval workflows using file-based
communication with Obsidian vault integration.
"""

import asyncio
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
import json
import uuid
import shutil

from ..core.event_bus import get_event_bus, Event
from ..core.config import get_config
from ..utils.logging_config import business_logger

logger = logging.getLogger(__name__)


class ApprovalStatus(Enum):
    """Approval status values."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


@dataclass
class ApprovalRequest:
    """Approval request data."""
    request_id: str
    item_type: str
    item_id: str
    amount: Optional[float] = None
    reason: str = ""
    requested_by: str = "AI Employee"
    requested_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    status: ApprovalStatus = ApprovalStatus.PENDING
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    notes: Optional[str] = None

    def is_expired(self) -> bool:
        """Check if approval request has expired.

        Returns:
            True if expired
        """
        if not self.expires_at:
            return False
        return datetime.now(timezone.utc) > self.expires_at

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary.

        Returns:
            Dictionary representation
        """
        return {
            'request_id': self.request_id,
            'item_type': self.item_type,
            'item_id': self.item_id,
            'amount': self.amount,
            'reason': self.reason,
            'requested_by': self.requested_by,
            'requested_at': self.requested_at.isoformat(),
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'metadata': self.metadata,
            'status': self.status.value,
            'approved_by': self.approved_by,
            'approved_at': self.approved_at.isoformat() if self.approved_at else None,
            'notes': self.notes
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ApprovalRequest':
        """Create from dictionary.

        Args:
            data: Dictionary data

        Returns:
            Approval request
        """
        # Convert datetime strings
        if 'requested_at' in data and data['requested_at']:
            data['requested_at'] = datetime.fromisoformat(data['requested_at'])
        if 'expires_at' in data and data['expires_at']:
            data['expires_at'] = datetime.fromisoformat(data['expires_at'])
        if 'approved_at' in data and data['approved_at']:
            data['approved_at'] = datetime.fromisoformat(data['approved_at'])

        # Convert status enum
        if 'status' in data and isinstance(data['status'], str):
            data['status'] = ApprovalStatus(data['status'])

        return cls(**data)


@dataclass
class ApprovalRequiredEvent(Event):
    """Event fired when approval is required."""
    request_id: str = field(default_factory=str)
    item_type: str = field(default_factory=str)
    item_id: str = field(default_factory=str)
    amount: Optional[float] = None
    reason: str = ""
    expires_at: Optional[datetime] = None


@dataclass
class ApprovalDecisionEvent(Event):
    """Event fired when approval decision is made."""
    request_id: str = field(default_factory=str)
    item_type: str = field(default_factory=str)
    item_id: str = field(default_factory=str)
    approved: bool = False
    approved_by: str = ""
    notes: Optional[str] = None


class ApprovalSystem:
    """File-based approval system."""

    def __init__(self):
        """Initialize approval system."""
        self.config = get_config()
        self.event_bus = get_event_bus()
        self.requests: Dict[str, ApprovalRequest] = {}
        self._lock = asyncio.Lock()

        # Path configuration
        self.pending_path = self.config.paths.pending_approval_path
        self.approved_path = self.config.paths.approved_path
        self.rejected_path = self.config.paths.rejected_path
        self.done_path = self.config.paths.done_path

        # Ensure directories exist
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """Ensure approval directories exist."""
        for path in [self.pending_path, self.approved_path, self.rejected_path, self.done_path]:
            path.mkdir(parents=True, exist_ok=True)

    async def create_approval_request(
        self,
        item_type: str,
        item_id: str,
        amount: Optional[float] = None,
        reason: str = "",
        metadata: Optional[Dict[str, Any]] = None,
        expires_in_hours: Optional[int] = None
    ) -> str:
        """Create an approval request.

        Args:
            item_type: Type of item requiring approval
            item_id: ID of the item
            amount: Amount (if applicable)
            reason: Reason for approval
            metadata: Additional metadata
            expires_in_hours: Hours until expiration (default from config)

        Returns:
            Approval request ID
        """
        async with self._lock:
            # Generate request ID
            request_id = str(uuid.uuid4())

            # Set expiration
            if expires_in_hours is None:
                expires_in_hours = self.config.approval_timeout_hours

            expires_at = None
            if expires_in_hours > 0:
                expires_at = datetime.now(timezone.utc) + timedelta(hours=expires_in_hours)

            # Create request
            request = ApprovalRequest(
                request_id=request_id,
                item_type=item_type,
                item_id=item_id,
                amount=amount,
                reason=reason,
                metadata=metadata or {},
                expires_at=expires_at
            )

            # Store request
            self.requests[request_id] = request

            # Create approval file
            await self._create_approval_file(request)

            # Log business event
            business_logger.log_approval_requested(item_type, item_id, amount)

            # Emit event
            await self.event_bus.publish(ApprovalRequiredEvent(
                request_id=request_id,
                item_type=item_type,
                item_id=item_id,
                amount=amount,
                reason=reason,
                expires_at=expires_at
            ))

            logger.info(f"Created approval request {request_id} for {item_type} {item_id}")
            return request_id

    async def _create_approval_file(self, request: ApprovalRequest) -> None:
        """Create approval file in pending directory.

        Args:
            request: Approval request
        """
        filename = f"{request.item_type}_{request.item_id}_{request.request_id[:8]}.md"
        file_path = self.pending_path / filename

        # Generate file content
        content = self._generate_approval_content(request)

        # Write file
        file_path.write_text(content, encoding='utf-8')

        logger.debug(f"Created approval file: {file_path}")

    def _generate_approval_content(self, request: ApprovalRequest) -> str:
        """Generate approval file content.

        Args:
            request: Approval request

        Returns:
            File content
        """
        content = f"# Approval Request: {request.item_type.title()}\n\n"
        content += f"**Request ID**: {request.request_id}\n"
        content += f"**Item Type**: {request.item_type}\n"
        content += f"**Item ID**: {request.item_id}\n"

        if request.amount:
            content += f"**Amount**: ${request.amount:,.2f}\n"

        content += f"**Requested By**: {request.requested_by}\n"
        content += f"**Requested At**: {request.requested_at.strftime('%Y-%m-%d %H:%M:%S')}\n"

        if request.expires_at:
            content += f"**Expires At**: {request.expires_at.strftime('%Y-%m-%d %H:%M:%S')}\n"

        content += f"\n## Reason\n\n{request.reason}\n"

        if request.metadata:
            content += f"\n## Additional Information\n\n"
            for key, value in request.metadata.items():
                content += f"- **{key.replace('_', ' ').title()}**: {value}\n"

        content += f"\n## Action Required\n\n"
        content += "Please review this request and move this file to the appropriate directory:\n\n"
        content += f"- Move to `{self.approved_path.name}/` to **APPROVE** this request\n"
        content += f"- Move to `{self.rejected_path.name}/` to **REJECT** this request\n\n"

        content += "---\n"
        content += f"*Generated by AI Employee at {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}*\n"

        return content

    async def check_approval_status(self, request_id: str) -> Optional[ApprovalRequest]:
        """Check approval status by monitoring file locations.

        Args:
            request_id: Approval request ID

        Returns:
            Updated approval request or None if not found
        """
        async with self._lock:
            request = self.requests.get(request_id)
            if not request:
                return None

            # Check if request has expired
            if request.is_expired() and request.status == ApprovalStatus.PENDING:
                request.status = ApprovalStatus.EXPIRED
                await self._move_to_done(request, "Expired")
                return request

            # Check file locations to determine status
            await self._update_status_from_file_location(request)

            return request

    async def _update_status_from_file_location(self, request: ApprovalRequest) -> None:
        """Update request status based on file location.

        Args:
            request: Approval request
        """
        # Find the approval file
        approval_file = await self._find_approval_file(request)

        if not approval_file:
            logger.warning(f"Approval file not found for request {request.request_id}")
            return

        # Check current location
        if approval_file.parent == self.approved_path:
            if request.status != ApprovalStatus.APPROVED:
                await self._handle_approval(request, approval_file)
        elif approval_file.parent == self.rejected_path:
            if request.status != ApprovalStatus.REJECTED:
                await self._handle_rejection(request, approval_file)

    async def _find_approval_file(self, request: ApprovalRequest) -> Optional[Path]:
        """Find approval file for request.

        Args:
            request: Approval request

        Returns:
            File path or None if not found
        """
        # Search in all possible directories
        search_paths = [self.pending_path, self.approved_path, self.rejected_path, self.done_path]

        for search_path in search_paths:
            pattern = f"{request.item_type}_{request.item_id}_{request.request_id[:8]}*.md"
            files = list(search_path.glob(pattern))

            if files:
                return files[0]  # Return first match

        return None

    async def _handle_approval(self, request: ApprovalRequest, file_path: Path) -> None:
        """Handle approval.

        Args:
            request: Approval request
            file_path: Approval file path
        """
        # Update request
        request.status = ApprovalStatus.APPROVED
        request.approved_at = datetime.now(timezone.utc)
        request.approved_by = "Human Reviewer"  # Could be extracted from file content

        # Extract notes from file if available
        try:
            content = file_path.read_text(encoding='utf-8')
            request.notes = self._extract_approval_notes(content)
        except Exception as e:
            logger.warning(f"Failed to read approval notes from {file_path}: {e}")

        # Move to done directory
        await self._move_to_done(request, "Approved")

        # Log business event
        business_logger.log_approval_decision(
            request.item_type, request.item_id, True, request.approved_by
        )

        # Emit event
        await self.event_bus.publish(ApprovalDecisionEvent(
            request_id=request.request_id,
            item_type=request.item_type,
            item_id=request.item_id,
            approved=True,
            approved_by=request.approved_by,
            notes=request.notes
        ))

        logger.info(f"Request {request.request_id} approved by {request.approved_by}")

    async def _handle_rejection(self, request: ApprovalRequest, file_path: Path) -> None:
        """Handle rejection.

        Args:
            request: Approval request
            file_path: Approval file path
        """
        # Update request
        request.status = ApprovalStatus.REJECTED
        request.approved_at = datetime.now(timezone.utc)
        request.approved_by = "Human Reviewer"

        # Extract notes from file if available
        try:
            content = file_path.read_text(encoding='utf-8')
            request.notes = self._extract_approval_notes(content)
        except Exception as e:
            logger.warning(f"Failed to read rejection notes from {file_path}: {e}")

        # Move to done directory
        await self._move_to_done(request, "Rejected")

        # Log business event
        business_logger.log_approval_decision(
            request.item_type, request.item_id, False, request.approved_by
        )

        # Emit event
        await self.event_bus.publish(ApprovalDecisionEvent(
            request_id=request.request_id,
            item_type=request.item_type,
            item_id=request.item_id,
            approved=False,
            approved_by=request.approved_by,
            notes=request.notes
        ))

        logger.info(f"Request {request.request_id} rejected by {request.approved_by}")

    def _extract_approval_notes(self, content: str) -> Optional[str]:
        """Extract approval notes from file content.

        Args:
            content: File content

        Returns:
            Approval notes or None
        """
        # Look for notes section
        lines = content.split('\n')
        notes_section = False
        notes = []

        for line in lines:
            line = line.strip()
            if line.startswith('## Notes'):
                notes_section = True
                continue
            elif line.startswith('##') and notes_section:
                break
            elif notes_section and line:
                notes.append(line)

        return '\n'.join(notes) if notes else None

    async def _move_to_done(self, request: ApprovalRequest, action: str) -> None:
        """Move approval file to done directory.

        Args:
            request: Approval request
            action: Action taken (Approved/Rejected/Expired)
        """
        approval_file = await self._find_approval_file(request)
        if not approval_file:
            return

        # Create new filename with status
        new_filename = f"{request.item_type}_{request.item_id}_{action.lower()}_{request.request_id[:8]}.md"
        new_path = self.done_path / new_filename

        # Move file
        try:
            shutil.move(str(approval_file), str(new_path))
            logger.debug(f"Moved approval file to {new_path}")
        except Exception as e:
            logger.error(f"Failed to move approval file: {e}")

    async def cancel_request(self, request_id: str, reason: str = "") -> bool:
        """Cancel an approval request.

        Args:
            request_id: Request ID
            reason: Cancellation reason

        Returns:
            True if cancelled
        """
        async with self._lock:
            request = self.requests.get(request_id)
            if not request:
                return False

            if request.status != ApprovalStatus.PENDING:
                logger.warning(f"Cannot cancel request {request_id} in status {request.status}")
                return False

            # Update request
            request.status = ApprovalStatus.CANCELLED
            request.notes = reason

            # Move to done
            await self._move_to_done(request, "Cancelled")

            logger.info(f"Cancelled approval request {request_id}: {reason}")
            return True

    async def get_pending_requests(self) -> List[ApprovalRequest]:
        """Get all pending approval requests.

        Returns:
            List of pending requests
        """
        async with self._lock:
            return [r for r in self.requests.values() if r.status == ApprovalStatus.PENDING]

    async def get_request_history(
        self,
        item_type: Optional[str] = None,
        limit: int = 50
    ) -> List[ApprovalRequest]:
        """Get approval request history.

        Args:
            item_type: Filter by item type (optional)
            limit: Maximum number of results

        Returns:
            List of approval requests
        """
        async with self._lock:
            requests = list(self.requests.values())

            # Filter by item type
            if item_type:
                requests = [r for r in requests if r.item_type == item_type]

            # Sort by requested_at descending
            requests.sort(key=lambda r: r.requested_at, reverse=True)

            return requests[:limit]

    async def cleanup_expired_requests(self) -> int:
        """Clean up expired approval requests.

        Returns:
            Number of requests cleaned up
        """
        async with self._lock:
            expired_requests = [
                r for r in self.requests.values()
                if r.status == ApprovalStatus.PENDING and r.is_expired()
            ]

            for request in expired_requests:
                request.status = ApprovalStatus.EXPIRED
                await self._move_to_done(request, "Expired")

            logger.info(f"Cleaned up {len(expired_requests)} expired approval requests")
            return len(expired_requests)

    async def get_statistics(self) -> Dict[str, Any]:
        """Get approval system statistics.

        Returns:
            Statistics dictionary
        """
        async with self._lock:
            total = len(self.requests)
            pending = sum(1 for r in self.requests.values() if r.status == ApprovalStatus.PENDING)
            approved = sum(1 for r in self.requests.values() if r.status == ApprovalStatus.APPROVED)
            rejected = sum(1 for r in self.requests.values() if r.status == ApprovalStatus.REJECTED)
            expired = sum(1 for r in self.requests.values() if r.status == ApprovalStatus.EXPIRED)
            cancelled = sum(1 for r in self.requests.values() if r.status == ApprovalStatus.CANCELLED)

            return {
                'total_requests': total,
                'pending': pending,
                'approved': approved,
                'rejected': rejected,
                'expired': expired,
                'cancelled': cancelled,
                'approval_rate': (approved / total * 100) if total > 0 else 0,
                'pending_amount': sum(
                    r.amount or 0 for r in self.requests.values()
                    if r.status == ApprovalStatus.PENDING and r.amount
                )
            }


# Global approval system instance
approval_system = ApprovalSystem()


def get_approval_system() -> ApprovalSystem:
    """Get the global approval system instance.

    Returns:
        Global approval system
    """
    return approval_system


# Convenience functions
async def create_approval_request(
    item_type: str,
    item_id: str,
    amount: Optional[float] = None,
    reason: str = "",
    metadata: Optional[Dict[str, Any]] = None
) -> str:
    """Create an approval request.

    Args:
        item_type: Type of item requiring approval
        item_id: ID of the item
        amount: Amount (if applicable)
        reason: Reason for approval
        metadata: Additional metadata

    Returns:
        Approval request ID
    """
    return await approval_system.create_approval_request(
        item_type, item_id, amount, reason, metadata
    )


async def check_approval_status(request_id: str) -> Optional[ApprovalRequest]:
    """Check approval status.

    Args:
        request_id: Approval request ID

    Returns:
        Approval request or None if not found
    """
    return await approval_system.check_approval_status(request_id)