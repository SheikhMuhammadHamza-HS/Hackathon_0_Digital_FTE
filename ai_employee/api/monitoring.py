"""Monitoring dashboard API endpoints."""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from ..utils.monitoring import (
    monitoring_dashboard,
    AlertSeverity,
    HealthCheck
)
from .auth import get_current_user, User, require_level, SecurityLevel

router = APIRouter(prefix="/api/v1/monitoring", tags=["monitoring"])


class DashboardResponse(BaseModel):
    """Response model for dashboard data."""
    timestamp: str
    health_status: str
    system_metrics: Dict[str, Any]
    active_alerts: int
    recent_alerts: List[Dict[str, Any]]
    derived_metrics: Dict[str, Any]
    monitoring_status: str


class HealthCheckResponse(BaseModel):
    """Response model for health check."""
    name: str
    status: str
    message: str
    response_time_ms: float
    timestamp: str
    details: Dict[str, Any]


class AlertResponse(BaseModel):
    """Response model for alert."""
    id: str
    severity: str
    title: str
    description: str
    metric_name: str
    current_value: Any
    threshold: Any
    timestamp: str
    resolved: bool
    resolved_at: Optional[str]


class MetricResponse(BaseModel):
    """Response model for metric."""
    name: str
    value: float
    timestamp: str
    labels: Dict[str, str]


@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    refresh: bool = Query(False, description="Force refresh of dashboard data")
):
    """Get monitoring dashboard data."""
    try:
        dashboard_data = monitoring_dashboard.get_dashboard_data()
        return DashboardResponse(**dashboard_data)
    except Exception as e:
        raise Exception(f"Failed to get dashboard: {str(e)}")


@router.get("/health", response_model=List[HealthCheckResponse])
async def get_health_status():
    """Get current health status of all components."""
    try:
        health_checks = await monitoring_dashboard.health_monitor.run_health_checks()
        return [
            HealthCheckResponse(
                name=check.name,
                status=check.status,
                message=check.message,
                response_time_ms=check.response_time_ms,
                timestamp=check.timestamp.isoformat(),
                details=check.details
            )
            for check in health_checks.values()
        ]
    except Exception as e:
        raise Exception(f"Failed to get health status: {str(e)}")


@router.get("/health/{check_name}", response_model=HealthCheckResponse)
async def get_specific_health_check(
    check_name: str,
    user: User = Depends(get_current_user)
):
    """Get health status for a specific component."""
    try:
        health_checks = await monitoring_dashboard.health_monitor.run_health_checks()
        check = health_checks.get(check_name)

        if not check:
            raise Exception(f"Health check '{check_name}' not found")

        return HealthCheckResponse(
            name=check.name,
            status=check.status,
            message=check.message,
            response_time_ms=check.response_time_ms,
            timestamp=check.timestamp.isoformat(),
            details=check.details
        )

    except Exception as e:
        if "not found" in str(e):
            raise Exception(f"Health check '{check_name}' not found", 404)
        raise Exception(f"Failed to get health check: {str(e)}")


@router.get("/metrics")
async def get_metrics(
    metric_names: Optional[str] = Query(None),
    hours: int = Query(1, ge=1, le=168)  # Max 7 days
):
    """Get metrics data."""
    try:
        if metric_names:
            metrics = {}
            for name in metric_names.split(","):
                metric_name = name.strip()
                historical = monitoring_dashboard.get_historical_metrics(metric_name, hours)
                metrics[metric_name] = historical
        else:
            # Get all metrics
            metrics = {}
            for name in monitoring_dashboard.metrics_collector.metrics:
                historical = monitoring_dashboard.get_historical_metrics(name, hours)
                if historical:
                    metrics[name] = historical

        return {"metrics": metrics, "period_hours": hours}

    except Exception as e:
        raise Exception(f"Failed to get metrics: {str(e)}")


@router.get("/alerts")
async def get_alerts(
    severity: Optional[str] = Query(None),
    resolved: Optional[bool] = Query(None),
    limit: int = Query(50, ge=1, le=1000)
):
    """Get monitoring alerts."""
    try:
        alerts = monitoring_dashboard.alert_manager.alerts

        # Filter by severity
        if severity:
            try:
                severity_enum = AlertSeverity(severity)
                alerts = [a for a in alerts if a.severity == severity_enum]
            except:
                pass  # Invalid severity, return all

        # Filter by resolved status
        if resolved is not None:
            alerts = [a for a in alerts if a.resolved == resolved]

        # Sort by timestamp (newest first)
        alerts.sort(key=lambda x: x.timestamp, reverse=True)

        # Limit results
        alerts = alerts[:limit]

        return {
            "alerts": [AlertResponse(**alert.to_dict()) for alert in alerts],
            "total": len(alerts),
            "filters": {
                "severity": severity,
                "resolved": resolved
            }
        }

    except Exception as e:
        raise Exception(f"Failed to get alerts: {str(e)}")


@router.post("/alerts/{alert_id}/resolve")
async def resolve_alert(
    alert_id: str,
    user: User = Depends(require_level(SecurityLevel.ADMIN))
):
    """Resolve an alert."""
    try:
        success = monitoring_dashboard.alert_manager.resolve_alert(alert_id)
        if success:
            return {"message": f"Alert {alert_id} resolved successfully"}
        else:
            raise Exception(f"Alert {alert_id} not found")

    except Exception as e:
        raise Exception(f"Failed to resolve alert: {str(e)}")


@router.get("/performance/summary")
async def get_performance_summary(
    hours: int = Query(24, ge=1, le=168)
):
    """Get performance summary."""
    try:
        summary = monitoring_dashboard.get_performance_summary(hours)
        return summary

    except Exception as e:
        raise Exception(f"Failed to get performance summary: {str(e)}")


@router.get("/system")
async def get_system_metrics(
    detailed: bool = Query(False, description="Include detailed system metrics")
):
    """Get system metrics."""
    try:
        system_metrics = await monitoring_dashboard.metrics_collector.collect_system_metrics()

        if detailed:
            return {"system_metrics": system_metrics}
        else:
            # Return summary metrics
            summary = {
                "cpu_percent": system_metrics.get("cpu", {}).get("percent", 0),
                "memory_percent": system_metrics.get("memory", {}).get("percent", 0),
                "disk_usage": {
                    path: {
                        "percent": usage.get("percent", 0)
                    }
                    for path, usage in system_metrics.get("disk", {}).items()
                },
                "load_average": system_metrics.get("load", {}),
                "process_count": system_metrics.get("processes", 0)
            }
            return {"system_summary": summary}

    except Exception as e:
        raise Exception(f"Failed to get system metrics: {str(e)}")


@router.get("/application")
async def get_application_metrics():
    """Get application metrics."""
    try:
        app_metrics = await monitoring_dashboard.metrics_collector.collect_application_metrics()
        return {"application_metrics": app_metrics}

    except Exception as e:
        raise Exception(f"Failed to get application metrics: {str(e)}")


@router.post("/monitoring/start")
async def start_monitoring(
    user: User = Depends(require_level(SecurityLevel.ADMIN))
):
    """Start the monitoring system."""
    try:
        if monitoring_dashboard.running:
            return {"message": "Monitoring is already running"}

        await monitoring_dashboard.start_monitoring()
        return {"message": "Monitoring started successfully"}

    except Exception as e:
        raise Exception(f"Failed to start monitoring: {str(e)}")


@router.post("/monitoring/stop")
async def stop_monitoring(
    user: User = Depends(require_level(SecurityLevel.ADMIN))
):
    """Stop the monitoring system."""
    try:
        if not monitoring_dashboard.running:
            return {"message": "Monitoring is not running"}

        await monitoring_dashboard.stop_monitoring()
        return {"message": "Monitoring stopped successfully"}

    except Exception as e:
        raise Exception(f"Failed to stop monitoring: {str(e)}")


@router.get("/monitoring/status")
async def get_monitoring_status(
    user: User = Depends(require_level(SecurityLevel.USER))
):
    """Get monitoring system status."""
    try:
        return {
            "running": monitoring_dashboard.running,
            "tasks_count": len(monitoring_dashboard.monitoring_tasks),
            "last_run": datetime.now().isoformat(),
            "storage_path": str(monitoring_dashboard.storage_path),
            "health_checks_count": len(monitoring_dashboard.health_monitor.health_checks),
            "alert_rules_count": len(monitoring_dashboard.alert_manager.alert_rules),
            "active_alerts_count": len([a for a in monitoring_dashboard.alert_manager.alerts if not a.resolved])
        }

    except Exception as e:
        raise Exception(f"Failed to get monitoring status: {str(e)}")


