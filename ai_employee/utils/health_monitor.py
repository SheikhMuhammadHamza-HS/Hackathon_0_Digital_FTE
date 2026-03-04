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
from enum import Enum
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


class HealthStatus(Enum):
    """Health status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


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
    name: str = field(default_factory="")
    value: float = field(default_factory=0.0)
    unit: str = field(default_factory="")
    threshold_warning: Optional[float] = field(default_factory=lambda: None)
    threshold_critical: Optional[float] = field(default_factory=lambda: None)
    status: HealthStatus = HealthStatus.HEALTHY
    timestamp: datetime = field(default_factory=datetime.utcnow)
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
    timestamp: datetime = field(default_factory=datetime.utcnow)
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
    alert_id: str = field(default_factory="")
    check_name: str = field(default_factory="")
    severity: AlertSeverity = field(default_factory=AlertSeverity.INFO)
    message: str = field(default_factory="")
    metric_name: Optional[str] = field(default_factory=lambda: None)
    metric_value: Optional[float] = field(default_factory=lambda: None)
    threshold: Optional[float] = field(default_factory=lambda: None)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    acknowledged: bool = field(default_factory=False)
    acknowledged_by: Optional[str] = field(default_factory=lambda: None)
    acknowledged_at: Optional[datetime] = field(default_factory=lambda: None)
    resolved: bool = field(default_factory=bool)
    resolved_at: Optional[datetime] = field(default_factory=lambda: None)


@dataclass
class HealthEvent(Event):
    """Event published for health status changes."""
    check_name: str = field(default_factory=str)
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
        self._boot_time = datetime.fromtimestamp(psutil.boot_time())
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
        for check_name in self._checks:
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

        # Service availability checks
        if hasattr(self.config, 'services'):
            for service_name, service_config in getattr(self.config, 'services', {}).items():
                self.register_check(
                    name=f"service_{service_name}",
                    check_type=CheckType.SERVICE_AVAILABILITY,
                    description=f"Service availability: {service_name}",
                    interval=30,
                    service_config=service_config
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
        """Register a new health check.

        Args:
            name: Unique check name
            check_type: Type of health check
            description: Check description
            interval: Check interval in seconds
            timeout: Check timeout in seconds
            retries: Number of retries on failure
            enabled: Whether check is enabled
            **kwargs: Additional check-specific parameters
        """
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

        # Start check task if not running
        if name not in self._check_tasks or self._check_tasks[name].done():
            self._check_tasks[name] = asyncio.create_task(self._run_check_loop(name))

        self.logger.info(f"Enabled health check: {name}")

    async def disable_check(self, name: str) -> None:
        """Disable a health check."""
        if name not in self._checks:
            raise ValueError(f"Health check '{name}' not found")

        self._checks[name].enabled = False

        # Cancel check task
        if name in self._check_tasks and not self._check_tasks[name].done():
            self._check_tasks[name].cancel()
            try:
                await self._check_tasks[name]
            except asyncio.CancelledError:
                pass

        self.logger.info(f"Disabled health check: {name}")

    async def run_check(self, name: str) -> HealthCheck:
        """Run a specific health check immediately.

        Args:
            name: Check name to run

        Returns:
            Updated health check with results
        """
        if name not in self._checks:
            raise ValueError(f"Health check '{name}' not found")

        check = self._checks[name]
        old_status = check.status

        try:
            # Run the check based on type
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

            # Update timestamps
            check.last_check = datetime.now(timezone.utc)
            check.last_success = datetime.now(timezone.utc)
            check.consecutive_failures = 0
            check.error_message = None

            # Evaluate overall status
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

        # Track uptime
        self._track_uptime(name, check.status == HealthStatus.HEALTHY)

        # Publish status change event
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
        """Check system resources (CPU, memory, disk)."""
        check.metrics.clear()

        if check.name == "cpu_usage":
            # CPU percentage
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

            # Load average (Unix systems)
            try:
                load_avg = psutil.getloadavg()[0]  # 1-minute average
                metric = HealthMetric(
                    name="load_average",
                    value=load_avg,
                    unit="processes",
                    threshold_warning=check.metadata.get("metrics", {}).get("load_average", {}).get("threshold_warning", psutil.cpu_count() * 0.7),
                    threshold_critical=check.metadata.get("metrics", {}).get("load_average", {}).get("threshold_critical", psutil.cpu_count() * 0.9)
                )
                metric.evaluate()
                check.metrics.append(metric)
            except AttributeError:
                # Windows doesn't have getloadavg
                pass

        elif check.name == "memory_usage":
            # Virtual memory
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

            # Swap memory
            swap = psutil.swap_memory()
            if swap.total > 0:
                metric = HealthMetric(
                    name="swap_percent",
                    value=swap.percent,
                    unit="percent",
                    threshold_warning=check.metadata.get("metrics", {}).get("swap_percent", {}).get("threshold_warning", 50.0),
                    threshold_critical=check.metadata.get("metrics", {}).get("swap_percent", {}).get("threshold_critical", 80.0)
                )
                metric.evaluate()
                check.metrics.append(metric)

        elif check.name == "disk_usage":
            # Check disk usage for all mounted filesystems
            for part in psutil.disk_partitions(all=False):
                try:
                    usage = psutil.disk_usage(part.mountpoint)
                    metric = HealthMetric(
                        name=f"disk_{part.device.replace(':', '')}_percent",
                        value=(usage.used / usage.total) * 100,
                        unit="percent",
                        threshold_warning=check.metadata.get("metrics", {}).get("disk_percent", {}).get("threshold_warning", 80.0),
                        threshold_critical=check.metadata.get("metrics", {}).get("disk_percent", {}).get("threshold_critical", 95.0),
                        metadata={"mountpoint": part.mountpoint, "device": part.device}
                    )
                    metric.evaluate()
                    check.metrics.append(metric)
                except PermissionError:
                    continue

    async def _check_service_availability(self, check: HealthCheck) -> None:
        """Check service availability."""
        check.metrics.clear()

        service_config = check.metadata.get("service_config", {})

        # Check if service is running (basic port check)
        host = service_config.get("host", "localhost")
        port = service_config.get("port")

        if port:
            start_time = time.time()
            try:
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(host, port),
                    timeout=check.timeout
                )
                writer.close()
                await writer.wait_closed()

                response_time = (time.time() - start_time) * 1000

                metric = HealthMetric(
                    name="response_time",
                    value=response_time,
                    unit="ms",
                    threshold_warning=1000.0,
                    threshold_critical=5000.0,
                    metadata={"host": host, "port": port}
                )
                metric.evaluate()
                check.metrics.append(metric)

            except Exception as e:
                raise Exception(f"Service unavailable on {host}:{port}: {e}")

        # Additional custom checks based on service type
        if service_config.get("type") == "http":
            await self._check_http_service(check, service_config)
        elif service_config.get("type") == "database":
            await self._check_database_service(check, service_config)

    async def _check_api_endpoint(self, check: HealthCheck) -> None:
        """Check API endpoint availability."""
        check.metrics.clear()

        endpoint_config = check.metadata.get("endpoint", {})
        url = endpoint_config.get("url")
        method = endpoint_config.get("method", "GET")
        headers = endpoint_config.get("headers", {})
        expected_status = endpoint_config.get("expected_status", 200)

        if not url:
            raise ValueError("URL not configured for API endpoint check")

        start_time = time.time()
        try:
            async with self._http_session.request(
                method=method,
                url=url,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=check.timeout)
            ) as response:
                response_time = (time.time() - start_time) * 1000

                # Check response status
                if response.status != expected_status:
                    raise Exception(f"Unexpected status code: {response.status}, expected: {expected_status}")

                # Record response time
                metric = HealthMetric(
                    name="response_time",
                    value=response_time,
                    unit="ms",
                    threshold_warning=1000.0,
                    threshold_critical=5000.0,
                    metadata={"url": url, "method": method}
                )
                metric.evaluate()
                check.metrics.append(metric)

                # Check response size
                content = await response.read()
                metric = HealthMetric(
                    name="response_size",
                    value=len(content),
                    unit="bytes"
                )
                check.metrics.append(metric)

        except asyncio.TimeoutError:
            raise Exception(f"API endpoint timeout after {check.timeout}s")
        except Exception as e:
            raise Exception(f"API endpoint check failed: {e}")

    async def _check_file_system(self, check: HealthCheck) -> None:
        """Check file system accessibility."""
        check.metrics.clear()

        paths = check.metadata.get("paths", [])

        for path_str in paths:
            path = Path(path_str)

            try:
                # Check if path exists
                if not path.exists():
                    raise Exception(f"Path does not exist: {path}")

                # Check read/write permissions
                test_file = path / f".health_check_{int(time.time())}"
                test_file.write_text("test")
                test_file.unlink()

                # Count files
                file_count = len(list(path.iterdir()))

                metric = HealthMetric(
                    name=f"path_{path.name}_file_count",
                    value=file_count,
                    unit="files",
                    metadata={"path": str(path)}
                )
                check.metrics.append(metric)

            except Exception as e:
                raise Exception(f"File system check failed for {path}: {e}")

    async def _check_database(self, check: HealthCheck) -> None:
        """Check database connectivity."""
        check.metrics.clear()

        db_config = check.metadata.get("database", {})

        # This is a placeholder - actual implementation would depend on database type
        # For now, we'll just simulate a check
        await asyncio.sleep(0.1)

        metric = HealthMetric(
            name="connection_time",
            value=10.0,
            unit="ms",
            threshold_warning=100.0,
            threshold_critical=500.0
        )
        metric.evaluate()
        check.metrics.append(metric)

    async def _run_custom_check(self, check: HealthCheck) -> None:
        """Run custom health check."""
        check.metrics.clear()

        # Get custom check function
        check_func = check.metadata.get("check_function")
        if not check_func:
            raise ValueError("Custom check requires 'check_function' in metadata")

        # Execute the custom check
        if callable(check_func):
            if asyncio.iscoroutinefunction(check_func):
                result = await check_func(check)
            else:
                result = check_func(check)

            # Process results
            if isinstance(result, list):
                check.metrics = result
            elif isinstance(result, dict):
                for name, value in result.items():
                    if isinstance(value, (int, float)):
                        metric = HealthMetric(name=name, value=float(value), unit="")
                        metric.evaluate()
                        check.metrics.append(metric)

    async def _check_http_service(self, check: HealthCheck, service_config: Dict[str, Any]) -> None:
        """Check HTTP service health."""
        url = service_config.get("health_url", f"http://{service_config.get('host')}:{service_config.get('port')}/health")

        try:
            async with self._http_session.get(
                url,
                timeout=aiohttp.ClientTimeout(total=check.timeout)
            ) as response:
                if response.status != 200:
                    raise Exception(f"Health check returned status: {response.status}")

                health_data = await response.json()

                # Add metrics from health endpoint
                for key, value in health_data.items():
                    if isinstance(value, (int, float)) and "time" in key.lower():
                        metric = HealthMetric(
                            name=f"service_{key}",
                            value=float(value),
                            unit="ms" if "time" in key.lower() else ""
                        )
                        metric.evaluate()
                        check.metrics.append(metric)

        except Exception as e:
            raise Exception(f"HTTP service check failed: {e}")

    async def _check_database_service(self, check: HealthCheck, service_config: Dict[str, Any]) -> None:
        """Check database service health."""
        # Placeholder for database-specific health checks
        # Would implement based on database type (PostgreSQL, MySQL, etc.)
        pass

    def _track_uptime(self, check_name: str, is_healthy: bool) -> None:
        """Track uptime for a health check."""
        tracker = self._uptime_tracker[check_name]
        tracker.append((datetime.now(timezone.utc), is_healthy))

        # Keep only last 24 hours
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        self._uptime_tracker[check_name] = [
            (t, h) for t, h in tracker if t > cutoff
        ]

    def calculate_uptime(self, check_name: str, hours: int = 24) -> float:
        """Calculate uptime percentage for a check.

        Args:
            check_name: Name of the check
            hours: Number of hours to calculate uptime for

        Returns:
            Uptime percentage (0-100)
        """
        tracker = self._uptime_tracker.get(check_name, [])
        if not tracker:
            return 0.0

        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        recent_checks = [(t, h) for t, h in tracker if t > cutoff]

        if not recent_checks:
            return 0.0

        healthy_count = sum(1 for _, h in recent_checks if h)
        return (healthy_count / len(recent_checks)) * 100

    def get_overall_status(self) -> HealthStatus:
        """Get overall system health status."""
        if not self._checks:
            return HealthStatus.UNKNOWN

        statuses = [check.status for check in self._checks.values() if check.enabled]

        if not statuses:
            return HealthStatus.UNKNOWN

        # Determine overall status based on worst status
        if HealthStatus.CRITICAL in statuses:
            return HealthStatus.CRITICAL
        elif HealthStatus.UNHEALTHY in statuses:
            return HealthStatus.UNHEALTHY
        elif HealthStatus.DEGRADED in statuses:
            return HealthStatus.DEGRADED
        elif all(s == HealthStatus.HEALTHY for s in statuses):
            return HealthStatus.HEALTHY
        else:
            return HealthStatus.UNKNOWN

    async def generate_health_report(self) -> HealthReport:
        """Generate comprehensive health report."""
        report = HealthReport()
        report.overall_status = self.get_overall_status()
        report.checks = self._checks.copy()

        # Collect system metrics
        for check in self._checks.values():
            if check.check_type == CheckType.SYSTEM_RESOURCE:
                for metric in check.metrics:
                    report.system_metrics[f"{check.name}_{metric.name}"] = metric
            else:
                for metric in check.metrics:
                    report.service_metrics[f"{check.name}_{metric.name}"] = metric

        # Calculate overall uptime
        if self._uptime_tracker:
            all_healthy = []
            for check_name in self._checks:
                uptime = self.calculate_uptime(check_name)
                all_healthy.append(uptime)
            report.uptime_percentage = sum(all_healthy) / len(all_healthy) if all_healthy else 0.0

        # Get active alerts
        report.alerts = list(self._active_alerts.values())

        return report

    async def _publish_health_event(self, check: HealthCheck, old_status: HealthStatus) -> None:
        """Publish health status change event."""
        event = HealthEvent(
            check_name=check.name,
            old_status=old_status,
            new_status=check.status,
            metrics={m.name: m.value for m in check.metrics},
            source="health_monitor"
        )

        # Set priority based on status
        if check.status == HealthStatus.CRITICAL:
            event.priority = EventPriority.CRITICAL
        elif check.status == HealthStatus.UNHEALTHY:
            event.priority = EventPriority.HIGH
        elif check.status == HealthStatus.DEGRADED:
            event.priority = EventPriority.NORMAL
        else:
            event.priority = EventPriority.LOW

        await self.event_bus.publish(event)

        # Generate alerts if needed
        if check.status in [HealthStatus.DEGRADED, HealthStatus.UNHEALTHY, HealthStatus.CRITICAL]:
            await self._generate_alerts(check)

    async def _generate_alerts(self, check: HealthCheck) -> None:
        """Generate alerts for unhealthy metrics."""
        for metric in check.metrics:
            if metric.status in [HealthStatus.DEGRADED, HealthStatus.UNHEALTHY, HealthStatus.CRITICAL]:
                alert_id = f"{check.name}_{metric.name}"

                # Skip if alert already exists and not resolved
                if alert_id in self._active_alerts and not self._active_alerts[alert_id].resolved:
                    continue

                # Determine severity
                if metric.status == HealthStatus.CRITICAL:
                    severity = AlertSeverity.CRITICAL
                elif metric.status == HealthStatus.UNHEALTHY:
                    severity = AlertSeverity.ERROR
                else:
                    severity = AlertSeverity.WARNING

                # Create alert
                alert = HealthAlert(
                    alert_id=alert_id,
                    check_name=check.name,
                    severity=severity,
                    message=f"{metric.name} is {metric.value:.1f}{metric.unit}",
                    metric_name=metric.name,
                    metric_value=metric.value,
                    threshold=metric.threshold_warning if severity == AlertSeverity.WARNING else metric.threshold_critical
                )

                self._active_alerts[alert_id] = alert
                self._alert_history.append(alert)

                self.logger.warning(f"Health alert generated: {alert.message}")

    async def acknowledge_alert(
        self,
        alert_id: str,
        acknowledged_by: str
    ) -> bool:
        """Acknowledge a health alert.

        Args:
            alert_id: ID of alert to acknowledge
            acknowledged_by: User acknowledging the alert

        Returns:
            True if acknowledged successfully
        """
        if alert_id not in self._active_alerts:
            return False

        alert = self._active_alerts[alert_id]
        alert.acknowledged = True
        alert.acknowledged_by = acknowledged_by
        alert.acknowledged_at = datetime.now(timezone.utc)

        self.logger.info(f"Alert {alert_id} acknowledged by {acknowledged_by}")
        return True

    async def resolve_alert(self, alert_id: str) -> bool:
        """Resolve a health alert.

        Args:
            alert_id: ID of alert to resolve

        Returns:
            True if resolved successfully
        """
        if alert_id not in self._active_alerts:
            return False

        alert = self._active_alerts[alert_id]
        alert.resolved = True
        alert.resolved_at = datetime.now(timezone.utc)

        # Remove from active alerts
        del self._active_alerts[alert_id]

        self.logger.info(f"Alert {alert_id} resolved")
        return True

    async def get_metrics_history(
        self,
        metric_name: str,
        limit: int = 100
    ) -> List[Tuple[datetime, float]]:
        """Get historical metrics data.

        Args:
            metric_name: Name of metric
            limit: Maximum number of data points

        Returns:
            List of (timestamp, value) tuples
        """
        history = list(self._metrics_history.get(metric_name, []))[-limit:]
        return [(h["timestamp"], h["value"]) for h in history]

    async def _monitoring_loop(self) -> None:
        """Main monitoring loop."""
        self.logger.info("Starting health monitoring loop")

        while not self._shutdown_event.is_set():
            try:
                # Update metrics history
                for check in self._checks.values():
                    for metric in check.metrics:
                        self._metrics_history[f"{check.name}_{metric.name}"].append({
                            "timestamp": metric.timestamp,
                            "value": metric.value,
                            "status": metric.status
                        })

                # Check for anomalies
                await self._check_anomalies()

                await asyncio.sleep(30)  # Update every 30 seconds

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(10)

    async def _reporting_loop(self) -> None:
        """Periodic health report generation."""
        while not self._shutdown_event.is_set():
            try:
                # Generate daily report
                await asyncio.sleep(3600)  # Every hour

                report = await self.generate_health_report()

                # Save report to file
                report_file = self.config.paths.reports_path / f"health_report_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
                report_file.parent.mkdir(parents=True, exist_ok=True)

                async with aiofiles.open(report_file, 'w') as f:
                    await f.write(json.dumps(report.to_dict(), indent=2, default=str))

                # Log summary
                self.logger.info(
                    f"Health report generated: Overall={report.overall_status.value}, "
                    f"Uptime={report.uptime_percentage:.1f}%, "
                    f"Alerts={len(report.alerts)}"
                )

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in reporting loop: {e}")

    async def _cleanup_loop(self) -> None:
        """Cleanup old data and resources."""
        while not self._shutdown_event.is_set():
            try:
                # Clean old metrics history (keep last 7 days)
                cutoff = datetime.now(timezone.utc) - timedelta(days=7)
                for metric_name, history in self._metrics_history.items():
                    while history and history[0]["timestamp"] < cutoff:
                        history.popleft()

                # Clean old alert history (keep last 30 days)
                alert_cutoff = datetime.now(timezone.utc) - timedelta(days=30)
                self._alert_history = [
                    alert for alert in self._alert_history
                    if alert.timestamp > alert_cutoff
                ]

                # Run every 6 hours
                await asyncio.sleep(21600)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in cleanup loop: {e}")

    async def _check_anomalies(self) -> None:
        """Check for anomalies in metrics."""
        for metric_name, history in self._metrics_history.items():
            if len(history) < 10:
                continue

            # Get recent values
            recent = list(history)[-10:]
            values = [h["value"] for h in recent]

            # Check for spikes or drops
            if len(values) >= 2:
                latest = values[-1]
                previous = values[-2]

                # Detect sudden changes (>50% change)
                if previous > 0:
                    change_percent = abs((latest - previous) / previous) * 100
                    if change_percent > 50:
                        self.logger.warning(
                            f"Anomaly detected in {metric_name}: "
                            f"{previous:.1f} -> {latest:.1f} ({change_percent:.1f}% change)"
                        )


# Global instance
_health_monitor: Optional[HealthMonitor] = None


def get_health_monitor() -> HealthMonitor:
    """Get global health monitor instance."""
    global _health_monitor
    if _health_monitor is None:
        _health_monitor = HealthMonitor()
    return _health_monitor


async def initialize_health_monitor() -> None:
    """Initialize the global health monitor."""
    monitor = get_health_monitor()
    await monitor.initialize()


# Health check decorator
def health_check(
    name: str,
    check_type: CheckType = CheckType.CUSTOM,
    interval: int = 60,
    **kwargs
):
    """Decorator to register a function as a health check.

    Args:
        name: Name of the health check
        check_type: Type of health check
        interval: Check interval in seconds
        **kwargs: Additional check parameters
    """
    def decorator(func: Callable):
        monitor = get_health_monitor()

        # Register the check
        monitor.register_check(
            name=name,
            check_type=check_type,
            description=func.__doc__ or f"Custom check: {name}",
            interval=interval,
            check_function=func,
            **kwargs
        )

        return func

    return decorator