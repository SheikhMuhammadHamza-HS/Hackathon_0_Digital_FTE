"""
Backup and Restore API Endpoints
Provides REST API for backup management, restore operations, and backup scheduling
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, Query
from pydantic import BaseModel, Field
import asyncio

from ..utils.backup_manager import backup_manager
from ..utils.auth import get_current_user, require_permission
from ..utils.logger import setup_logger

logger = setup_logger(__name__)
router = APIRouter(prefix="/api/v1/backup", tags=["backup"])

# Pydantic models for request/response
class BackupRequest(BaseModel):
    backup_type: str = Field(default="daily", regex="^(daily|weekly|monthly|manual)$")
    include_media: bool = Field(default=True)
    encrypt: bool = Field(default=True)
    comment: Optional[str] = Field(default=None)

class RestoreRequest(BaseModel):
    backup_id: str = Field(..., description="ID of backup to restore")
    restore_components: Optional[List[str]] = Field(
        default=None,
        description="Components to restore (database, config, user_data, logs, media)"
    )
    force: bool = Field(default=False, description="Force restore without confirmation")

class BackupResponse(BaseModel):
    status: str
    backup_id: Optional[str] = None
    archive_path: Optional[str] = None
    size_mb: Optional[float] = None
    checksum: Optional[str] = None
    message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class RestoreResponse(BaseModel):
    status: str
    message: str
    restored_components: Optional[List[str]] = None
    results: Optional[Dict[str, Any]] = None

class BackupInfo(BaseModel):
    backup_id: str
    type: str
    created_at: str
    archive_path: str
    size_mb: float
    checksum: str
    includes_media: bool
    encrypted: bool
    comment: str

class BackupVerificationResponse(BaseModel):
    status: str
    message: str
    metadata: Optional[Dict[str, Any]] = None
    issues: Optional[List[str]] = None
    expected: Optional[str] = None
    actual: Optional[str] = None

class BackupStatistics(BaseModel):
    total_backups: int
    total_size_mb: float
    oldest_backup: Optional[str]
    newest_backup: Optional[str]
    by_type: Dict[str, Dict[str, Any]]
    storage_path: str
    encryption_enabled: bool

@router.post("/create", response_model=BackupResponse)
async def create_backup(
    request: BackupRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new backup

    Requires backup management permission
    """
    # Check permission
    if not require_permission(current_user, "backup:manage"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    try:
        # Create backup
        result = await backup_manager.create_backup(
            backup_type=request.backup_type,
            include_media=request.include_media,
            encrypt=request.encrypt,
            comment=request.comment
        )

        if result["status"] == "error":
            raise HTTPException(status_code=500, detail=result["message"])

        logger.info(f"Backup created by user {current_user['username']}: {result['backup_id']}")

        return BackupResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Backup creation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Backup creation failed: {str(e)}")

@router.post("/create/background")
async def create_backup_background(
    request: BackupRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """
    Create a backup in the background

    Requires backup management permission
    """
    if not require_permission(current_user, "backup:manage"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    # Add to background tasks
    background_tasks.add_task(
        backup_manager.create_backup,
        backup_type=request.backup_type,
        include_media=request.include_media,
        encrypt=request.encrypt,
        comment=request.comment
    )

    logger.info(f"Background backup initiated by user {current_user['username']}")

    return {
        "status": "accepted",
        "message": "Backup creation started in background",
        "backup_type": request.backup_type
    }

@router.get("/list", response_model=List[BackupInfo])
async def list_backups(
    backup_type: Optional[str] = Query(None, regex="^(daily|weekly|monthly|manual)$"),
    current_user: dict = Depends(get_current_user)
):
    """
    List available backups

    Requires backup view permission
    """
    if not require_permission(current_user, "backup:view"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    try:
        backups = await backup_manager.list_backups(backup_type=backup_type)
        return [BackupInfo(**backup) for backup in backups]

    except Exception as e:
        logger.error(f"Failed to list backups: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list backups: {str(e)}")

@router.get("/verify/{backup_id}", response_model=BackupVerificationResponse)
async def verify_backup(
    backup_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Verify backup integrity

    Requires backup view permission
    """
    if not require_permission(current_user, "backup:view"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    try:
        result = await backup_manager.verify_backup(backup_id)
        return BackupVerificationResponse(**result)

    except Exception as e:
        logger.error(f"Backup verification failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Backup verification failed: {str(e)}")

@router.post("/restore", response_model=RestoreResponse)
async def restore_backup(
    request: RestoreRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """
    Restore from backup

    Requires system administration permission
    """
    if not require_permission(current_user, "system:admin"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    try:
        # Verify backup exists first
        verification = await backup_manager.verify_backup(request.backup_id)
        if verification.status == "error":
            raise HTTPException(status_code=404, detail="Backup not found or corrupted")

        # For safety, require force flag or implement confirmation mechanism
        if not request.force:
            # In a real implementation, you might want to send a confirmation email
            # or require a second token for sensitive operations
            raise HTTPException(
                status_code=400,
                detail="Restore operation requires force=True flag. This is a destructive operation."
            )

        # Perform restore
        result = await backup_manager.restore_backup(
            backup_id=request.backup_id,
            restore_components=request.restore_components,
            force=request.force
        )

        logger.warning(f"Backup restore performed by user {current_user['username']}: {request.backup_id}")

        return RestoreResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Backup restore failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Backup restore failed: {str(e)}")

@router.post("/restore/background")
async def restore_backup_background(
    request: RestoreRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """
    Restore from backup in background

    Requires system administration permission
    """
    if not require_permission(current_user, "system:admin"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    if not request.force:
        raise HTTPException(
            status_code=400,
            detail="Restore operation requires force=True flag"
        )

    # Add to background tasks
    background_tasks.add_task(
        backup_manager.restore_backup,
        backup_id=request.backup_id,
        restore_components=request.restore_components,
        force=request.force
    )

    logger.warning(f"Background backup restore initiated by user {current_user['username']}: {request.backup_id}")

    return {
        "status": "accepted",
        "message": "Backup restore started in background",
        "backup_id": request.backup_id
    }

@router.get("/statistics", response_model=BackupStatistics)
async def get_backup_statistics(
    current_user: dict = Depends(get_current_user)
):
    """
    Get backup statistics

    Requires backup view permission
    """
    if not require_permission(current_user, "backup:view"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    try:
        stats = await backup_manager.get_backup_statistics()
        return BackupStatistics(**stats)

    except Exception as e:
        logger.error(f"Failed to get backup statistics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get backup statistics: {str(e)}")

@router.post("/schedule/automatic")
async def schedule_automatic_backups(
    current_user: dict = Depends(get_current_user)
):
    """
    Schedule automatic backups

    Requires system administration permission
    """
    if not require_permission(current_user, "system:admin"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    try:
        await backup_manager.schedule_automatic_backups()
        logger.info(f"Automatic backup schedules configured by user {current_user['username']}")

        return {
            "status": "success",
            "message": "Automatic backup schedules configured",
            "schedules": {
                "daily": "2:00 AM every day",
                "weekly": "3:00 AM every Sunday",
                "monthly": "4:00 AM on 1st of month"
            }
        }

    except Exception as e:
        logger.error(f"Failed to schedule automatic backups: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to schedule automatic backups: {str(e)}")

@router.delete("/{backup_id}")
async def delete_backup(
    backup_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Delete a backup

    Requires backup management permission
    """
    if not require_permission(current_user, "backup:manage"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    try:
        # Get backup info
        backups = await backup_manager.list_backups()
        backup_info = None

        for backup in backups:
            if backup["backup_id"] == backup_id:
                backup_info = backup
                break

        if not backup_info:
            raise HTTPException(status_code=404, detail="Backup not found")

        # Delete backup file
        from pathlib import Path
        backup_path = Path(backup_manager.backup_dir) / backup_info["archive_path"]

        if backup_path.exists():
            backup_path.unlink()
        else:
            raise HTTPException(status_code=404, detail="Backup file not found")

        # Update registry
        import json
        import aiofiles
        registry_file = backup_manager.backup_dir / "backup_registry.json"

        async with aiofiles.open(registry_file, 'r') as f:
            content = await f.read()
            registry = json.loads(content)

        registry["backups"] = [b for b in registry["backups"] if b["backup_id"] != backup_id]

        async with aiofiles.open(registry_file, 'w') as f:
            await f.write(json.dumps(registry, indent=2))

        logger.info(f"Backup deleted by user {current_user['username']}: {backup_id}")

        return {
            "status": "success",
            "message": f"Backup {backup_id} deleted successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete backup: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete backup: {str(e)}")

@router.get("/download/{backup_id}")
async def download_backup(
    backup_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Generate download URL for backup

    Requires backup view permission
    """
    if not require_permission(current_user, "backup:view"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    try:
        # Get backup info
        backups = await backup_manager.list_backups()
        backup_info = None

        for backup in backups:
            if backup["backup_id"] == backup_id:
                backup_info = backup
                break

        if not backup_info:
            raise HTTPException(status_code=404, detail="Backup not found")

        from pathlib import Path
        backup_path = Path(backup_manager.backup_dir) / backup_info["archive_path"]

        if not backup_path.exists():
            raise HTTPException(status_code=404, detail="Backup file not found")

        # In a real implementation, you would generate a signed URL
        # or use a file streaming response
        from fastapi.responses import FileResponse

        logger.info(f"Backup download requested by user {current_user['username']}: {backup_id}")

        return FileResponse(
            path=str(backup_path),
            filename=backup_path.name,
            media_type='application/gzip'
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to download backup: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to download backup: {str(e)}")

@router.get("/health")
async def backup_health_check():
    """
    Health check for backup system
    """
    try:
        # Check backup directory
        from pathlib import Path
        backup_dir = backup_manager.backup_dir

        if not backup_dir.exists():
            return {
                "status": "warning",
                "message": "Backup directory does not exist",
                "backup_directory": str(backup_dir)
            }

        # Get basic stats
        backups = await backup_manager.list_backups()

        return {
            "status": "healthy",
            "backup_directory": str(backup_dir),
            "total_backups": len(backups),
            "encryption_enabled": backup_manager.cipher is not None,
            "last_backup": backups[0]["created_at"] if backups else None
        }

    except Exception as e:
        logger.error(f"Backup health check failed: {str(e)}")
        return {
            "status": "error",
            "message": f"Health check failed: {str(e)}"
        }

# Error handlers
@router.exception_handler(404)
async def backup_not_found_handler(request, exc):
    return {
        "error": "backup_not_found",
        "message": "The specified backup was not found",
        "status_code": 404
    }

@router.exception_handler(403)
async def permission_denied_handler(request, exc):
    return {
        "error": "permission_denied",
        "message": "You don't have permission to perform this action",
        "status_code": 403
    }

@router.exception_handler(500)
async def internal_error_handler(request, exc):
    logger.error(f"Internal server error in backup API: {str(exc)}")
    return {
        "error": "internal_server_error",
        "message": "An internal server error occurred",
        "status_code": 500
    }