@router.get("/statistics")
async def get_monitoring_statistics(
    days: int = Query(7, ge=1, le=30),
    user: User = Depends(require_level(SecurityLevel.USER))
):
    """Get monitoring statistics for analysis."""
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        # Get health check statistics
        health_history = list(monitoring_dashboard.health_monitor.health_history)
        recent_health = [
            h for h in health_history
            if h.timestamp >= start_date
        ]

        if recent_health:
            health_stats = {
                "total_checks": len(recent_health),
                "healthy": len([h for h in recent_health if h.status == "healthy"]),
                "degraded": len([h for h in recent_health if h.status == "degraded"]),
                "unhealthy": len([h for h in recent_health if h.status == "unhealthy"]),
                "uptime_percentage": (len([h for h in recent_health if h.status == "healthy"]) / len(recent_health)) * 100 if recent_health else 0
            }
        else:
            health_stats = {
                "total_checks": 0,
                "healthy": 0,
                "degraded": 0,
                "unhealthy": 0,
                "uptime_percentage": 0
            }

        # Get alert statistics
        alert_history = list(monitoring_dashboard.alert_manager.alert_history)
        recent_alerts = [
            a for a in alert_history
            if a.timestamp >= start_date
        ]

        alert_stats = {
            "total_alerts": len(recent_alerts),
            "by_severity": {
                "info": len([a for a in recent_alerts if a.severity == AlertSeverity.INFO]),
                "warning": len([a for a in recent_alerts if a.severity == AlertSeverity.WARNING]),
                "error": len([a for a in recent_alerts if a.severity == AlertSeverity.ERROR]),
                "critical": len([a for a in recent_alerts if a.severity == AlertSeverity.CRITICAL])
            },
            "resolved": len([a for a in recent_alerts if a.resolved]),
            "active": len([a for a in recent_alerts if not a.resolved])
        }

        # Get metrics statistics
        metrics_stats = {}
        for name in monitoring_dashboard.metrics_collector.metrics:
            recent_metrics = [
                m for m in monitoring_dashboard.metrics_collector.metrics[name]
                if m.timestamp >= start_date
            ]
            if recent_metrics:
                values = [m.value for m in recent_metrics]
                metrics_stats[name] = {
                    "count": len(recent_metrics),
                    "min": min(values),
                    "max": max(values),
                    "avg": sum(values) / len(values),
                    "latest": values[-1] if values else 0
                }

        return {
            "period_days": days,
            "date_range": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "health": health_stats,
            "alerts": alert_stats,
            "metrics": metrics_stats,
            "generated_at": datetime.now().isoformat()
        }

    except Exception as e:
        raise Exception(f"Failed to get monitoring statistics: {str(e)}")


