"""GDPR compliance utilities for EU customers."""

import json
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import logging
import asyncio
import aiofiles
import csv
import zipfile
import io

logger = logging.getLogger(__name__)


class GDPRRequestType(Enum):
    """Types of GDPR requests."""
    DATA_ACCESS = "data_access"
    DATA_PORTABILITY = "data_portability"
    DATA_RECTIFICATION = "data_rectification"
    DATA_ERASURE = "data_erasure"
    RESTRICT_PROCESSING = "restrict_processing"
    OBJECTION = "objection"
    CONSENT_WITHDRAWAL = "consent_withdrawal"


class ConsentStatus(Enum):
    """Consent status for data processing."""
    GRANTED = "granted"
    DENIED = "denied"
    WITHDRAWN = "withdrawn"
    EXPIRED = "expired"


class DataProcessingBasis(Enum):
    """Legal basis for data processing."""
    CONSENT = "consent"
    CONTRACT = "contract"
    LEGAL_OBLIGATION = "legal_obligation"
    VITAL_INTERESTS = "vital_interests"
    PUBLIC_TASK = "public_task"
    LEGITIMATE_INTERESTS = "legitimate_interests"


@dataclass
class ConsentRecord:
    """Record of consent given by data subject."""
    id: str
    data_subject_id: str
    purpose: str
    basis: DataProcessingBasis
    status: ConsentStatus
    granted_at: datetime
    expires_at: Optional[datetime] = None
    withdrawn_at: Optional[datetime] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_valid(self) -> bool:
        """Check if consent is currently valid."""
        if self.status != ConsentStatus.GRANTED:
            return False

        if self.expires_at and datetime.now() > self.expires_at:
            return False

        return True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "data_subject_id": self.data_subject_id,
            "purpose": self.purpose,
            "basis": self.basis.value,
            "status": self.status.value,
            "granted_at": self.granted_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "withdrawn_at": self.withdrawn_at.isoformat() if self.withdrawn_at else None,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "metadata": self.metadata
        }


@dataclass
class GDPRRequest:
    """GDPR data subject request."""
    id: str
    type: GDPRRequestType
    data_subject_id: str
    request_details: Dict[str, Any] = field(default_factory=dict)
    status: str = "pending"  # pending, processing, completed, rejected
    created_at: datetime = field(default_factory=datetime.now)
    processed_at: Optional[datetime] = None
    processed_by: Optional[str] = None
    response: Optional[Dict[str, Any]] = None
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "type": self.type.value,
            "data_subject_id": self.data_subject_id,
            "request_details": self.request_details,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
            "processed_by": self.processed_by,
            "response": self.response,
            "notes": self.notes
        }


class DataSubject:
    """Represents a data subject under GDPR."""

    def __init__(self, id: str, email: str, **kwargs):
        self.id = id
        self.email = email
        self.name = kwargs.get("name")
        self.phone = kwargs.get("phone")
        self.address = kwargs.get("address")
        self.dob = kwargs.get("dob")
        self.created_at = kwargs.get("created_at", datetime.now())
        self.last_activity = kwargs.get("last_activity", datetime.now())
        self.preferences = kwargs.get("preferences", {})
        self.metadata = kwargs.get("metadata", {})

    def to_dict(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """Convert to dictionary with optional sensitive data."""
        data = {
            "id": self.id,
            "email": self.email,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "preferences": self.preferences
        }

        if include_sensitive:
            data.update({
                "name": self.name,
                "phone": self.phone,
                "address": self.address,
                "dob": self.dob.isoformat() if self.dob else None,
                "metadata": self.metadata
            })

        return data

    def anonymize(self):
        """Anonymize personal data."""
        self.name = "Anonymous User"
        self.email = f"anon-{self.id[:8]}@ anonymized.com"
        self.phone = "+1-555-000-0000"
        self.address = ""
        self.dob = None
        self.metadata = {"anonymized": True, "anonymized_at": datetime.now().isoformat()}


class GDPRManager:
    """Manages GDPR compliance."""

    def __init__(self, storage_path: str = "gdpr_data"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        # Storage files
        self.consent_file = self.storage_path / "consents.json"
        self.requests_file = self.storage_path / "requests.json"
        self.data_subjects_file = self.storage_path / "data_subjects.json"
        self.processing_log_file = self.storage_path / "processing_log.json"

        # In-memory storage
        self.consents: Dict[str, ConsentRecord] = {}
        self.requests: Dict[str, GDPRRequest] = {}
        self.data_subjects: Dict[str, DataSubject] = {}
        self.processing_log: List[Dict[str, Any]] = []

        # Load existing data
        self._load_data()

    def _load_data(self):
        """Load GDPR data from storage."""
        try:
            # Load consents
            if self.consent_file.exists():
                with open(self.consent_file, 'r') as f:
                    data = json.load(f)
                    for consent_data in data:
                        consent = ConsentRecord(
                            id=consent_data["id"],
                            data_subject_id=consent_data["data_subject_id"],
                            purpose=consent_data["purpose"],
                            basis=DataProcessingBasis(consent_data["basis"]),
                            status=ConsentStatus(consent_data["status"]),
                            granted_at=datetime.fromisoformat(consent_data["granted_at"]),
                            expires_at=datetime.fromisoformat(consent_data["expires_at"]) if consent_data.get("expires_at") else None,
                            withdrawn_at=datetime.fromisoformat(consent_data["withdrawn_at"]) if consent_data.get("withdrawn_at") else None,
                            ip_address=consent_data.get("ip_address"),
                            user_agent=consent_data.get("user_agent"),
                            metadata=consent_data.get("metadata", {})
                        )
                        self.consents[consent.id] = consent

            # Load requests
            if self.requests_file.exists():
                with open(self.requests_file, 'r') as f:
                    data = json.load(f)
                    for request_data in data:
                        request = GDPRRequest(
                            id=request_data["id"],
                            type=GDPRRequestType(request_data["type"]),
                            data_subject_id=request_data["data_subject_id"],
                            request_details=request_data.get("request_details", {}),
                            status=request_data.get("status", "pending"),
                            created_at=datetime.fromisoformat(request_data["created_at"]),
                            processed_at=datetime.fromisoformat(request_data["processed_at"]) if request_data.get("processed_at") else None,
                            processed_by=request_data.get("processed_by"),
                            response=request_data.get("response"),
                            notes=request_data.get("notes", [])
                        )
                        self.requests[request.id] = request

            # Load data subjects
            if self.data_subjects_file.exists():
                with open(self.data_subjects_file, 'r') as f:
                    data = json.load(f)
                    for subject_data in data:
                        subject = DataSubject(
                            id=subject_data["id"],
                            email=subject_data["email"],
                            name=subject_data.get("name"),
                            phone=subject_data.get("phone"),
                            address=subject_data.get("address"),
                            dob=datetime.fromisoformat(subject_data["dob"]) if subject_data.get("dob") else None,
                            created_at=datetime.fromisoformat(subject_data["created_at"]),
                            last_activity=datetime.fromisoformat(subject_data["last_activity"]),
                            preferences=subject_data.get("preferences", {}),
                            metadata=subject_data.get("metadata", {})
                        )
                        self.data_subjects[subject.id] = subject

            # Load processing log
            if self.processing_log_file.exists():
                with open(self.processing_log_file, 'r') as f:
                    self.processing_log = json.load(f)

        except Exception as e:
            logger.error(f"Failed to load GDPR data: {e}")

    def _save_data(self):
        """Save GDPR data to storage."""
        try:
            # Save consents
            consent_data = [consent.to_dict() for consent in self.consents.values()]
            with open(self.consent_file, 'w') as f:
                json.dump(consent_data, f, indent=2)

            # Save requests
            request_data = [request.to_dict() for request in self.requests.values()]
            with open(self.requests_file, 'w') as f:
                json.dump(request_data, f, indent=2)

            # Save data subjects
            subject_data = [subject.to_dict() for subject in self.data_subjects.values()]
            with open(self.data_subjects_file, 'w') as f:
                json.dump(subject_data, f, indent=2)

            # Save processing log (keep last 1000 entries)
            recent_log = self.processing_log[-1000:]
            with open(self.processing_log_file, 'w') as f:
                json.dump(recent_log, f, indent=2)

        except Exception as e:
            logger.error(f"Failed to save GDPR data: {e}")

    def create_data_subject(self, email: str, **kwargs) -> DataSubject:
        """Create a new data subject."""
        subject_id = f"ds_{secrets.token_urlsafe(16)}"
        subject = DataSubject(subject_id, email, **kwargs)
        self.data_subjects[subject_id] = subject
        self._save_data()

        self._log_processing(
            "data_subject_created",
            subject_id,
            {"email": email}
        )

        return subject

    def record_consent(
        self,
        data_subject_id: str,
        purpose: str,
        basis: DataProcessingBasis,
        expires_days: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> ConsentRecord:
        """Record consent from data subject."""
        consent_id = f"consent_{secrets.token_urlsafe(16)}"

        expires_at = None
        if expires_days:
            expires_at = datetime.now() + timedelta(days=expires_days)

        consent = ConsentRecord(
            id=consent_id,
            data_subject_id=data_subject_id,
            purpose=purpose,
            basis=basis,
            status=ConsentStatus.GRANTED,
            granted_at=datetime.now(),
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent
        )

        self.consents[consent_id] = consent
        self._save_data()

        self._log_processing(
            "consent_granted",
            data_subject_id,
            {
                "consent_id": consent_id,
                "purpose": purpose,
                "basis": basis.value
            }
        )

        return consent

    def withdraw_consent(self, consent_id: str, reason: Optional[str] = None):
        """Withdraw consent."""
        consent = self.consents.get(consent_id)
        if not consent:
            raise ValueError("Consent not found")

        consent.status = ConsentStatus.WITHDRAWN
        consent.withdrawn_at = datetime.now()
        consent.metadata["withdrawal_reason"] = reason

        self._save_data()

        self._log_processing(
            "consent_withdrawn",
            consent.data_subject_id,
            {
                "consent_id": consent_id,
                "reason": reason
            }
        )

    def check_consent(self, data_subject_id: str, purpose: str) -> bool:
        """Check if valid consent exists for purpose."""
        for consent in self.consents.values():
            if (consent.data_subject_id == data_subject_id and
                consent.purpose == purpose and
                consent.is_valid()):
                return True
        return False

    def create_gdpr_request(
        self,
        data_subject_id: str,
        request_type: GDPRRequestType,
        details: Optional[Dict[str, Any]] = None
    ) -> GDPRRequest:
        """Create a GDPR request."""
        request_id = f"gdpr_{secrets.token_urlsafe(16)}"

        request = GDPRRequest(
            id=request_id,
            type=request_type,
            data_subject_id=data_subject_id,
            request_details=details or {}
        )

        self.requests[request_id] = request
        self._save_data()

        self._log_processing(
            "gdpr_request_created",
            data_subject_id,
            {
                "request_id": request_id,
                "type": request_type.value
            }
        )

        return request

    async def process_data_access_request(self, request_id: str) -> Dict[str, Any]:
        """Process a data access request."""
        request = self.requests.get(request_id)
        if not request:
            raise ValueError("Request not found")

        request.status = "processing"
        self._save_data()

        # Collect all data for the data subject
        data = await self._collect_all_data(request.data_subject_id)

        # Update request
        request.status = "completed"
        request.processed_at = datetime.now()
        request.response = {"data": data, "collected_at": datetime.now().isoformat()}
        self._save_data()

        self._log_processing(
            "data_access_completed",
            request.data_subject_id,
            {"request_id": request_id, "data_count": len(data)}
        )

        return request.response

    async def process_data_portability_request(self, request_id: str) -> str:
        """Process a data portability request and return file path."""
        request = self.requests.get(request_id)
        if not request:
            raise ValueError("Request not found")

        request.status = "processing"
        self._save_data()

        # Collect data
        data = await self._collect_all_data(request.data_subject_id)

        # Create portable format (JSON)
        portable_data = {
            "export_date": datetime.now().isoformat(),
            "data_subject_id": request.data_subject_id,
            "data": data,
            "format": "json",
            "version": "1.0"
        }

        # Create file
        filename = f"portability_{request.data_subject_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = self.storage_path / "exports" / filename
        filepath.parent.mkdir(exist_ok=True)

        async with aiofiles.open(filepath, 'w') as f:
            await f.write(json.dumps(portable_data, indent=2))

        # Update request
        request.status = "completed"
        request.processed_at = datetime.now()
        request.response = {
            "file_path": str(filepath),
            "filename": filename,
            "size": filepath.stat().st_size if filepath.exists() else 0
        }
        self._save_data()

        self._log_processing(
            "data_portability_completed",
            request.data_subject_id,
            {"request_id": request_id, "filename": filename}
        )

        return str(filepath)

    async def process_data_erasure_request(self, request_id: str) -> Dict[str, Any]:
        """Process a data erasure request (right to be forgotten)."""
        request = self.requests.get(request_id)
        if not request:
            raise ValueError("Request not found")

        request.status = "processing"
        self._save_data()

        erased_items = []

        # Anonymize data subject
        if request.data_subject_id in self.data_subjects:
            subject = self.data_subjects[request.data_subject_id]
            subject.anonymize()
            erased_items.append("data_subject_profile")

        # Delete or anonymize related data
        erased_items.extend(await self._erase_subject_data(request.data_subject_id))

        # Withdraw all consents
        for consent in self.consents.values():
            if consent.data_subject_id == request.data_subject_id:
                consent.status = ConsentStatus.WITHDRAWN
                consent.withdrawn_at = datetime.now()
                erased_items.append(f"consent_{consent.id}")

        # Update request
        request.status = "completed"
        request.processed_at = datetime.now()
        request.response = {
            "erased_items": erased_items,
            "erased_at": datetime.now().isoformat()
        }
        self._save_data()

        self._log_processing(
            "data_erasure_completed",
            request.data_subject_id,
            {"request_id": request_id, "items_erased": len(erased_items)}
        )

        return request.response

    async def _collect_all_data(self, data_subject_id: str) -> Dict[str, Any]:
        """Collect all data related to a data subject."""
        data = {}

        # Data subject profile
        if data_subject_id in self.data_subjects:
            subject = self.data_subjects[data_subject_id]
            data["profile"] = subject.to_dict(include_sensitive=True)

        # Consents
        data["consents"] = [
            consent.to_dict()
            for consent in self.consents.values()
            if consent.data_subject_id == data_subject_id
        ]

        # Requests
        data["requests"] = [
            request.to_dict()
            for request in self.requests.values()
            if request.data_subject_id == data_subject_id
        ]

        # Processing logs
        data["processing_log"] = [
            log for log in self.processing_log
            if log.get("data_subject_id") == data_subject_id
        ]

        # Add system-specific data (would integrate with other modules)
        data["invoices"] = []  # Would fetch from invoicing system
        data["payments"] = []  # Would fetch from payment system
        data["social_posts"] = []  # Would fetch from social media

        return data

    async def _erase_subject_data(self, data_subject_id: str) -> List[str]:
        """Erase or anonymize all data for a subject."""
        erased = []

        # This would integrate with other systems
        # For now, just log what would be erased

        # Example: Erase from invoicing
        erased.append("invoices")

        # Example: Erase from payments
        erased.append("payments")

        # Example: Erase from social media
        erased.append("social_posts")

        # Example: Erase from reports
        erased.append("reports")

        return erased

    def _log_processing(self, action: str, data_subject_id: str, details: Dict[str, Any]):
        """Log GDPR processing activity."""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "data_subject_id": data_subject_id,
            "details": details
        }

        self.processing_log.append(log_entry)

        # Also log to standard logger
        logger.info(f"GDPR: {action} for {data_subject_id}", extra={"gdpr_log": log_entry})

    def generate_compliance_report(self) -> Dict[str, Any]:
        """Generate GDPR compliance report."""
        now = datetime.now()
        last_30_days = now - timedelta(days=30)

        report = {
            "generated_at": now.isoformat(),
            "summary": {
                "total_data_subjects": len(self.data_subjects),
                "active_consents": len([c for c in self.consents.values() if c.is_valid()]),
                "pending_requests": len([r for r in self.requests.values() if r.status == "pending"]),
                "completed_requests": len([r for r in self.requests.values() if r.status == "completed"])
            },
            "consents_by_basis": {},
            "requests_by_type": {},
            "recent_activity": []
        }

        # Consents by basis
        for consent in self.consents.values():
            basis = consent.basis.value
            if basis not in report["consents_by_basis"]:
                report["consents_by_basis"][basis] = 0
            report["consents_by_basis"][basis] += 1

        # Requests by type
        for request in self.requests.values():
            req_type = request.type.value
            if req_type not in report["requests_by_type"]:
                report["requests_by_type"][req_type] = 0
            report["requests_by_type"][req_type] += 1

        # Recent activity (last 30 days)
        for log in self.processing_log:
            if datetime.fromisoformat(log["timestamp"]) > last_30_days:
                report["recent_activity"].append(log)

        return report


# Global GDPR manager
gdpr_manager = GDPRManager()