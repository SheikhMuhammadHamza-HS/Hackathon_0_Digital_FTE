"""GDPR compliance API endpoints."""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, EmailStr
import tempfile
import os

from ..utils.gdpr import (
    GDPRManager,
    DataSubject,
    ConsentRecord,
    GDPRRequest,
    GDPRRequestType,
    ConsentStatus,
    DataProcessingBasis,
    gdpr_manager
)
from .auth import get_current_user, User, require_level, SecurityLevel

router = APIRouter(prefix="/api/v1/gdpr", tags=["gdpr"])


class DataSubjectRequest(BaseModel):
    """Request model for creating a data subject."""
    email: EmailStr = Field(..., description="Data subject email")
    name: Optional[str] = Field(None, description="Full name")
    phone: Optional[str] = Field(None, description="Phone number")
    address: Optional[str] = Field(None, description="Address")
    dob: Optional[str] = Field(None, description="Date of birth (YYYY-MM-DD)")
    preferences: Dict[str, Any] = Field(default_factory=dict)


class ConsentRequest(BaseModel):
    """Request model for recording consent."""
    data_subject_id: str = Field(..., description="Data subject ID")
    purpose: str = Field(..., description="Purpose of processing")
    basis: str = Field(..., description="Legal basis: consent, contract, legal_obligation, vital_interests, public_task, legitimate_interests")
    expires_days: Optional[int] = Field(None, description="Consent expiration in days")
    ip_address: Optional[str] = Field(None, description="IP address of consent")
    user_agent: Optional[str] = Field(None, description="User agent")


class GDPRRequestCreate(BaseModel):
    """Request model for creating GDPR request."""
    data_subject_id: str = Field(..., description="Data subject ID")
    request_type: str = Field(..., description="Request type")
    details: Dict[str, Any] = Field(default_factory=dict)


class DataSubjectResponse(BaseModel):
    """Response model for data subject."""
    id: str
    email: str
    name: Optional[str]
    phone: Optional[str]
    address: Optional[str]
    dob: Optional[str]
    created_at: str
    last_activity: str
    preferences: Dict[str, Any]


class ConsentResponse(BaseModel):
    """Response model for consent."""
    id: str
    data_subject_id: str
    purpose: str
    basis: str
    status: str
    granted_at: str
    expires_at: Optional[str]
    withdrawn_at: Optional[str]


