"""
Health monitoring API endpoints for AI Employee system.

Provides REST API endpoints for accessing health status, metrics,
alerts, and system health information.
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, HTTPException, Query, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
import json

from ..utils.health_monitor import (
    get_health_monitor,
    HealthStatus,
    AlertSeverity,
    HealthReport,
    HealthAlert
)
from ..utils.logging_config import get_logger

logger = get_logger(__name__)

# Create router
router = APIRouter(prefix="/health", tags=["health"])

# Dependencies
async def get_health_monitor_dependency():
    """Get health monitor instance."""
    return get_health_monitor()


@router.get("/", response_model=Dict[str, Any])
async def get_health_status(
    monitor: Any = Depends(get_health_monitor_dependency)
):
    """Get overall system health status."""
    try:
        report = await monitor.generate_health_report()

        return {
            "status": report.overall_status.value,
            "timestamp": report.timestamp.isoformat(),
            "uptime_percentage": report.uptime_percentage,
            "checks_count": len(report.checks),
            "active_alerts": len(report.alerts),
            "response_time_ms": report.response_time_ms
        }
    except Exception as e:
        logger.error(f"Error getting health status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get health status")


@router.get("/detailed", response_model=Dict[str, Any])
async def get_detailed_health(
    monitor: Any = Depends(get_health_monitor_dependency)
):
    """Get detailed health report with all checks and metrics."""
    try:
        report = await monitor.generate_health_report()
        return report.to_dict()
    except Exception as e:
        logger.error(f"Error getting detailed health: {e}")
        raise HTTPException(status_code=500, detail="Failed to get detailed health")


@router.get("/checks", response_model=List[Dict[str, Any]])
async def get_health_checks(
    monitor: Any = Depends(get_health_monitor_dependency),
    status: Optional[str] = Query(None, description="Filter by status"),
    type: Optional[str] = Query(None, description="Filter by check type")
):
    """Get all health checks with their status."""
    try:
        checks = []

        for check_name, check in monitor._checks.items():
            # Apply filters
            if status and check.status.value != status:
                continue
            if type and check.check_type.value != type:
                continue

            check_data = {
                "name": check.name,
                "type": check.check_type.value,
                "description": check.description,
                "status": check.status.value,
                "enabled": check.enabled,
                "interval": check.interval,
                "last_check": check.last_check.isoformat() if check.last_check else None,
                "last_success": check.last_success.isoformat() if check.last_success else None,
                "last_failure": check.last_failure.isoformat() if check.last_failure else None,
                "consecutive_failures": check.consecutive_failures,
                "error_message": check.error_message,
                "metrics": [
                    {
                        "name": m.name,
                        "value": m.value,
                        "unit": m.unit,
                        "status": m.status.value,
                        "threshold_warning": m.threshold_warning,
                        "threshold_critical": m.threshold_critical
                    }
                    for m in check.metrics
                ]
            }
            checks.append(check_data)

        return checks
    except Exception as e:
        logger.error(f"Error getting health checks: {e}")
        raise HTTPException(status_code=500, detail="Failed to get health checks")


@router.get("/checks/{check_name}", response_model=Dict[str, Any])
async def get_health_check(
    check_name: str,
    monitor: Any = Depends(get_health_monitor_dependency)
):
    """Get specific health check details."""
    try:
        if check_name not in monitor._checks:
            raise HTTPException(status_code=404, detail=f"Health check '{check_name}' not found")

        check = monitor._checks[check_name]

        # Calculate uptime
        uptime = monitor.calculate_uptime(check_name)

        return {
            "name": check.name,
            "type": check.check_type.value,
            "description": check.description,
            "status": check.status.value,
            "enabled": check.enabled,
            "interval": check.interval,
            "timeout": check.timeout,
            "retries": check.retries,
            "uptime_percentage_24h": uptime,
            "last_check": check.last_check.isoformat() if check.last_check else None,
            "last_success": check.last_success.isoformat() if check.last_success else None,
            "last_failure": check.last_failure.isoformat() if check.last_failure else None,
            "consecutive_failures": check.consecutive_failures,
            "error_message": check.error_message,
            "metrics": [
                {
                    "name": m.name,
                    "value": m.value,
                    "unit": m.unit,
                    "status": m.status.value,
                    "threshold_warning": m.threshold_warning,
                    "threshold_critical": m.threshold_critical,
                    "timestamp": m.timestamp.isoformat(),
                    "metadata": m.metadata
                }
                for m in check.metrics
            ],
            "metadata": check.metadata
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting health check '{check_name}': {e}")
        raise HTTPException(status_code=500, detail="Failed to get health check")


@router.post("/checks/{check_name}/run", response_model=Dict[str, Any])
async def run_health_check(
    check_name: str,
    background_tasks: BackgroundTasks,
    monitor: Any = Depends(get_health_monitor_dependency)
):
    """Run a health check immediately."""
    try:
        if check_name not in monitor._checks:
            raise HTTPException(status_code=404, detail=f"Health check '{check_name}' not found")

        check = await monitor.run_check(check_name)

        response = {
            "message": f"Health check '{check_name}' completed",
            "status": check.status.value,
            "timestamp": check.last_check.isoformat() if check.last_check else None,
            "metrics": [
                {
                    "name": m.name,
                    "value": m.value,
                    "unit": m.unit,
                    "status": m.status.value
                }
                for m in check.metrics
            ]
        }

        if check.error_message:
            response["error"] = check.error_message

        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error running health check '{check_name}': {e}")
        raise HTTPException(status_code=500, detail="Failed to run health check")


@router.put("/checks/{check_name}/enable", response_model=Dict[str, str])
async def enable_health_check(
    check_name: str,
    monitor: Any = Depends(get_health_monitor_dependency)
):
    """Enable a health check."""
    try:
        if check_name not in monitor._checks:
            raise HTTPException(status_code=404, detail=f"Health check '{check_name}' not found")

        await monitor.enable_check(check_name)

        return {"message": f"Health check '{check_name}' enabled"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error enabling health check '{check_name}': {e}")
        raise HTTPException(status_code=500, detail="Failed to enable health check")


@router.put("/checks/{check_name}/disable", response_model=Dict[str, str])
async def disable_health_check(
    check_name: str,
    monitor: Any = Depends(get_health_monitor_dependency)
):
    """Disable a health check."""
    try:
        if check_name not in monitor._checks:
            raise HTTPException(status_code=404, detail=f"Health check '{check_name}' not found")

        await monitor.disable_check(check_name)

        return {"message": f"Health check '{check_name}' disabled"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error disabling health check '{check_name}': {e}")
        raise HTTPException(status_code=500, detail="Failed to disable health check")


@router.get("/metrics", response_model=Dict[str, Any])
async def get_metrics(
    monitor: Any = Depends(get_health_monitor_dependency),
    metric_name: Optional[str] = Query(None, description="Specific metric name"),
    hours: int = Query(24, ge=1, le=168, description="Hours of history to fetch")
):
    """Get system metrics and their history."""
    try:
        response = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "system_metrics": {},
            "service_metrics": {},
            "history": {}
        }

        # Get current metrics
        report = await monitor.generate_health_report()

        for name, metric in report.system_metrics.items():
            if metric_name and metric_name not in name:
                continue
            response["system_metrics"][name] = {
                "value": metric.value,
                "unit": metric.unit,
                "status": metric.status.value,
                "timestamp": metric.timestamp.isoformat()
            }

        for name, metric in report.service_metrics.items():
            if metric_name and metric_name not in name:
                continue
            response["service_metrics"][name] = {
                "value": metric.value,
                "unit": metric.unit,
                "status": metric.status.value,
                "timestamp": metric.timestamp.isoformat()
            }

        # Get historical data
        if metric_name:
            history = await monitor.get_metrics_history(metric_name, limit=100)
            response["history"][metric_name] = [
                {"timestamp": t.isoformat(), "value": v} for t, v in history
            ]
        else:
            # Get history for all metrics
            for metric_key in monitor._metrics_history:
                if hours:
                    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
                    history = [
                        (h["timestamp"], h["value"])
                        for h in monitor._metrics_history[metric_key]
                        if h["timestamp"] > cutoff
                    ]
                else:
                    history = await monitor.get_metrics_history(metric_key, limit=100)

                response["history"][metric_key] = [
                    {"timestamp": t.isoformat(), "value": v} for t, v in history
                ]

        return response
    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get metrics")


@router.get("/alerts", response_model=List[Dict[str, Any]])
async def get_alerts(
    monitor: Any = Depends(get_health_monitor_dependency),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    active_only: bool = Query(True, description="Show only active alerts"),
    acknowledged: Optional[bool] = Query(None, description="Filter by acknowledgment status"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of alerts")
):
    """Get health alerts."""
    try:
        alerts = []

        # Get alerts from active and history
        all_alerts = list(monitor._active_alerts.values())
        if not active_only:
            all_alerts.extend(monitor._alert_history)

        # Sort by timestamp (newest first)
        all_alerts.sort(key=lambda a: a.timestamp, reverse=True)

        for alert in all_alerts[:limit]:
            # Apply filters
            if severity and alert.severity.value != severity:
                continue
            if acknowledged is not None and alert.acknowledged != acknowledged:
                continue
            if active_only and alert.resolved:
                continue

            alert_data = {
                "alert_id": alert.alert_id,
                "check_name": alert.check_name,
                "severity": alert.severity.value,
                "message": alert.message,
                "metric_name": alert.metric_name,
                "metric_value": alert.metric_value,
                "threshold": alert.threshold,
                "timestamp": alert.timestamp.isoformat(),
                "acknowledged": alert.acknowledged,
                "acknowledged_by": alert.acknowledged_by,
                "acknowledged_at": alert.acknowledged_at.isoformat() if alert.acknowledged_at else None,
                "resolved": alert.resolved,
                "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None,
                "active": alert.alert_id in monitor._active_alerts
            }
            alerts.append(alert_data)

        return alerts
    except Exception as e:
        logger.error(f"Error getting alerts: {e}")
        raise HTTPException(status_code=500, detail="Failed to get alerts")


@router.post("/alerts/{alert_id}/acknowledge", response_model=Dict[str, str])
async def acknowledge_alert(
    alert_id: str,
    request: Dict[str, str],
    monitor: Any = Depends(get_health_monitor_dependency)
):
    """Acknowledge a health alert."""
    try:
        acknowledged_by = request.get("acknowledged_by")
        if not acknowledged_by:
            raise HTTPException(status_code=400, detail="acknowledged_by is required")

        success = await monitor.acknowledge_alert(alert_id, acknowledged_by)

        if not success:
            raise HTTPException(status_code=404, detail=f"Alert '{alert_id}' not found")

        return {"message": f"Alert '{alert_id}' acknowledged"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error acknowledging alert '{alert_id}': {e}")
        raise HTTPException(status_code=500, detail="Failed to acknowledge alert")


@router.post("/alerts/{alert_id}/resolve", response_model=Dict[str, str])
async def resolve_alert(
    alert_id: str,
    monitor: Any = Depends(get_health_monitor_dependency)
):
    """Resolve a health alert."""
    try:
        success = await monitor.resolve_alert(alert_id)

        if not success:
            raise HTTPException(status_code=404, detail=f"Alert '{alert_id}' not found")

        return {"message": f"Alert '{alert_id}' resolved"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resolving alert '{alert_id}': {e}")
        raise HTTPException(status_code=500, detail="Failed to resolve alert")


@router.get("/uptime", response_model=Dict[str, Any])
async def get_uptime(
    monitor: Any = Depends(get_health_monitor_dependency),
    check_name: Optional[str] = Query(None, description="Specific check name"),
    hours: int = Query(24, ge=1, le=168, description="Hours to calculate uptime for")
):
    """Get system uptime information."""
    try:
        uptime_data = {
            "system_start_time": monitor._start_time.isoformat(),
            "system_boot_time": monitor._boot_time.isoformat(),
            "uptime_hours": (datetime.now(timezone.utc) - monitor._start_time).total_seconds() / 3600,
            "checks": {}
        }

        # Get uptime for each check or specific check
        checks = [check_name] if check_name else monitor._checks.keys()

        for name in checks:
            if name in monitor._checks:
                uptime = monitor.calculate_uptime(name, hours=hours)
                uptime_data["checks"][name] = {
                    "uptime_percentage": uptime,
                    "status": monitor._checks[name].status.value,
                    "last_check": monitor._checks[name].last_check.isoformat() if monitor._checks[name].last_check else None
                }

        # Calculate overall uptime
        if uptime_data["checks"]:
            overall_uptime = sum(u["uptime_percentage"] for u in uptime_data["checks"].values()) / len(uptime_data["checks"])
            uptime_data["overall_uptime_percentage"] = overall_uptime

        return uptime_data
    except Exception as e:
        logger.error(f"Error getting uptime: {e}")
        raise HTTPException(status_code=500, detail="Failed to get uptime")


@router.get("/summary", response_model=Dict[str, Any])
async def get_health_summary(
    monitor: Any = Depends(get_health_monitor_dependency)
):
    """Get a concise health summary for dashboards."""
    try:
        report = await monitor.generate_health_report()

        # Count checks by status
        status_counts = {}
        for check in monitor._checks.values():
            status = check.status.value
            status_counts[status] = status_counts.get(status, 0) + 1

        # Count alerts by severity
        alert_counts = {}
        for alert in monitor._active_alerts.values():
            severity = alert.severity.value
            alert_counts[severity] = alert_counts.get(severity, 0) + 1

        # Get critical metrics
        critical_metrics = []
        for metric in report.system_metrics.values():
            if metric.status in ["degraded", "unhealthy", "critical"]:
                critical_metrics.append({
                    "name": metric.name,
                    "value": metric.value,
                    "unit": metric.unit,
                    "status": metric.status.value
                })

        return {
            "overall_status": report.overall_status.value,
            "timestamp": report.timestamp.isoformat(),
            "uptime_percentage": report.uptime_percentage,
            "checks": {
                "total": len(monitor._checks),
                "healthy": status_counts.get("healthy", 0),
                "degraded": status_counts.get("degraded", 0),
                "unhealthy": status_counts.get("unhealthy", 0),
                "critical": status_counts.get("critical", 0),
                "unknown": status_counts.get("unknown", 0)
            },
            "alerts": {
                "active": len(monitor._active_alerts),
                "critical": alert_counts.get("critical", 0),
                "error": alert_counts.get("error", 0),
                "warning": alert_counts.get("warning", 0),
                "info": alert_counts.get("info", 0)
            },
            "critical_metrics": critical_metrics[:5]  # Top 5 critical metrics
        }
    except Exception as e:
        logger.error(f"Error getting health summary: {e}")
        raise HTTPException(status_code=500, detail="Failed to get health summary")


# Health check for load balancers (always returns 200 if service is running)
@router.get("/ping", response_model=Dict[str, str])
async def ping():
    """Simple ping endpoint for load balancer health checks."""
    return {"status": "ok", "message": "Service is running"}


# Liveness probe (checks if service is alive)
@router.get("/live", response_model=Dict[str, str])
async def liveness():
    """Kubernetes liveness probe endpoint."""
    return {"status": "alive", "timestamp": datetime.now(timezone.utc).isoformat()}


# Readiness probe (checks if service is ready to accept traffic)
@router.get("/ready", response_model=Dict[str, Any])
async def readiness(
    monitor: Any = Depends(get_health_monitor_dependency)
):
    """Kubernetes readiness probe endpoint."""
    try:
        # Check if essential systems are ready
        essential_checks = ["cpu_usage", "memory_usage", "disk_usage"]
        ready = True
        issues = []

        for check_name in essential_checks:
            if check_name in monitor._checks:
                check = monitor._checks[check_name]
                if check.status in ["unhealthy", "critical"]:
                    ready = False
                    issues.append(f"{check_name}: {check.status.value}")

        if ready:
            return {"status": "ready", "timestamp": datetime.now(timezone.utc).isoformat()}
        else:
            return JSONResponse(
                status_code=503,
                content={
                    "status": "not_ready",
                    "issues": issues,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            )
    except Exception as e:
        logger.error(f"Error checking readiness: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "error": "Health check system unavailable",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )