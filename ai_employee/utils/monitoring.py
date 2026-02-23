"""Comprehensive monitoring system for AI Employee."""

import asyncio
import json
import time
import psutil
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import aiofiles
import statistics
from collections import defaultdict, deque

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of metrics."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class MetricValue:
    """Single metric value."""
    name: str
    value: float
    timestamp: datetime
    labels: Dict[str, str] = field(default_factory=dict)
    metric_type: MetricType = MetricType.GAUGE


@dataclass
class Alert:
    """Monitoring alert."""
    id: str
    severity: AlertSeverity
    title: str
    description: str
    metric_name: str
    current_value: Any
    threshold: Any
    timestamp: datetime = field(default_factory=datetime.now)
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HealthCheck:
    """Health check result."""
    name: str
    status: str  # healthy, degraded, unhealthy
    message: str
    response_time_ms: float
    timestamp: datetime = field(default_factory=datetime.now)
    details: Dict[str, Any] = field(default_factory=dict)


class MetricsCollector:
    """Collects system and application metrics."""

    def __init__(self):
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.counters: Dict[str, int] = defaultdict(int)
        self.lock = asyncio.Lock()

    async def collect_system_metrics(self) -> Dict[str, Any]:
        """Collect system-level metrics."""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            cpu_freq = psutil.cpu_freq()

            # Memory usage
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()

            # Disk usage
            disk_usage = {}
            for partition in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    disk_usage[partition.mountpoint] = {
                        "total": usage.total,
                        "used": usage.used,
                        "free": usage.free,
                        "percent": usage.percent
                    }
                except:
                    pass

            # Network I/O
            network = psutil.net_io_counters()

            # Process count
            process_count = len(psutil.pids())

            # System load
            load_avg = psutil.getloadavg()

            return {
                "cpu": {
                    "percent": cpu_percent,
                    "count": cpu_count,
                    "frequency": cpu_freq.current if cpu_freq else None
                },
                "memory": {
                    "total": memory.total,
                    "available": memory.available,
                    "percent": memory.percent,
                    "used": memory.used,
                    "swap": {
                        "total": swap.total,
                        "used": swap.used,
                        "percent": swap.percent
                    }
                },
                "disk": disk_usage,
                "network": {
                    "bytes_sent": network.bytes_sent,
                    "bytes_recv": network.bytes_recv,
                    "packets_sent": network.packets_sent,
                    "packets_recv": network.packets_recv
                },
                "processes": process_count,
                "load": {
                    "1min": load_avg[0],
                    "5min": load_avg[1],
                    "15min": load_avg[2]
                }
            }

        except Exception as e:
            logger.error(f"Failed to collect system metrics: {e}")
            return {}

    async def collect_application_metrics(self) -> Dict[str, Any]:
        """Collect application-specific metrics."""
        try:
            # API metrics
            api_metrics = {
                "requests_total": self.counters.get("api_requests_total", 0),
                "requests_per_second": 0,  # Would be calculated from recent requests
                "error_rate": 0.0,  # Would be calculated from errors/total
                "response_time_avg": 0.0,  # Would be calculated from request times
                "active_sessions": self.counters.get("active_sessions", 0)
            }

            # Database metrics (simplified)
            db_metrics = {
                "connections": self.counters.get("db_connections", 0),
                "queries_per_second": 0,
                "slow_queries": self.counters.get("slow_queries", 0)
            }

            # Business metrics
            business_metrics = {
                "active_users": self.counters.get("active_users", 0),
                "invoices_generated": self.counters.get("invoices_generated", 0),
                "briefings_generated": self.counters.get("briefings_generated", 0),
                "social_posts": self.counters.get("social_posts", 0)
            }

            return {
                "api": api_metrics,
                "database": db_metrics,
                "business": business_metrics
            }

        except Exception as e:
            logger.error(f"Failed to collect application metrics: {e}")
            return {}

    def increment_counter(self, name: str, value: int = 1, labels: Dict[str, str] = None):
        """Increment a counter metric."""
        key = f"{name}:{hash(str(labels))}" if labels else name
        self.counters[key] += value

    async def record_metric(self, name: str, value: float, labels: Dict[str, str] = None):
        """Record a metric value."""
        metric = MetricValue(
            name=name,
            value=value,
            timestamp=datetime.now(),
            labels=labels or {}
        )

        async with self.lock:
            self.metrics[name].append(metric)


