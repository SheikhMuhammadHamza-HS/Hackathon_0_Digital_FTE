"""Data retention API endpoints."""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..utils.data_retention import (
    DataRetentionManager,
    RetentionPolicy,
    DataCategory,
    RetentionAction,
    retention_manager
)
from .auth import get_current_user, User, require_level, SecurityLevel

router = APIRouter(prefix="/api/v1/retention", tags=["data-retention"])


class RetentionPolicyRequest(BaseModel):
    """Request model for creating/updating retention policies."""
    category: str = Field(..., description="Data category")
    retention_days: int = Field(..., gt=0, description="Retention period in days")
    action: str = Field(..., description="Action: keep, archive, delete, anonymize")
    archive_location: Optional[str] = Field(None, description="Archive location path")
    compression: bool = Field(True, description="Compress archived data")
    exceptions: List[str] = Field(default_factory=list, description="Paths to exclude")
    description: str = Field("", description="Policy description")


class RetentionPolicyResponse(BaseModel):
    """Response model for retention policies."""
    category: str
    retention_days: int
    action: str
    archive_location: Optional[str]
    compression: bool
    exceptions: List[str]
    description: str


class RetentionExecutionRequest(BaseModel):
    """Request model for retention execution."""
    dry_run: bool = Field(False, description="Perform dry run without making changes")
    categories: Optional[List[str]] = Field(None, description="Specific categories to process")


class RetentionExecutionResponse(BaseModel):
    """Response model for retention execution results."""
    scanned: int
    processed: int
    archived: int
    deleted: int
    anonymized: int
    errors: int
    dry_run: bool
    execution_time: Optional[float] = None


@router.get("/policies", response_model=Dict[str, RetentionPolicyResponse])
async def get_retention_policies(user: User = Depends(require_level(SecurityLevel.ADMIN))):
    """Get all retention policies."""
    policies = {}

    for category, policy in retention_manager.policies.items():
        policies[category.value] = RetentionPolicyResponse(
            category=category.value,
            retention_days=policy.retention_days,
            action=policy.action.value,
            archive_location=policy.archive_location,
            compression=policy.compression,
            exceptions=policy.exceptions,
            description=policy.description
        )

    return policies


@router.get("/policies/{category}", response_model=RetentionPolicyResponse)
async def get_retention_policy(
    category: str,
    user: User = Depends(require_level(SecurityLevel.ADMIN))
):
    """Get a specific retention policy."""
    try:
        data_category = DataCategory(category)
        policy = retention_manager.policies.get(data_category)

        if not policy:
            raise HTTPException(status_code=404, detail="Policy not found")

        return RetentionPolicyResponse(
            category=policy.category.value,
            retention_days=policy.retention_days,
            action=policy.action.value,
            archive_location=policy.archive_location,
            compression=policy.compression,
            exceptions=policy.exceptions,
            description=policy.description
        )

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid category")


@router.post("/policies", response_model=RetentionPolicyResponse)
async def create_retention_policy(
    request: RetentionPolicyRequest,
    user: User = Depends(require_level(SecurityLevel.ADMIN))
):
    """Create or update a retention policy."""
    try:
        data_category = DataCategory(request.category)
        action = RetentionAction(request.action)

        policy = RetentionPolicy(
            category=data_category,
            retention_days=request.retention_days,
            action=action,
            archive_location=request.archive_location,
            compression=request.compression,
            exceptions=request.exceptions,
            description=request.description
        )

        retention_manager.add_policy(policy)

        return RetentionPolicyResponse(
            category=policy.category.value,
            retention_days=policy.retention_days,
            action=policy.action.value,
            archive_location=policy.archive_location,
            compression=policy.compression,
            exceptions=policy.exceptions,
            description=policy.description
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/policies/{category}")
async def delete_retention_policy(
    category: str,
    user: User = Depends(require_level(SecurityLevel.ADMIN))
):
    """Delete a retention policy."""
    try:
        data_category = DataCategory(category)

        if data_category not in retention_manager.policies:
            raise HTTPException(status_code=404, detail="Policy not found")

        retention_manager.remove_policy(data_category)

        return {"message": f"Policy for {category} deleted successfully"}

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid category")


@router.post("/execute", response_model=RetentionExecutionResponse)
async def execute_retention_policies(
    request: RetentionExecutionRequest,
    user: User = Depends(require_level(SecurityLevel.ADMIN))
):
    """Execute retention policies."""
    import time

    start_time = time.time()

    try:
        # Execute retention policies
        results = await retention_manager.apply_retention_policies(dry_run=request.dry_run)

        results["execution_time"] = time.time() - start_time

        return RetentionExecutionResponse(**results)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Retention execution failed: {str(e)}")


@router.get("/report")
async def get_retention_report(user: User = Depends(require_level(SecurityLevel.USER))):
    """Get data retention report."""
    try:
        report = await retention_manager.get_retention_report()
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {str(e)}")


@router.get("/scan")
async def scan_data_directory(
    directory: str = Query(..., description="Directory to scan"),
    category: str = Query(..., description="Data category"),
    user: User = Depends(require_level(SecurityLevel.ADMIN))
):
    """Scan a directory for retention analysis."""
    try:
        data_category = DataCategory(category)
        items = await retention_manager.scan_directory(directory, data_category)

        # Analyze items
        policy = retention_manager.policies.get(data_category)
        expired_count = 0
        total_size = 0

        for item in items:
            total_size += item.size
            if policy and policy.is_expired(item.modified_at):
                expired_count += 1

        return {
            "directory": directory,
            "category": category,
            "total_items": len(items),
            "expired_items": expired_count,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "policy": {
                "retention_days": policy.retention_days if policy else None,
                "action": policy.action.value if policy else None
            },
            "sample_items": [item.to_dict() for item in items[:10]]  # First 10 items
        }

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid category")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scan failed: {str(e)}")


