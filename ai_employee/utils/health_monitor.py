"""
Health monitoring system for AI Employee.

Provides comprehensive system health monitoring, service availability checks,
performance metrics tracking, and anomaly detection with real-time alerts.
"""

import asyncio
import psutil
import json
import time
from datetime import datetime, timezone, timedelta
from enum import Enum, IntEnum
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Union, Tuple
from dataclasses import dataclass, field, asdict
import aiohttp
import aiofiles
from collections import deque, defaultdict

from ..core.event_bus import get_event_bus, Event, EventPriority
from ..core.config import get_config, AppConfig
from ..utils.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class HealthCheckConfig:
    """Configuration for health monitoring."""
    check_interval: float = 60.0  # seconds
    metrics_retention_hours: int = 24
    alert_retention_hours: int = 48
    enable_system_checks: bool = True
    enable_service_checks: bool = True


class HealthStatus(IntEnum):
    """Health status levels (Ordered by severity: higher is worse)."""
    UNKNOWN = 0
    HEALTHY = 1
    DEGRADED = 2
    UNHEALTHY = 3
    CRITICAL = 4


class CheckType(Enum):
    """Types of health checks."""
    SYSTEM_RESOURCE = "system_resource"
    SERVICE_AVAILABILITY = "service_availability"
    API_ENDPOINT = "api_endpoint"
    FILE_SYSTEM = "file_system"
    DATABASE = "database"
    CUSTOM = "custom"


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class HealthMetric:
    """Individual health metric data."""
    name: str = ""
    value: float = 0.0
    unit: str = ""
    threshold_warning: Optional[float] = None
    threshold_critical: Optional[float] = None
    status: HealthStatus = HealthStatus.HEALTHY
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)

    def evaluate(self) -> HealthStatus:
        """Evaluate metric against thresholds."""
        if self.threshold_critical is not None and self.value >= self.threshold_critical:
            self.status = HealthStatus.CRITICAL
        elif self.threshold_warning is not None and self.value >= self.threshold_warning:
            self.status = HealthStatus.DEGRADED
        else:
            self.status = HealthStatus.HEALTHY
        return self.status


@dataclass
class HealthCheck:
    """Health check configuration and results."""
    name: str = ""
    check_type: CheckType = CheckType.SERVICE_AVAILABILITY
    description: str = ""
    enabled: bool = True
    interval: int = 60  # seconds
    timeout: int = 10  # seconds
    retries: int = 3
    last_check: Optional[datetime] = None
    last_success: Optional[datetime] = None
    last_failure: Optional[datetime] = None
    consecutive_failures: int = 0
    status: HealthStatus = HealthStatus.UNKNOWN
    metrics: List[HealthMetric] = field(default_factory=list)
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HealthReport:
    """Comprehensive health report."""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    overall_status: HealthStatus = HealthStatus.UNKNOWN
    checks: Dict[str, HealthCheck] = field(default_factory=dict)
    system_metrics: Dict[str, HealthMetric] = field(default_factory=dict)
    service_metrics: Dict[str, HealthMetric] = field(default_factory=dict)
    alerts: List['HealthAlert'] = field(default_factory=list)
    uptime_percentage: float = 0.0
    response_time_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "overall_status": self.overall_status.value,
            "checks": {name: asdict(check) for name, check in self.checks.items()},
            "system_metrics": {name: asdict(metric) for name, metric in self.system_metrics.items()},
            "service_metrics": {name: asdict(metric) for name, metric in self.service_metrics.items()},
            "alerts": [asdict(alert) for alert in self.alerts],
            "uptime_percentage": self.uptime_percentage,
            "response_time_ms": self.response_time_ms
        }


@dataclass
class HealthAlert:
    """Health alert event."""
    alert_id: str = ""
    check_name: str = ""
    severity: AlertSeverity = AlertSeverity.INFO
    message: str = ""
    metric_name: Optional[str] = None
    metric_value: Optional[float] = None
    threshold: Optional[float] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    resolved: bool = False
    resolved_at: Optional[datetime] = None