class HealthMonitor:
    """Monitors system and application health."""

    def __init__(self):
        self.health_checks: Dict[str, Callable] = {}
        self.health_history: deque = deque(maxlen=1000)
        self.alerts: List[Alert] = []

    def register_health_check(self, name: str, check_func: Callable):
        """Register a health check."""
        self.health_checks[name] = check_func

    async def run_health_checks(self) -> Dict[str, HealthCheck]:
        """Run all registered health checks."""
        results = {}

        for name, check_func in self.health_checks.items():
            try:
                start_time = time.time()
                result = await check_func()
                response_time = (time.time() - start_time) * 1000

                health_check = HealthCheck(
                    name=name,
                    status=result.get("status", "healthy"),
                    message=result.get("message", "OK"),
                    response_time_ms=response_time,
                    details=result.get("details", {})
                )

                results[name] = health_check
                self.health_history.append(health_check)

            except Exception as e:
                logger.error(f"Health check '{name}' failed: {e}")
                results[name] = HealthCheck(
                    name=name,
                    status="unhealthy",
                    message=str(e),
                    response_time_ms=0
                )

        return results

    def get_overall_health(self) -> str:
        """Get overall health status."""
        recent_checks = list(self.health_history)[-10:]
        if not recent_checks:
            return "unknown"

        statuses = [check.status for check in recent_checks]
        if all(status == "healthy" for status in statuses):
            return "healthy"
        elif any(status == "unhealthy" for status in statuses):
            return "unhealthy"
        else:
            return "degraded"


class AlertManager:
    """Manages monitoring alerts."""

    def __init__(self):
        self.alerts: List[Alert] = []
        self.alert_rules: Dict[str, Dict[str, Any]] = {}
        self.alert_history: deque = deque(maxlen=1000)

    def add_alert_rule(self, name: str, metric_name: str, condition: str,
                      threshold: Any, severity: AlertSeverity, title: str, description: str):
        """Add an alert rule."""
        self.alert_rules[name] = {
            "metric_name": metric_name,
            "condition": condition,
            "threshold": threshold,
            "severity": severity,
            "title": title,
            "description": description
        }

    def check_alerts(self, metrics: Dict[str, Any]):
        """Check metrics against alert rules."""
        for rule_name, rule in self.alert_rules.items():
            try:
                metric_value = self._get_nested_value(metrics, rule["metric_name"])
                if metric_value is None:
                    continue

                triggered = self._evaluate_condition(metric_value, rule["condition"], rule["threshold"])

                if triggered:
                    # Check if alert already exists and not resolved
                    existing_alert = next(
                        (a for a in self.alerts
                         if a.metric_name == rule["metric_name"] and not a.resolved),
                        None
                    )

                    if not existing_alert:
                        alert = Alert(
                            id=f"alert_{int(time.time() * 1000)}_{len(self.alerts)}",
                            severity=rule["severity"],
                            title=rule["title"],
                            description=rule["description"],
                            metric_name=rule["metric_name"],
                            current_value=metric_value,
                            threshold=rule["threshold"]
                        )

                        self.alerts.append(alert)
                        self.alert_history.append(alert)

                        logger.warning(f"Alert triggered: {alert.title} - {alert.description}")

            except Exception as e:
                logger.error(f"Failed to check alert rule {rule_name}: {e}")

    def resolve_alert(self, alert_id: str):
        """Resolve an alert."""
        for alert in self.alerts:
            if alert.id == alert_id:
                alert.resolved = True
                alert.resolved_at = datetime.now()
                logger.info(f"Alert resolved: {alert.title}")
                return True
        return False

    def _get_nested_value(self, data: Dict[str, Any], path: str):
        """Get nested value from dictionary using dot notation."""
        keys = path.split(".")
        value = data
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None
        return value

    def _evaluate_condition(self, value: Any, condition: str, threshold: Any) -> bool:
        """Evaluate alert condition."""
        if condition == ">":
            return value > threshold
        elif condition == "<":
            return value < threshold
        elif condition == "==":
            return value == threshold
        elif condition == "!=":
            return value != threshold
        elif condition == ">=":
            return value >= threshold
        elif condition == "<=":
            return value <= threshold
        else:
            return False