@router.get("/metrics/trends")
async def get_metrics_trends(
    metric_name: str = Query(..., description="Metric name to analyze"),
    hours: int = Query(24, ge=1, le=168),
    user: User = Depends(require_level(SecurityLevel.USER))
):
    """Get metric trends over time."""
    try:
        historical = monitoring_dashboard.get_historical_metrics(metric_name, hours)

        if not historical:
            return {"message": f"No data found for metric '{metric_name}'"}

        # Calculate trends
        values = [m["value"] for m in historical]
        timestamps = [m["timestamp"] for m in historical]

        if len(values) < 2:
            return {
                "metric_name": metric_name,
                "trend": "insufficient_data",
                "data_count": len(values)
            }

        # Calculate trend
        if len(values) >= 2:
            first_half = values[:len(values)//2]
            second_half = values[len(values)//2:]
            first_avg = sum(first_half) / len(first_half)
            second_avg = sum(second_half) / len(second_half)

            if second_avg > first_avg * 1.1:
                trend = "increasing"
            elif second_avg < first_half * 0.9:
                trend = "decreasing"
            else:
                trend = "stable"
        else:
            trend = "stable"

        return {
            "metric_name": metric_name,
            "trend": trend,
            "data_count": len(values),
            "time_range": {
                "start": timestamps[0],
                "end": timestamps[-1]
            },
            "statistics": {
                "min": min(values),
                "max": max(values),
                "avg": sum(values) / len(values),
                "latest": values[-1],
                "first": values[0]
            }
        }

    except Exception as e:
        raise Exception(f"Failed to get metric trends: {str(e)}")


@router.post("/alert-rules")
async def create_alert_rule(
    name: str = Query(..., description="Rule name"),
    metric_name: str = Query(..., description="Metric to monitor"),
    condition: str = Query(..., description="Condition (>, <, ==, !=, >=, <=)"),
    threshold: float = Query(..., description="Threshold value"),
    severity: str = Query(..., description="Alert severity"),
    title: str = Query(..., description="Alert title"),
    description: str = Query(..., description="Alert description"),
    user: User = Depends(require_level(SecurityLevel.ADMIN))
):
    """Create a new alert rule."""
    try:
        severity_enum = AlertSeverity(severity)
        monitoring_dashboard.alert_manager.add_alert_rule(
            name=name,
            metric_name=metric_name,
            condition=condition,
            threshold=threshold,
            severity=severity_enum,
            title=title,
            description=description
        )

        return {
            "message": f"Alert rule '{name}' created successfully",
            "rule": {
                "name": name,
                "metric_name": metric_name,
                "condition": condition,
                "threshold": threshold,
                "severity": severity,
                "title": title,
                "description": description
            }
        }

    except ValueError as e:
        raise Exception(f"Invalid parameter: {str(e)}", 400)
    except Exception as e:
        raise Exception(f"Failed to create alert rule: {str(e)}")


@router.delete("/alert-rules/{rule_name}")
async def delete_alert_rule(
    rule_name: str,
    user: User = Depends(require_level(SecurityLevel.ADMIN))
):
    """Delete an alert rule."""
    try:
        if rule_name in monitoring_dashboard.alert_manager.alert_rules:
            del monitoring_dashboard.alert_manager.alert_rules[rule_name]
            return {"message": f"Alert rule '{rule_name}' deleted successfully"}
        else:
            raise Exception(f"Alert rule '{rule_name}' not found", 404)

    except Exception as e:
        raise Exception(f"Failed to delete alert rule: {str(e)}")


@router.get("/alert-rules")
async def list_alert_rules(
    user: User = Depends(require_level(SecurityLevel.ADMIN))
):
    """List all alert rules."""
    try:
        rules = []
        for name, rule in monitoring_dashboard.alert_manager.alert_rules.items():
            rules.append({
                "name": name,
                "metric_name": rule["metric_name"],
                "condition": rule["condition"],
                "threshold": rule["threshold"],
                "severity": rule["severity"].value,
                "title": rule["title"],
                "description": rule["description"]
            })

        return {"alert_rules": rules, "total": len(rules)}

    except Exception as e:
        raise Exception(f"Failed to list alert rules: {str(e)}")


@router.get("/export/monitoring-data")
async def export_monitoring_data(
    format: str = Query("json", regex="^(json|csv)$"),
    days: int = Query(7, ge=1, le=30),
    user: User = Depends(require_level(SecurityLevel.ADMIN))
):
    """Export monitoring data."""
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        # Collect all data
        export_data = {
            "export_info": {
                "timestamp": end_date.isoformat(),
                "period_days": days,
                "format": format,
                "generated_by": user.id
            },
            "dashboard": monitoring_dashboard.get_dashboard_data(),
            "health_history": [
                check.to_dict() for check in monitoring_dashboard.health_monitor.health_history
                if check.timestamp >= start_date
            ],
            "alerts": [
                alert.to_dict() for alert in monitoring_dashboard.alert_manager.alerts
                if alert.timestamp >= start_date
            ],
            "metrics": {}
        }

        # Add metrics for requested period
        for name in monitoring_dashboard.metrics_collector.metrics:
            historical = monitoring_dashboard.get_historical_metrics(name, days)
            if historical:
                export_data["metrics"][name] = historical

        if format == "json":
            return export_data
        elif format == "csv":
            # For CSV, we'll convert metrics to flat format
            csv_data = []

            # Dashboard data
            dashboard = export_data["dashboard"]
            csv_data.append(["timestamp", "health_status", "active_alerts"])
            csv_data.append([
                dashboard["timestamp"],
                dashboard["health_status"],
                dashboard["active_alerts"]
            ])

            # Metrics data (simplified)
            for metric_name, metric_list in export_data.get("metrics", {}).items():
                for metric in metric_list[-10:]:  # Last 10 values
                    csv_data.append([metric["timestamp"], metric["name"], str(metric["value"])])

            return {"csv_data": csv_data}

    except Exception as e:
        raise Exception(f"Failed to export monitoring data: {str(e)}")


@router.post("/test/metrics")
async def test_metrics(
    test_value: float = Query(42.0, description="Test metric value"),
    metric_name: str = Query("test_metric", description="Test metric name"),
    user: User = Depends(require_level(SecurityLevel.ADMIN))
):
    """Create a test metric for monitoring validation."""
    try:
        monitoring_dashboard.metrics_collector.record_metric(
            name=metric_name,
            value=test_value,
            labels={"test": "true"}
        )

        return {
            "message": f"Test metric '{metric_name}' recorded with value {test_value}",
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        raise Exception(f"Failed to create test metric: {str(e)}")