@router.get("/logs")
async def get_retention_logs(
    limit: int = Query(100, ge=1, le=1000),
    action: Optional[str] = Query(None, description="Filter by action type"),
    user: User = Depends(require_level(SecurityLevel.ADMIN))
):
    """Get retention action logs."""
    try:
        logs = retention_manager.retention_log

        # Filter by action if specified
        if action:
            logs = [log for log in logs if action in log.get("action", "")]

        # Return most recent logs
        recent_logs = logs[-limit:]

        return {
            "logs": recent_logs,
            "total": len(logs),
            "showing": len(recent_logs)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get logs: {str(e)}")


@router.get("/statistics")
async def get_retention_statistics(user: User = Depends(require_level(SecurityLevel.USER))):
    """Get retention statistics and insights."""
    try:
        # Calculate statistics from policies
        stats = {
            "total_policies": len(retention_manager.policies),
            "policies_by_action": {},
            "policies_by_category": {},
            "average_retention_days": 0,
            "longest_retention": {"days": 0, "category": ""},
            "shortest_retention": {"days": float('inf'), "category": ""}
        }

        total_days = 0

        for category, policy in retention_manager.policies.items():
            # By category
            stats["policies_by_category"][category.value] = {
                "retention_days": policy.retention_days,
                "action": policy.action.value
            }

            # By action
            action = policy.action.value
            if action not in stats["policies_by_action"]:
                stats["policies_by_action"][action] = 0
            stats["policies_by_action"][action] += 1

            # Retention periods
            total_days += policy.retention_days

            if policy.retention_days > stats["longest_retention"]["days"]:
                stats["longest_retention"] = {
                    "days": policy.retention_days,
                    "category": category.value
                }

            if policy.retention_days < stats["shortest_retention"]["days"]:
                stats["shortest_retention"] = {
                    "days": policy.retention_days,
                    "category": category.value
                }

        # Calculate average
        if retention_manager.policies:
            stats["average_retention_days"] = total_days / len(retention_manager.policies)

        # Recent activity summary
        cutoff = datetime.now() - timedelta(days=7)
        recent_logs = [
            log for log in retention_manager.retention_log
            if datetime.fromisoformat(log["timestamp"]) > cutoff
        ]

        stats["recent_activity"] = {
            "last_7_days": len(recent_logs),
            "actions_by_type": {}
        }

        for log in recent_logs:
            action = log.get("action", "unknown")
            if action not in stats["recent_activity"]["actions_by_type"]:
                stats["recent_activity"]["actions_by_type"][action] = 0
            stats["recent_activity"]["actions_by_type"][action] += 1

        return stats

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get statistics: {str(e)}")


@router.post("/export-policies")
async def export_retention_policies(
    format: str = Query("json", regex="^(json|yaml)$"),
    user: User = Depends(require_level(SecurityLevel.ADMIN))
):
    """Export retention policies configuration."""
    try:
        policies_dict = {}

        for category, policy in retention_manager.policies.items():
            policies_dict[category.value] = {
                "retention_days": policy.retention_days,
                "action": policy.action.value,
                "archive_location": policy.archive_location,
                "compression": policy.compression,
                "exceptions": policy.exceptions,
                "description": policy.description
            }

        if format == "json":
            return policies_dict
        elif format == "yaml":
            import yaml
            return yaml.dump(policies_dict, default_flow_style=False)

    except ImportError:
        raise HTTPException(status_code=400, detail="YAML format not available (install PyYAML)")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.post("/import-policies")
async def import_retention_policies(
    policies: Dict[str, Any],
    overwrite: bool = Query(False, description="Overwrite existing policies"),
    user: User = Depends(require_level(SecurityLevel.ADMIN))
):
    """Import retention policies configuration."""
    try:
        imported = 0
        errors = []

        for category_str, policy_data in policies.items():
            try:
                category = DataCategory(category_str)
                action = RetentionAction(policy_data.get("action", "keep"))

                # Check if policy exists
                if category in retention_manager.policies and not overwrite:
                    errors.append(f"Policy for {category_str} already exists (use overwrite=true)")
                    continue

                policy = RetentionPolicy(
                    category=category,
                    retention_days=policy_data.get("retention_days", 730),
                    action=action,
                    archive_location=policy_data.get("archive_location"),
                    compression=policy_data.get("compression", True),
                    exceptions=policy_data.get("exceptions", []),
                    description=policy_data.get("description", "")
                )

                retention_manager.add_policy(policy)
                imported += 1

            except (ValueError, KeyError) as e:
                errors.append(f"Invalid policy for {category_str}: {str(e)}")

        return {
            "imported": imported,
            "errors": errors,
            "total": len(policies)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")