@router.post("/data-subjects", response_model=DataSubjectResponse)
async def create_data_subject(
    request: DataSubjectRequest,
    user: User = Depends(require_level(SecurityLevel.USER))
):
    """Create a new data subject."""
    try:
        # Parse DOB if provided
        dob = None
        if request.dob:
            dob = datetime.strptime(request.dob, "%Y-%m-%d")

        subject = gdpr_manager.create_data_subject(
            email=request.email,
            name=request.name,
            phone=request.phone,
            address=request.address,
            dob=dob,
            preferences=request.preferences
        )

        return DataSubjectResponse(
            id=subject.id,
            email=subject.email,
            name=subject.name,
            phone=subject.phone,
            address=subject.address,
            dob=subject.dob.isoformat() if subject.dob else None,
            created_at=subject.created_at.isoformat(),
            last_activity=subject.last_activity.isoformat(),
            preferences=subject.preferences
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create data subject: {str(e)}")


@router.get("/data-subjects/{subject_id}", response_model=DataSubjectResponse)
async def get_data_subject(
    subject_id: str,
    user: User = Depends(require_level(SecurityLevel.USER))
):
    """Get data subject information."""
    try:
        subject = gdpr_manager.data_subjects.get(subject_id)
        if not subject:
            raise HTTPException(status_code=404, detail="Data subject not found")

        return DataSubjectResponse(
            id=subject.id,
            email=subject.email,
            name=subject.name,
            phone=subject.phone,
            address=subject.address,
            dob=subject.dob.isoformat() if subject.dob else None,
            created_at=subject.created_at.isoformat(),
            last_activity=subject.last_activity.isoformat(),
            preferences=subject.preferences
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get data subject: {str(e)}")


@router.post("/consents", response_model=ConsentResponse)
async def record_consent(
    request: ConsentRequest,
    user: User = Depends(get_current_user)
):
    """Record consent from data subject."""
    try:
        basis = DataProcessingBasis(request.basis)
        consent = gdpr_manager.record_consent(
            data_subject_id=request.data_subject_id,
            purpose=request.purpose,
            basis=basis,
            expires_days=request.expires_days,
            ip_address=request.ip_address,
            user_agent=request.user_agent
        )

        return ConsentResponse(
            id=consent.id,
            data_subject_id=consent.data_subject_id,
            purpose=consent.purpose,
            basis=consent.basis.value,
            status=consent.status.value,
            granted_at=consent.granted_at.isoformat(),
            expires_at=consent.expires_at.isoformat() if consent.expires_at else None,
            withdrawn_at=consent.withdrawn_at.isoformat() if consent.withdrawn_at else None
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to record consent: {str(e)}")


@router.post("/consents/{consent_id}/withdraw")
async def withdraw_consent(
    consent_id: str,
    reason: Optional[str] = None,
    user: User = Depends(get_current_user)
):
    """Withdraw consent."""
    try:
        gdpr_manager.withdraw_consent(consent_id, reason)
        return {"message": "Consent withdrawn successfully"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to withdraw consent: {str(e)}")


@router.get("/data-subjects/{subject_id}/consents")
async def get_subject_consents(
    subject_id: str,
    user: User = Depends(require_level(SecurityLevel.USER))
):
    """Get all consents for a data subject."""
    try:
        consents = [
            ConsentResponse(
                id=consent.id,
                data_subject_id=consent.data_subject_id,
                purpose=consent.purpose,
                basis=consent.basis.value,
                status=consent.status.value,
                granted_at=consent.granted_at.isoformat(),
                expires_at=consent.expires_at.isoformat() if consent.expires_at else None,
                withdrawn_at=consent.withdrawn_at.isoformat() if consent.withdrawn_at else None
            )
            for consent in gdpr_manager.consents.values()
            if consent.data_subject_id == subject_id
        ]

        return {"consents": consents, "total": len(consents)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get consents: {str(e)}")


@router.post("/requests", response_model=Dict[str, Any])
async def create_gdpr_request(
    request: GDPRRequestCreate,
    user: User = Depends(get_current_user)
):
    """Create a GDPR request."""
    try:
        request_type = GDPRRequestType(request.request_type)
        gdpr_request = gdpr_manager.create_gdpr_request(
            data_subject_id=request.data_subject_id,
            request_type=request_type,
            details=request.details
        )

        return {
            "request_id": gdpr_request.id,
            "type": gdpr_request.type.value,
            "status": gdpr_request.status,
            "created_at": gdpr_request.created_at.isoformat(),
            "message": "GDPR request created successfully"
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create request: {str(e)}")


@router.get("/requests/{request_id}")
async def get_gdpr_request(
    request_id: str,
    user: User = Depends(require_level(SecurityLevel.USER))
):
    """Get GDPR request details."""
    try:
        request = gdpr_manager.requests.get(request_id)
        if not request:
            raise HTTPException(status_code=404, detail="Request not found")

        return request.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get request: {str(e)}")


@router.post("/requests/{request_id}/process")
async def process_gdpr_request(
    request_id: str,
    user: User = Depends(require_level(SecurityLevel.ADMIN))
):
    """Process a GDPR request."""
    try:
        request = gdpr_manager.requests.get(request_id)
        if not request:
            raise HTTPException(status_code=404, detail="Request not found")

        if request.status == "completed":
            return {"message": "Request already completed", "response": request.response}

        # Process based on request type
        if request.type == GDPRRequestType.DATA_ACCESS:
            result = await gdpr_manager.process_data_access_request(request_id)
        elif request.type == GDPRRequestType.DATA_PORTABILITY:
            file_path = await gdpr_manager.process_data_portability_request(request_id)
            return {
                "message": "Data portability file created",
                "file_path": file_path,
                "download_url": f"/api/v1/gdpr/requests/{request_id}/download"
            }
        elif request.type == GDPRRequestType.DATA_ERASURE:
            result = await gdpr_manager.process_data_erasure_request(request_id)
        else:
            raise HTTPException(status_code=400, detail="Request type not supported for processing")

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process request: {str(e)}")


@router.get("/requests/{request_id}/download")
async def download_portability_file(
    request_id: str,
    user: User = Depends(require_level(SecurityLevel.USER))
):
    """Download data portability file."""
    try:
        request = gdpr_manager.requests.get(request_id)
        if not request:
            raise HTTPException(status_code=404, detail="Request not found")

        if request.type != GDPRRequestType.DATA_PORTABILITY:
            raise HTTPException(status_code=400, detail="Not a portability request")

        if not request.response or "file_path" not in request.response:
            raise HTTPException(status_code=400, detail="File not ready")

        file_path = Path(request.response["file_path"])
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")

        return FileResponse(
            path=file_path,
            filename=request.response["filename"],
            media_type="application/json"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to download file: {str(e)}")


@router.get("/requests")
async def list_gdpr_requests(
    subject_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(50, ge=1, le=1000),
    user: User = Depends(require_level(SecurityLevel.USER))
):
    """List GDPR requests."""
    try:
        requests = list(gdpr_manager.requests.values())

        # Filter by subject ID
        if subject_id:
            requests = [r for r in requests if r.data_subject_id == subject_id]

        # Filter by status
        if status:
            requests = [r for r in requests if r.status == status]

        # Sort by creation date (newest first)
        requests.sort(key=lambda x: x.created_at, reverse=True)

        # Limit results
        requests = requests[:limit]

        return {
            "requests": [r.to_dict() for r in requests],
            "total": len(requests)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list requests: {str(e)}")


@router.post("/data-subjects/{subject_id}/anonymize")
async def anonymize_data_subject(
    subject_id: str,
    reason: str = "User request",
    user: User = Depends(require_level(SecurityLevel.ADMIN))
):
    """Anonymize a data subject's data."""
    try:
        subject = gdpr_manager.data_subjects.get(subject_id)
        if not subject:
            raise HTTPException(status_code=404, detail="Data subject not found")

        # Anonymize
        subject.anonymize()
        gdpr_manager._save_data()

        # Log action
        gdpr_manager._log_processing(
            "data_subject_anonymized",
            subject_id,
            {"reason": reason, "anonymized_at": datetime.now().isoformat()}
        )

        return {"message": "Data subject anonymized successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to anonymize: {str(e)}")


@router.get("/compliance/report")
async def get_compliance_report(
    user: User = Depends(require_level(SecurityLevel.USER))
):
    """Get GDPR compliance report."""
    try:
        report = gdpr_manager.generate_compliance_report()
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {str(e)}")


@router.get("/consents/check")
async def check_consent(
    subject_id: str,
    purpose: str,
    user: User = Depends(get_current_user)
):
    """Check if valid consent exists."""
    try:
        has_consent = gdpr_manager.check_consent(subject_id, purpose)
        return {
            "data_subject_id": subject_id,
            "purpose": purpose,
            "has_consent": has_consent
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to check consent: {str(e)}")


@router.post("/consents/{subject_id}/batch")
async def batch_record_consents(
    subject_id: str,
    consents: List[dict],
    user: User = Depends(get_current_user)
):
    """Record multiple consents at once."""
    try:
        results = []
        errors = []

        for consent_data in consents:
            try:
                basis = DataProcessingBasis(consent_data["basis"])
                consent = gdpr_manager.record_consent(
                    data_subject_id=subject_id,
                    purpose=consent_data["purpose"],
                    basis=basis,
                    expires_days=consent_data.get("expires_days"),
                    ip_address=consent_data.get("ip_address"),
                    user_agent=consent_data.get("user_agent")
                )
                results.append({
                    "consent_id": consent.id,
                    "purpose": consent.purpose,
                    "status": "success"
                })
            except Exception as e:
                errors.append({
                    "consent_data": consent_data,
                    "error": str(e)
                })

        return {
            "processed": len(consents),
            "successful": len(results),
            "errors": len(errors),
            "results": results,
            "error_details": errors
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to record consents: {str(e)}")


@router.get("/export/data-subjects")
async def export_data_subjects(
    format: str = Query("json", regex="^(json|csv)$"),
    user: User = Depends(require_level(SecurityLevel.ADMIN))
):
    """Export all data subjects."""
    try:
        subjects = list(gdpr_manager.data_subjects.values())
        data = [subject.to_dict(include_sensitive=True) for subject in subjects]

        if format == "json":
            return {"data_subjects": data, "exported_at": datetime.now().isoformat()}
        elif format == "csv":
            # Create CSV file
            output = io.StringIO()
            if data:
                writer = csv.DictWriter(output, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)

            csv_content = output.getvalue()
            output.close()

            return Response(
                content=csv_content,
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename=data_subjects_{datetime.now().strftime('%Y%m%d')}.csv"}
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to export: {str(e)}")


@router.post("/import/data-subjects")
async def import_data_subjects(
    file: UploadFile = File(...),
    user: User = Depends(require_level(SecurityLevel.ADMIN))
):
    """Import data subjects from file."""
    try:
        # Read file
        content = await file.read()
        if file.filename.endswith('.json'):
            data = json.loads(content)
            subjects = data.get("data_subjects", data)
        else:
            # Parse CSV
            import csv
            from io import StringIO

            csv_data = content.decode('utf-8')
            reader = csv.DictReader(StringIO(csv_data))
            subjects = list(reader)

        # Import subjects
        imported = 0
        errors = []

        for subject_data in subjects:
            try:
                # Parse DOB if present
                dob = None
                if subject_data.get("dob"):
                    dob = datetime.strptime(subject_data["dob"], "%Y-%m-%d")

                subject = gdpr_manager.create_data_subject(
                    email=subject_data["email"],
                    name=subject_data.get("name"),
                    phone=subject_data.get("phone"),
                    address=subject_data.get("address"),
                    dob=dob,
                    preferences=json.loads(subject_data.get("preferences", "{}"))
                )
                imported += 1
            except Exception as e:
                errors.append({
                    "email": subject_data.get("email", "unknown"),
                    "error": str(e)
                })

        return {
            "imported": imported,
            "total": len(subjects),
            "errors": len(errors),
            "error_details": errors
        }

    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON file")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to import: {str(e)}")


@router.get("/dashboard")
async def get_gdpr_dashboard(user: User = Depends(require_level(SecurityLevel.USER))):
    """Get GDPR dashboard overview."""
    try:
        report = gdpr_manager.generate_compliance_report()

        # Additional dashboard metrics
        dashboard = {
            "summary": report["summary"],
            "charts": {
                "consents_by_basis": report["consents_by_basis"],
                "requests_by_type": report["requests_by_type"]
            },
            "alerts": []
        }

        # Generate alerts
        if report["summary"]["pending_requests"] > 0:
            dashboard["alerts"].append({
                "type": "warning",
                "message": f"{report['summary']['pending_requests']} pending GDPR requests"
            })

        # Check expired consents
        expired_consents = len([
            c for c in gdpr_manager.consents.values()
            if c.expires_at and datetime.now() > c.expires_at and c.status == ConsentStatus.GRANTED
        ])
        if expired_consents > 0:
            dashboard["alerts"].append({
                "type": "error",
                "message": f"{expired_consents} consents have expired"
            })

        return dashboard

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get dashboard: {str(e)}")