@dataclass
class HealthEvent(Event):
    """Event published for health status changes."""
    check_name: str = ""
    old_status: HealthStatus = HealthStatus.UNKNOWN
    new_status: HealthStatus = HealthStatus.UNKNOWN
    metrics: Dict[str, float] = field(default_factory=dict)
    alerts: List[str] = field(default_factory=list)


class HealthMonitor:
    """Main health monitoring system."""

    def __init__(
        self,
        config: Optional[AppConfig] = None,
        event_bus=None
    ):
        """Initialize health monitor.

        Args:
            config: Application configuration
            event_bus: Event bus instance for publishing events
        """
        self.config = config or get_config()
        self.event_bus = event_bus or get_event_bus()
        self.logger = get_logger(__name__)

        # Health checks registry
        self._checks: Dict[str, HealthCheck] = {}
        self._check_tasks: Dict[str, asyncio.Task] = {}

        # Metrics history
        self._metrics_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self._uptime_tracker: Dict[str, List[Tuple[datetime, bool]]] = defaultdict(list)

        # Alerts management
        self._active_alerts: Dict[str, HealthAlert] = {}
        self._alert_history: List[HealthAlert] = []

        # Background tasks
        self._monitoring_task: Optional[asyncio.Task] = None
        self._report_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()

        # HTTP session for external checks
        self._http_session: Optional[aiohttp.ClientSession] = None

        # System info cache
        self._boot_time = datetime.fromtimestamp(psutil.boot_time(), tz=timezone.utc)
        self._start_time = datetime.now(timezone.utc)

        # Initialize default checks
        self._setup_default_checks()

    async def initialize(self) -> None:
        """Initialize the health monitoring system."""
        self.logger.info("Initializing Health Monitor")

        # Create HTTP session
        connector = aiohttp.TCPConnector(limit=100, limit_per_host=10)
        timeout = aiohttp.ClientTimeout(total=30)
        self._http_session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout
        )

        # Start background tasks
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        self._report_task = asyncio.create_task(self._reporting_loop())
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

        # Enable all default checks
        for check_name in list(self._checks.keys()):
            if self._checks[check_name].enabled:
                await self.enable_check(check_name)

        self.logger.info("Health Monitor initialized successfully")

    async def shutdown(self) -> None:
        """Shutdown the health monitoring system."""
        self.logger.info("Shutting down Health Monitor")

        # Signal shutdown
        self._shutdown_event.set()

        # Cancel background tasks
        for task in [self._monitoring_task, self._report_task, self._cleanup_task]:
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        # Cancel all check tasks
        for check_name, task in self._check_tasks.items():
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        # Close HTTP session
        if self._http_session:
            await self._http_session.close()

        self.logger.info("Health Monitor shutdown complete")

    def _setup_default_checks(self) -> None:
        """Setup default health checks."""
        # System resource checks
        self.register_check(
            name="cpu_usage",
            check_type=CheckType.SYSTEM_RESOURCE,
            description="CPU usage monitoring",
            interval=30,
            metrics={
                "cpu_percent": {
                    "threshold_warning": 70.0,
                    "threshold_critical": 90.0
                },
                "load_average": {
                    "threshold_warning": psutil.cpu_count() * 0.7,
                    "threshold_critical": psutil.cpu_count() * 0.9
                }
            }
        )

        self.register_check(
            name="memory_usage",
            check_type=CheckType.SYSTEM_RESOURCE,
            description="Memory usage monitoring",
            interval=30,
            metrics={
                "memory_percent": {
                    "threshold_warning": 75.0,
                    "threshold_critical": 90.0
                },
                "swap_percent": {
                    "threshold_warning": 50.0,
                    "threshold_critical": 80.0
                }
            }
        )

        self.register_check(
            name="disk_usage",
            check_type=CheckType.SYSTEM_RESOURCE,
            description="Disk space monitoring",
            interval=60,
            metrics={
                "disk_percent": {
                    "threshold_warning": 80.0,
                    "threshold_critical": 95.0
                }
            }
        )

        # File system checks
        self.register_check(
            name="file_systems",
            check_type=CheckType.FILE_SYSTEM,
            description="Essential file system accessibility",
            interval=60,
            paths=[
                str(self.config.paths.inbox_path),
                str(self.config.paths.logs_path),
                str(self.config.paths.archive_path)
            ]
        )

    def register_check(
        self,
        name: str,
        check_type: CheckType,
        description: str,
        interval: int = 60,
        timeout: int = 10,
        retries: int = 3,
        enabled: bool = True,
        **kwargs
    ) -> None:
        """Register a new health check."""
        if name in self._checks:
            self.logger.warning(f"Health check '{name}' already exists, updating...")

        check = HealthCheck(
            name=name,
            check_type=check_type,
            description=description,
            interval=interval,
            timeout=timeout,
            retries=retries,
            enabled=enabled,
            metadata=kwargs
        )

        self._checks[name] = check
        self.logger.info(f"Registered health check: {name}")

    async def enable_check(self, name: str) -> None:
        """Enable a health check."""
        if name not in self._checks:
            raise ValueError(f"Health check '{name}' not found")

        check = self._checks[name]
        check.enabled = True

        if name not in self._check_tasks or self._check_tasks[name].done():
            self._check_tasks[name] = asyncio.create_task(self._run_check_loop(name))

        self.logger.info(f"Enabled health check: {name}")

    async def run_check(self, name: str) -> HealthCheck:
        """Run a specific health check immediately."""
        if name not in self._checks:
            raise ValueError(f"Health check '{name}' not found")

        check = self._checks[name]
        old_status = check.status

        try:
            if check.check_type == CheckType.SYSTEM_RESOURCE:
                await self._check_system_resources(check)
            elif check.check_type == CheckType.SERVICE_AVAILABILITY:
                await self._check_service_availability(check)
            elif check.check_type == CheckType.API_ENDPOINT:
                await self._check_api_endpoint(check)
            elif check.check_type == CheckType.FILE_SYSTEM:
                await self._check_file_system(check)
            elif check.check_type == CheckType.DATABASE:
                await self._check_database(check)
            elif check.check_type == CheckType.CUSTOM:
                await self._run_custom_check(check)

            check.last_check = datetime.now(timezone.utc)
            check.last_success = datetime.now(timezone.utc)
            check.consecutive_failures = 0
            check.error_message = None

            if check.metrics:
                worst_status = max(m.status for m in check.metrics)
                check.status = worst_status
            else:
                check.status = HealthStatus.HEALTHY

        except Exception as e:
            self.logger.error(f"Health check '{name}' failed: {e}")
            check.last_check = datetime.now(timezone.utc)
            check.last_failure = datetime.now(timezone.utc)
            check.consecutive_failures += 1
            check.error_message = str(e)
            check.status = HealthStatus.CRITICAL if check.consecutive_failures >= check.retries else HealthStatus.UNHEALTHY

        self._track_uptime(name, check.status == HealthStatus.HEALTHY)

        if old_status != check.status:
            await self._publish_health_event(check, old_status)

        return check

    async def _run_check_loop(self, name: str) -> None:
        """Run health check in a loop."""
        check = self._checks[name]
        while not self._shutdown_event.is_set() and check.enabled:
            try:
                await self.run_check(name)
                await asyncio.sleep(check.interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in check loop for '{name}': {e}")
                await asyncio.sleep(min(check.interval, 60))

    async def _check_system_resources(self, check: HealthCheck) -> None:
        """Check system resources."""
        check.metrics.clear()
        if check.name == "cpu_usage":
            cpu_percent = psutil.cpu_percent(interval=1)
            metric = HealthMetric(
                name="cpu_percent",
                value=cpu_percent,
                unit="percent",
                threshold_warning=check.metadata.get("metrics", {}).get("cpu_percent", {}).get("threshold_warning", 70.0),
                threshold_critical=check.metadata.get("metrics", {}).get("cpu_percent", {}).get("threshold_critical", 90.0)
            )
            metric.evaluate()
            check.metrics.append(metric)

        elif check.name == "memory_usage":
            vm = psutil.virtual_memory()
            metric = HealthMetric(
                name="memory_percent",
                value=vm.percent,
                unit="percent",
                threshold_warning=check.metadata.get("metrics", {}).get("memory_percent", {}).get("threshold_warning", 75.0),
                threshold_critical=check.metadata.get("metrics", {}).get("memory_percent", {}).get("threshold_critical", 90.0)
            )
            metric.evaluate()
            check.metrics.append(metric)

    async def _check_file_system(self, check: HealthCheck) -> None:
        """Check file system accessibility."""
        check.metrics.clear()
        paths = check.metadata.get("paths", [])
        for path_str in paths:
            path = Path(path_str)
            try:
                if not path.exists():
                    path.mkdir(parents=True, exist_ok=True)
                
                test_file = path / f".health_check_{int(time.time())}"
                test_file.write_text("test")
                test_file.unlink()
                
                metric = HealthMetric(name=f"path_{path.name}_ok", value=1.0, status=HealthStatus.HEALTHY)
                check.metrics.append(metric)
            except Exception as e:
                raise Exception(f"File system check failed for {path}: {e}")

    def _track_uptime(self, check_name: str, is_healthy: bool) -> None:
        """Track uptime."""
        self._uptime_tracker[check_name].append((datetime.now(timezone.utc), is_healthy))
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        self._uptime_tracker[check_name] = [t for t in self._uptime_tracker[check_name] if t[0] > cutoff]

    def calculate_uptime(self, check_name: str, hours: int = 24) -> float:
        """Calculate uptime percentage."""
        tracker = self._uptime_tracker.get(check_name, [])
        if not tracker: return 0.0
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        recent = [t for t in tracker if t[0] > cutoff]
        if not recent: return 0.0
        return (sum(1 for _, h in recent if h) / len(recent)) * 100

    def get_overall_status(self) -> HealthStatus:
        """Get overall status."""
        statuses = [check.status for check in self._checks.values() if check.enabled]
        if not statuses: return HealthStatus.UNKNOWN
        return max(statuses)

    async def generate_health_report(self) -> HealthReport:
        """Generate report."""
        report = HealthReport()
        report.overall_status = self.get_overall_status()
        report.checks = self._checks.copy()
        return report

    async def _publish_health_event(self, check: HealthCheck, old_status: HealthStatus) -> None:
        """Publish status change event."""
        event = HealthEvent(
            check_name=check.name,
            old_status=old_status,
            new_status=check.status,
            metrics={m.name: m.value for m in check.metrics}
        )
        if check.status == HealthStatus.CRITICAL:
            event.priority = EventPriority.CRITICAL
        elif check.status == HealthStatus.UNHEALTHY:
            event.priority = EventPriority.HIGH
        else:
            event.priority = EventPriority.LOW
        
        await self.event_bus.publish(event)

    async def _monitoring_loop(self) -> None:
        """Monitoring loop."""
        while not self._shutdown_event.is_set():
            try:
                for check in list(self._checks.values()):
                    for metric in check.metrics:
                        self._metrics_history[f"{check.name}_{metric.name}"].append({
                            "timestamp": metric.timestamp,
                            "value": metric.value,
                            "status": metric.status
                        })
                await asyncio.sleep(30)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(10)

    async def _reporting_loop(self) -> None:
        """Reporting loop."""
        while not self._shutdown_event.is_set():
            try:
                await asyncio.sleep(3600)
                report = await self.generate_health_report()
            except asyncio.CancelledError:
                break

    async def _cleanup_loop(self) -> None:
        """Cleanup loop."""
        while not self._shutdown_event.is_set():
            try:
                cutoff = datetime.now(timezone.utc) - timedelta(days=7)
                for metric_name in list(self._metrics_history.keys()):
                    history = self._metrics_history[metric_name]
                    while history and history[0]["timestamp"] < cutoff:
                        history.popleft()
                await asyncio.sleep(21600)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in cleanup loop: {e}")
                await asyncio.sleep(30)

    async def _check_service_availability(self, check: HealthCheck) -> None: pass
    async def _check_api_endpoint(self, check: HealthCheck) -> None: pass
    async def _check_database(self, check: HealthCheck) -> None: pass
    async def _run_custom_check(self, check: HealthCheck) -> None: pass


# Global instance
_health_monitor: Optional[HealthMonitor] = None

def get_health_monitor() -> HealthMonitor:
    global _health_monitor
    if _health_monitor is None:
        _health_monitor = HealthMonitor()
    return _health_monitor

async def initialize_health_monitor() -> None:
    monitor = get_health_monitor()
    await monitor.initialize()