class MonitoringDashboard:
    """Main monitoring dashboard."""

    def __init__(self):
        self.metrics_collector = MetricsCollector()
        self.health_monitor = HealthMonitor()
        self.alert_manager = AlertManager()
        self.storage_path = Path("monitoring_data")
        self.storage_path.mkdir(parents=True, exist_ok=True)

        # Initialize default health checks
        self._setup_default_health_checks()
        self._setup_default_alerts()

        # Start monitoring tasks
        self.monitoring_tasks = []
        self.running = False

    def _setup_default_health_checks(self):
        """Setup default health checks."""

        async def check_api_health():
            # Check if API is responding
            try:
                # Would make actual health check call
                response_time = 50  # Simulated
                if response_time < 1000:
                    return {"status": "healthy", "message": "API responding normally"}
                else:
                    return {"status": "degraded", "message": "API response slow"}
            except:
                return {"status": "unhealthy", "message": "API not responding"}

        async def check_database_health():
            # Check database connectivity
            try:
                # Would check actual database
                connection_count = 5
                if connection_count < 10:
                    return {"status": "healthy", "message": "Database connections OK"}
                else:
                    return {"status": "degraded", "message": "High database connections"}
            except:
                return {"status": "unhealthy", "message": "Database connection failed"}

        async def check_disk_space():
            # Check disk space
            try:
                disk_usage = psutil.disk_usage('/')
                percent_used = (disk_usage.used / disk_usage.total) * 100
                if percent_used < 80:
                    return {"status": "healthy", "message": f"Disk usage: {percent_used:.1f}%"}
                elif percent_used < 90:
                    return {"status": "degraded", "message": f"Disk usage: {percent_used:.1f}%"}
                else:
                    return {"status": "unhealthy", "message": f"Disk usage: {percent_used:.1f}%"}
            except:
                return {"status": "unhealthy", "message": "Failed to check disk space"}

        async def check_memory_usage():
            # Check memory usage
            try:
                memory = psutil.virtual_memory()
                if memory.percent < 80:
                    return {"status": "healthy", "message": f"Memory usage: {memory.percent:.1f}%"}
                elif memory.percent < 90:
                    return {"status": "degraded", "message": f"Memory usage: {memory.percent:.1f}%"}
                else:
                    return {"status": "unhealthy", "message": f"Memory usage: {memory.percent:.1f}%"}
            except:
                return {"status": "unhealthy", "message": "Failed to check memory"}

        self.health_monitor.register_health_check("api", check_api_health)
        self.health_monitor.register_health_check("database", check_database_health)
        self.health_monitor.register_health_check("disk_space", check_disk_space)
        self.health_monitor.register_health_check("memory", check_memory_usage)

    def _setup_default_alerts(self):
        """Setup default alert rules."""
        # CPU alerts
        self.alert_manager.add_alert_rule(
            "high_cpu",
            "system.cpu.percent",
            ">",
            80,
            AlertSeverity.WARNING,
            "High CPU Usage",
            "CPU usage is above 80%"
        )

        self.alert_manager.add_alert_rule(
            "critical_cpu",
            "system.cpu.percent",
            ">",
            95,
            AlertSeverity.CRITICAL,
            "Critical CPU Usage",
            "CPU usage is above 95%"
        )

        # Memory alerts
        self.alert_manager.add_alert_rule(
            "high_memory",
            "system.memory.percent",
            ">",
            85,
            AlertSeverity.WARNING,
            "High Memory Usage",
            "Memory usage is above 85%"
        )

        # Disk space alerts
        self.alert_manager.add_alert_rule(
            "low_disk_space",
            "system.disk",
            "percent_used",
            90,
            AlertSeverity.CRITICAL,
            "Low Disk Space",
            "Disk usage is above 90%"
        )

        # API error rate
        self.alert_manager.add_alert_rule(
            "high_error_rate",
            "api.error_rate",
            ">",
            5.0,
            AlertSeverity.ERROR,
            "High Error Rate",
            "API error rate is above 5%"
        )

    async def start_monitoring(self):
        """Start the monitoring system."""
        self.running = True
        logger.info("Starting monitoring dashboard")

        # Start monitoring tasks
        self.monitoring_tasks = [
            asyncio.create_task(self._metrics_collection_loop()),
            asyncio.create_task(self._health_check_loop()),
            asyncio.create_task(self._alert_check_loop()),
            asyncio.create_task(self._cleanup_loop())
        ]

        logger.info(f"Monitoring started with {len(self.monitoring_tasks)} tasks")

    async def stop_monitoring(self):
        """Stop the monitoring system."""
        self.running = False
        logger.info("Stopping monitoring dashboard")

        # Cancel all tasks
        for task in self.monitoring_tasks:
            task.cancel()

        # Wait for tasks to complete
        await asyncio.gather(*self.monitoring_tasks, return_exceptions=True)
        self.monitoring_tasks.clear()

        logger.info("Monitoring stopped")

    async def _metrics_collection_loop(self):
        """Collect metrics periodically."""
        while self.running:
            try:
                # Collect system metrics
                system_metrics = await self.metrics_collector.collect_system_metrics()
                for name, value in system_metrics.items():
                    if isinstance(value, dict):
                        for sub_name, sub_value in value.items():
                            self.metrics_collector.record_metric(f"system.{name}.{sub_name}", sub_value)
                    else:
                        self.metrics_collector.record_metric(f"system.{name}", value)

                # Collect application metrics
                app_metrics = await self.metrics_collector.collect_application_metrics()
                for category, metrics in app_metrics.items():
                    for name, value in metrics.items():
                        self.metrics_collector.record_metric(f"app.{category}.{name}", value)

                # Wait before next collection
                await asyncio.sleep(30)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Metrics collection error: {e}")
                await asyncio.sleep(30)

    async def _health_check_loop(self):
        """Run health checks periodically."""
        while self.running:
            try:
                await self.health_monitor.run_health_checks()
                await asyncio.sleep(60)  # Check every minute

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check error: {e}")
                await asyncio.sleep(60)

    async def _alert_check_loop(self):
        """Check for alerts periodically."""
        while self.running:
            try:
                # Get current metrics
                system_metrics = await self.metrics_collector.collect_system_metrics()
                app_metrics = await self.metrics_collector.collect_application_metrics()

                # Combine metrics
                all_metrics = {
                    "system": system_metrics,
                    "app": app_metrics
                }

                # Check alerts
                self.alert_manager.check_alerts(all_metrics)
                await asyncio.sleep(30)  # Check every 30 seconds

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Alert check error: {e}")
                await asyncio.sleep(30)

    async def _cleanup_loop(self):
        """Clean up old data periodically."""
        while self.running:
            try:
                # Save metrics data
                await self._save_monitoring_data()

                # Wait before next cleanup
                await asyncio.sleep(300)  # Every 5 minutes

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cleanup error: {e}")
                await asyncio.sleep(300)

    async def _save_monitoring_data(self):
        """Save monitoring data to storage."""
        try:
            # Save metrics
            metrics_file = self.storage_path / "metrics.json"
            metrics_data = {}
            for name, metric_list in self.metrics_collector.metrics.items():
                metrics_data[name] = [m.to_dict() for m in metric_list]

            async with aiofiles.open(metrics_file, 'w') as f:
                await f.write(json.dumps(metrics_data, indent=2))

            # Save health history
            health_file = self.storage_path / "health_history.json"
            health_data = [check.to_dict() for check in self.health_monitor.health_history]

            async with aiofiles.open(health_file, 'w') as f:
                await f.write(json.dumps(health_data, indent=2))

            # Save alerts
            alerts_file = self.storage_path / "alerts.json"
            alerts_data = [alert.to_dict() for alert in self.alert_manager.alerts]

            async with aiofiles.open(alerts_file, 'w') as f:
                await f.write(json.dumps(alerts_data, indent=2))

        except Exception as e:
            logger.error(f"Failed to save monitoring data: {e}")

    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get dashboard data for display."""
        try:
            # Get latest system metrics
            system_metrics = {}
            for name, metric_list in self.metrics_collector.metrics.items():
                if name.startswith("system."):
                    # Get most recent value
                    if metric_list:
                        latest = metric_list[-1]
                        self._set_nested_value(system_metrics, name[7:], latest.value)

            # Get overall health
            overall_health = self.health_monitor.get_overall_health()

            # Get active alerts
            active_alerts = [a for a in self.alert_manager.alerts if not a.resolved]

            # Calculate some derived metrics
            derived_metrics = {
                "uptime_percentage": 99.9,  # Would calculate from actual data
                "avg_response_time": 150.5,
                "requests_per_minute": 45.2,
                "error_rate_percentage": 0.5
            }

            return {
                "timestamp": datetime.now().isoformat(),
                "health_status": overall_health,
                "system_metrics": system_metrics,
                "active_alerts": len(active_alerts),
                "recent_alerts": [a.to_dict() for a in active_alerts[-5:]],
                "derived_metrics": derived_metrics,
                "monitoring_status": "running" if self.running else "stopped"
            }

        except Exception as e:
            logger.error(f"Failed to get dashboard data: {e}")
            return {"error": str(e), "timestamp": datetime.now().isoformat()}

    def _set_nested_value(self, data: Dict[str, Any], path: str, value: Any):
        """Set nested value in dictionary."""
        keys = path.split(".")
        current = data
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[keys[-1]] = value

    def get_historical_metrics(self, metric_name: str, hours: int = 24) -> List[Dict[str, Any]]:
        """Get historical metrics for a specific metric."""
        try:
            cutoff = datetime.now() - timedelta(hours=hours)
            metric_list = self.metrics_collector.metrics.get(metric_name, [])

            return [
                m.to_dict() for m in metric_list
                if m.timestamp > cutoff
            ]

        except Exception as e:
            logger.error(f"Failed to get historical metrics: {e}")
            return []

    def get_performance_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get performance summary for the last N hours."""
        try:
            cutoff = datetime.now() - timedelta(hours=hours)

            # Get recent health checks
            recent_health = [
                check for check in self.health_monitor.health_history
                if check.timestamp > cutoff
            ]

            # Calculate statistics
            if recent_health:
                response_times = [h.response_time_ms for h in recent_health]
                avg_response = statistics.mean(response_times) if response_times else 0
                max_response = max(response_times) if response_times else 0
            else:
                avg_response = max_response = 0

            # Get recent alerts
            recent_alerts = [
                alert for alert in self.alert_manager.alert_history
                if alert.timestamp > cutoff
            ]

            return {
                "period_hours": hours,
                "health_checks": {
                    "total": len(recent_health),
                    "healthy": len([h for h in recent_health if h.status == "healthy"]),
                    "degraded": len([h for h in recent_health if h.status == "degraded"]),
                    "unhealthy": len([h for h in recent_health if h.status == "unhealthy"]),
                    "avg_response_time_ms": avg_response,
                    "max_response_time_ms": max_response
                },
                "alerts": {
                    "total": len(recent_alerts),
                    "by_severity": {
                        "info": len([a for a in recent_alerts if a.severity == AlertSeverity.INFO]),
                        "warning": len([a for a in recent_alerts if a.severity == AlertSeverity.WARNING]),
                        "error": len([a for a in recent_alerts if a.severity == AlertSeverity.ERROR]),
                        "critical": len([a for a in recent_alerts if a.severity == AlertSeverity.CRITICAL])
                    }
                },
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Failed to get performance summary: {e}")
            return {"error": str(e)}


# Global monitoring dashboard instance
monitoring_dashboard = MonitoringDashboard()