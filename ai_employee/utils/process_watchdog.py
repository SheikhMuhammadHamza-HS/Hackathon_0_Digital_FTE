"""
Process watchdog system for AI Employee.

Monitors process health and automatically restarts failed processes with
intelligent backoff strategies and comprehensive failure tracking.
"""

import asyncio
import psutil
import signal
import time
import json
from datetime import datetime, timezone, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Union, Tuple
from dataclasses import dataclass, field, asdict
import aiofiles
from collections import deque, defaultdict
import subprocess
import os
import uuid
import threading

from ..core.event_bus import get_event_bus, Event, EventPriority
from ..core.config import get_config, AppConfig
from ..utils.logging_config import get_logger
from ..utils.health_monitor import HealthStatus, HealthMetric
from ..utils.error_recovery import ErrorRecoveryService, ErrorCategory, ErrorSeverity

logger = get_logger(__name__)


class ProcessStatus(Enum):
    """Process status states."""
    RUNNING = "running"
    STOPPED = "stopped"
    CRASHED = "crashed"
    HANGING = "hanging"
    RESTARTING = "restarting"
    DISABLED = "disabled"
    UNKNOWN = "unknown"


class RestartStrategy(Enum):
    """Restart strategy types."""
    IMMEDIATE = "immediate"
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    FIXED_INTERVAL = "fixed_interval"
    NO_RESTART = "no_restart"


class HealthCheckType(Enum):
    """Process health check types."""
    HEARTBEAT = "heartbeat"
    CPU_USAGE = "cpu_usage"
    MEMORY_USAGE = "memory_usage"
    RESPONSE_TIME = "response_time"
    CUSTOM_ENDPOINT = "custom_endpoint"


@dataclass
class ProcessInfo:
    """Information about a monitored process."""
    pid: int = field(default_factory=0)
    name: str = field(default_factory="")
    command: List[str] = field(default_factory=list)
    working_dir: Optional[str] = field(default_factory=lambda: None)
    env: Dict[str, str] = field(default_factory=dict)
    status: ProcessStatus = field(default_factory=ProcessStatus.UNKNOWN)
    process: Optional[psutil.Process] = field(default_factory=lambda: None)
    start_time: Optional[datetime] = field(default_factory=lambda: None)
    last_heartbeat: Optional[datetime] = field(default_factory=lambda: None)
    last_restart: Optional[datetime] = field(default_factory=lambda: None)
    restart_count: int = field(default_factory=0)
    max_restarts: int = field(default_factory=5)
    uptime: float = field(default_factory=0.0)  # seconds
    cpu_percent: float = field(default_factory=0.0)
    memory_mb: float = field(default_factory=0.0)
    metadata: Dict[str, Any] = field(default_factory=dict)
    monitored: bool = field(default_factory=True)
    auto_restart: bool = field(default_factory=True)
    restart_strategy: RestartStrategy = field(default_factory=RestartStrategy.EXPONENTIAL_BACKOFF)
    health_checks: List[HealthCheckType] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "pid": self.pid,
            "name": self.name,
            "command": self.command,
            "working_dir": self.working_dir,
            "status": self.status.value,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "last_heartbeat": self.last_heartbeat.isoformat() if self.last_heartbeat else None,
            "last_restart": self.last_restart.isoformat() if self.last_restart else None,
            "restart_count": self.restart_count,
            "uptime": self.uptime,
            "cpu_percent": self.cpu_percent,
            "memory_mb": self.memory_mb,
            "monitored": self.monitored,
            "auto_restart": self.auto_restart,
            "restart_strategy": self.restart_strategy.value
        }


@dataclass
class RestartHistory:
    """History of process restarts."""
    process_name: str = field(default_factory="")
    timestamp: datetime = field(default_factory=datetime.utcnow)
    reason: str = field(default_factory="")
    exit_code: Optional[int] = field(default_factory=lambda: None)
    downtime: float = field(default_factory=0.0)  # seconds
    restart_time: float = field(default_factory=0.0)  # seconds
    successful: bool = field(default_factory=False)


@dataclass
class HealthCheckConfig:
    """Configuration for process health checks."""
    check_type: HealthCheckType = field(default_factory=HealthCheckType.HEARTBEAT)
    interval: int = field(default_factory=30)  # seconds
    timeout: int = field(default_factory=10)  # seconds
    threshold: float = field(default_factory=0.0)
    endpoint: Optional[str] = field(default_factory=lambda: None)
    custom_function: Optional[Callable] = field(default_factory=lambda: None)
    enabled: bool = field(default_factory=True)


@dataclass
class ProcessWatchdogEvent(Event):
    """Event published for process watchdog events."""
    process_name: str = field(default_factory="")
    pid: int = field(default_factory=0)
    event_type: str = field(default_factory="")  # started, stopped, crashed, restarted, health_failed
    message: str = field(default_factory="")
    status: ProcessStatus = field(default_factory=ProcessStatus.UNKNOWN)
    metrics: Dict[str, float] = field(default_factory=dict)


@dataclass
class BackoffConfig:
    """Configuration for backoff strategies."""
    strategy: RestartStrategy = RestartStrategy.EXPONENTIAL_BACKOFF
    base_delay: float = 1.0  # seconds
    max_delay: float = 300.0  # seconds
    multiplier: float = 2.0
    jitter: bool = True
    max_attempts: int = 5


class ProcessWatchdog:
    """Process monitoring and automatic restart system."""

    def __init__(
        self,
        config: Optional[AppConfig] = None,
        event_bus=None,
        error_recovery: Optional[ErrorRecoveryService] = None
    ):
        """Initialize process watchdog.

        Args:
            config: Application configuration
            event_bus: Event bus instance
            error_recovery: Error recovery service instance
        """
        self.config = config or get_config()
        self.event_bus = event_bus or get_event_bus()
        self.error_recovery = error_recovery
        self.logger = get_logger(__name__)

        # Process registry
        self._processes: Dict[str, ProcessInfo] = {}
        self._process_tasks: Dict[str, asyncio.Task] = {}
        self._health_check_tasks: Dict[str, asyncio.Task] = {}
        self._health_configs: Dict[str, List[HealthCheckConfig]] = {}

        # Restart tracking
        self._restart_history: deque = deque(maxlen=1000)
        self._restart_backoffs: Dict[str, BackoffConfig] = {}
        self._last_restart_times: Dict[str, datetime] = {}

        # Background tasks
        self._monitoring_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()

        # Statistics
        self._stats = {
            "total_restarts": 0,
            "successful_restarts": 0,
            "failed_restarts": 0,
            "process_crashes": 0,
            "uptime_total": 0.0
        }

        # Default configuration
        self._default_backoff = BackoffConfig()

    async def initialize(self) -> None:
        """Initialize the process watchdog system."""
        self.logger.info("Initializing Process Watchdog")

        # Start background tasks
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

        # Register event handlers
        await self._register_event_handlers()

        # Load existing processes if any
        await self._load_process_configs()

        self.logger.info("Process Watchdog initialized successfully")

    async def shutdown(self) -> None:
        """Shutdown the process watchdog system."""
        self.logger.info("Shutting down Process Watchdog")

        # Signal shutdown
        self._shutdown_event.set()

        # Cancel monitoring tasks
        if self._monitoring_task and not self._monitoring_task.done():
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass

        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        # Cancel all process monitoring tasks
        for task in self._process_tasks.values():
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        # Cancel health check tasks
        for task in self._health_check_tasks.values():
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        # Save process states
        await self._save_process_states()

        self.logger.info("Process Watchdog shutdown complete")

    async def register_process(
        self,
        name: str,
        command: Union[str, List[str]],
        working_dir: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        auto_restart: bool = True,
        restart_strategy: RestartStrategy = RestartStrategy.EXPONENTIAL_BACKOFF,
        max_restarts: int = 5,
        health_checks: Optional[List[HealthCheckType]] = None,
        backoff_config: Optional[BackoffConfig] = None,
        **kwargs
    ) -> ProcessInfo:
        """Register a process for monitoring.

        Args:
            name: Unique process name
            command: Command to run (string or list)
            working_dir: Working directory for process
            env: Environment variables
            auto_restart: Whether to auto-restart on failure
            restart_strategy: Strategy for restart attempts
            max_restarts: Maximum number of restarts
            health_checks: List of health check types
            backoff_config: Backoff strategy configuration
            **kwargs: Additional process metadata

        Returns:
            ProcessInfo instance
        """
        if name in self._processes:
            self.logger.warning(f"Process '{name}' already registered, updating...")
            await self.unregister_process(name)

        # Normalize command
        if isinstance(command, str):
            command = command.split()

        # Create process info
        process_info = ProcessInfo(
            pid=0,  # Will be set when started
            name=name,
            command=command,
            working_dir=working_dir,
            env=env or {},
            auto_restart=auto_restart,
            restart_strategy=restart_strategy,
            max_restarts=max_restarts,
            health_checks=health_checks or [HealthCheckType.HEARTBEAT],
            metadata=kwargs
        )

        # Store backoff config
        self._restart_backoffs[name] = backoff_config or self._default_backoff

        # Register process
        self._processes[name] = process_info

        # Setup health checks
        await self._setup_health_checks(name)

        # Start monitoring if enabled
        if process_info.monitored:
            await self.start_monitoring(name)

        self.logger.info(f"Registered process for monitoring: {name}")
        return process_info

    async def unregister_process(self, name: str) -> bool:
        """Unregister a process from monitoring.

        Args:
            name: Process name to unregister

        Returns:
            True if unregistered successfully
        """
        if name not in self._processes:
            self.logger.warning(f"Process '{name}' not found")
            return False

        # Stop monitoring
        await self.stop_monitoring(name)

        # Stop process if running
        process_info = self._processes[name]
        if process_info.process and process_info.process.is_running():
            await self._stop_process(process_info)

        # Remove from registry
        del self._processes[name]

        # Clean up configs
        if name in self._restart_backoffs:
            del self._restart_backoffs[name]
        if name in self._last_restart_times:
            del self._last_restart_times[name]
        if name in self._health_configs:
            del self._health_configs[name]

        self.logger.info(f"Unregistered process: {name}")
        return True

    async def start_process(self, name: str) -> bool:
        """Start a monitored process.

        Args:
            name: Process name to start

        Returns:
            True if started successfully
        """
        if name not in self._processes:
            self.logger.error(f"Process '{name}' not registered")
            return False

        process_info = self._processes[name]

        # Check if already running
        if process_info.process and process_info.process.is_running():
            self.logger.warning(f"Process '{name}' is already running")
            return True

        try:
            # Start the process
            self.logger.info(f"Starting process: {name}")

            # Prepare environment
            env = os.environ.copy()
            env.update(process_info.env)

            # Start subprocess
            process = await asyncio.create_subprocess_exec(
                *process_info.command,
                cwd=process_info.working_dir,
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            # Get psutil Process object for monitoring
            psutil_process = psutil.Process(process.pid)

            # Update process info
            process_info.pid = process.pid
            process_info.process = psutil_process
            process_info.status = ProcessStatus.RUNNING
            process_info.start_time = datetime.now(timezone.utc)
            process_info.last_heartbeat = datetime.now(timezone.utc)

            # Start monitoring task
            if name not in self._process_tasks or self._process_tasks[name].done():
                self._process_tasks[name] = asyncio.create_task(self._monitor_process(name))

            # Publish event
            await self._publish_event(
                process_info,
                "started",
                f"Process started successfully"
            )

            self.logger.info(f"Process '{name}' started with PID {process.pid}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to start process '{name}': {e}")
            process_info.status = ProcessStatus.CRASHED

            # Publish error event
            await self._publish_event(
                process_info,
                "crashed",
                f"Failed to start: {e}"
            )

            return False

    async def stop_process(self, name: str, force: bool = False) -> bool:
        """Stop a monitored process.

        Args:
            name: Process name to stop
            force: Whether to force kill

        Returns:
            True if stopped successfully
        """
        if name not in self._processes:
            self.logger.error(f"Process '{name}' not registered")
            return False

        process_info = self._processes[name]

        if not process_info.process or not process_info.process.is_running():
            self.logger.warning(f"Process '{name}' is not running")
            return True

        return await self._stop_process(process_info, force)

    async def restart_process(self, name: str, reason: str = "manual") -> bool:
        """Restart a process.

        Args:
            name: Process name to restart
            reason: Reason for restart

        Returns:
            True if restarted successfully
        """
        if name not in self._processes:
            self.logger.error(f"Process '{name}' not registered")
            return False

        process_info = self._processes[name]

        # Check restart limit
        if process_info.restart_count >= process_info.max_restarts:
            self.logger.error(f"Max restarts exceeded for '{name}'")
            return False

        self.logger.info(f"Restarting process '{name}': {reason}")

        # Record restart start time
        start_time = time.time()

        # Stop if running
        if process_info.process and process_info.process.is_running():
            await self.stop_process(name, force=True)

        # Update status
        process_info.status = ProcessStatus.RESTARTING
        process_info.last_restart = datetime.now(timezone.utc)

        # Wait a bit
        await asyncio.sleep(1)

        # Start again
        success = await self.start_process(name)

        if success:
            process_info.restart_count += 1
            restart_time = time.time() - start_time

            # Record restart history
            history = RestartHistory(
                process_name=name,
                timestamp=datetime.now(timezone.utc),
                reason=reason,
                restart_time=restart_time,
                successful=True
            )
            self._restart_history.append(history)

            # Update stats
            self._stats["total_restarts"] += 1
            self._stats["successful_restarts"] += 1

            # Publish event
            await self._publish_event(
                process_info,
                "restarted",
                f"Process restarted: {reason}"
            )

            self.logger.info(f"Process '{name}' restarted in {restart_time:.2f}s")
        else:
            process_info.status = ProcessStatus.CRASHED
            self._stats["total_restarts"] += 1
            self._stats["failed_restarts"] += 1

            # Record failure
            history = RestartHistory(
                process_name=name,
                timestamp=datetime.now(timezone.utc),
                reason=reason,
                successful=False
            )
            self._restart_history.append(history)

        return success

    async def start_monitoring(self, name: str) -> None:
        """Start monitoring a process.

        Args:
            name: Process name to monitor
        """
        if name not in self._processes:
            raise ValueError(f"Process '{name}' not registered")

        # Start process monitoring task
        if name not in self._process_tasks or self._process_tasks[name].done():
            self._process_tasks[name] = asyncio.create_task(self._monitor_process(name))

        # Start health check tasks
        await self._start_health_checks(name)

        self.logger.info(f"Started monitoring for process: {name}")

    async def stop_monitoring(self, name: str) -> None:
        """Stop monitoring a process.

        Args:
            name: Process name to stop monitoring
        """
        # Cancel process monitoring task
        if name in self._process_tasks and not self._process_tasks[name].done():
            self._process_tasks[name].cancel()
            try:
                await self._process_tasks[name]
            except asyncio.CancelledError:
                pass

        # Cancel health check tasks
        if name in self._health_check_tasks:
            for check_name, task in self._health_check_tasks[name].items():
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
            del self._health_check_tasks[name]

        self.logger.info(f"Stopped monitoring for process: {name}")

    async def get_process_status(self, name: str) -> Optional[ProcessInfo]:
        """Get current status of a process.

        Args:
            name: Process name

        Returns:
            ProcessInfo or None if not found
        """
        if name not in self._processes:
            return None

        process_info = self._processes[name]

        # Update status if process is running
        if process_info.process and process_info.process.is_running():
            try:
                process_info.cpu_percent = process_info.process.cpu_percent()
                process_info.memory_mb = process_info.process.memory_info().rss / 1024 / 1024

                # Calculate uptime
                if process_info.start_time:
                    process_info.uptime = (datetime.now(timezone.utc) - process_info.start_time).total_seconds()
            except psutil.NoSuchProcess:
                process_info.status = ProcessStatus.CRASHED
                process_info.process = None

        return process_info

    async def get_all_processes(self) -> Dict[str, ProcessInfo]:
        """Get status of all monitored processes."""
        result = {}
        for name in self._processes:
            result[name] = await self.get_process_status(name)
        return result

    async def get_restart_history(self, name: Optional[str] = None, limit: int = 100) -> List[RestartHistory]:
        """Get restart history.

        Args:
            name: Optional process name filter
            limit: Maximum number of records

        Returns:
            List of restart history records
        """
        history = list(self._restart_history)

        if name:
            history = [h for h in history if h.process_name == name]

        # Sort by timestamp (newest first)
        history.sort(key=lambda h: h.timestamp, reverse=True)

        return history[:limit]

    async def calculate_uptime(self, name: str, hours: int = 24) -> float:
        """Calculate uptime percentage for a process.

        Args:
            name: Process name
            hours: Number of hours to calculate for

        Returns:
            Uptime percentage (0-100)
        """
        history = [h for h in self._restart_history if h.process_name == name]

        if not history:
            # If no history, check current process
            process = await self.get_process_status(name)
            if process and process.status == ProcessStatus.RUNNING and process.start_time:
                uptime = (datetime.now(timezone.utc) - process.start_time).total_seconds()
                return min(100.0, (uptime / (hours * 3600)) * 100)
            return 0.0

        # Calculate from history
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        recent_history = [h for h in history if h.timestamp > cutoff]

        if not recent_history:
            return 0.0

        # Simple calculation: successful restarts / total attempts
        successful = sum(1 for h in recent_history if h.successful)
        return (successful / len(recent_history)) * 100 if recent_history else 0.0

    async def _monitor_process(self, name: str) -> None:
        """Monitor a single process.

        Args:
            name: Process name to monitor
        """
        process_info = self._processes[name]
        check_interval = 5  # seconds

        while not self._shutdown_event.is_set() and process_info.monitored:
            try:
                # Check if process is still running
                if process_info.process:
                    try:
                        # Check if process exists
                        if not process_info.process.is_running():
                            self.logger.warning(f"Process '{name}' is not running")
                            process_info.status = ProcessStatus.CRASHED

                            # Attempt restart if enabled
                            if process_info.auto_restart:
                                await self._handle_process_crash(name)

                    except psutil.NoSuchProcess:
                        self.logger.error(f"Process '{name}' no longer exists")
                        process_info.status = ProcessStatus.CRASHED
                        process_info.process = None

                        # Attempt restart if enabled
                        if process_info.auto_restart:
                            await self._handle_process_crash(name)

                # Check for hanging processes
                await self._check_process_hang(name)

                await asyncio.sleep(check_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error monitoring process '{name}': {e}")
                await asyncio.sleep(10)

    async def _check_process_hang(self, name: str) -> None:
        """Check if process is hanging.

        Args:
            name: Process name to check
        """
        process_info = self._processes[name]

        if not process_info.process or not process_info.process.is_running():
            return

        # Check CPU usage
        try:
            cpu_percent = process_info.process.cpu_percent(interval=0.1)

            # High CPU for extended time might indicate hang
            if cpu_percent > 95.0:
                # Check how long it's been running
                if process_info.start_time:
                    runtime = (datetime.now(timezone.utc) - process_info.start_time).total_seconds()
                    if runtime > 300:  # 5 minutes
                        self.logger.warning(f"Process '{name}' might be hanging (CPU: {cpu_percent}%)")
                        process_info.status = ProcessStatus.HANGING

                        # Publish hang event
                        await self._publish_event(
                            process_info,
                            "health_failed",
                            f"Process might be hanging (CPU: {cpu_percent}%)"
                        )

        except psutil.NoSuchProcess:
            pass

    async def _handle_process_crash(self, name: str) -> None:
        """Handle process crash.

        Args:
            name: Process name that crashed
        """
        process_info = self._processes[name]

        self.logger.error(f"Process '{name}' crashed")

        # Update stats
        self._stats["process_crashes"] += 1

        # Check if we should restart
        if process_info.restart_count >= process_info.max_restarts:
            self.logger.error(f"Max restarts exceeded for '{name}', disabling auto-restart")
            process_info.auto_restart = False
            process_info.status = ProcessStatus.DISABLED

            # Publish critical event
            await self._publish_event(
                process_info,
                "crashed",
                f"Process crashed and max restarts exceeded",
                priority=EventPriority.CRITICAL
            )

            # Notify error recovery
            if self.error_recovery:
                await self.error_recovery.handle_system_crash(
                    name,
                    {"pid": process_info.pid, "restart_count": process_info.restart_count}
                )
            return

        # Calculate backoff delay
        backoff = self._restart_backoffs[name]
        delay = self._calculate_backoff_delay(name, backoff)

        # Schedule restart
        self.logger.info(f"Scheduling restart for '{name}' in {delay:.1f}s")
        await asyncio.sleep(delay)

        # Attempt restart
        await self.restart_process(name, "crash_recovery")

    def _calculate_backoff_delay(self, name: str, backoff: BackoffConfig) -> float:
        """Calculate backoff delay for restart.

        Args:
            name: Process name
            backoff: Backoff configuration

        Returns:
            Delay in seconds
        """
        process_info = self._processes[name]

        if backoff.strategy == RestartStrategy.IMMEDIATE:
            return 0.0
        elif backoff.strategy == RestartStrategy.FIXED_INTERVAL:
            return backoff.base_delay
        elif backoff.strategy == RestartStrategy.LINEAR_BACKOFF:
            delay = backoff.base_delay * process_info.restart_count
        elif backoff.strategy == RestartStrategy.EXPONENTIAL_BACKOFF:
            delay = backoff.base_delay * (backoff.multiplier ** process_info.restart_count)
        else:
            delay = backoff.base_delay

        # Apply max delay limit
        delay = min(delay, backoff.max_delay)

        # Add jitter if enabled
        if backoff.jitter:
            import random
            jitter = random.uniform(0.8, 1.2)
            delay *= jitter

        return delay

    async def _setup_health_checks(self, name: str) -> None:
        """Setup health checks for a process.

        Args:
            name: Process name
        """
        process_info = self._processes[name]
        configs = []

        for check_type in process_info.health_checks:
            config = HealthCheckConfig(
                check_type=check_type,
                interval=30,
                timeout=10,
                enabled=True
            )

            # Set default thresholds based on type
            if check_type == HealthCheckType.CPU_USAGE:
                config.threshold = 90.0
            elif check_type == HealthCheckType.MEMORY_USAGE:
                config.threshold = 500.0  # MB
            elif check_type == HealthCheckType.RESPONSE_TIME:
                config.threshold = 5000.0  # ms

            configs.append(config)

        self._health_configs[name] = configs

    async def _start_health_checks(self, name: str) -> None:
        """Start health check tasks for a process.

        Args:
            name: Process name
        """
        if name not in self._health_configs:
            return

        if name not in self._health_check_tasks:
            self._health_check_tasks[name] = {}

        configs = self._health_configs[name]

        for config in configs:
            if not config.enabled:
                continue

            check_name = f"{name}_{config.check_type.value}"

            # Cancel existing task if any
            if check_name in self._health_check_tasks[name]:
                task = self._health_check_tasks[name][check_name]
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass

            # Start new health check task
            task = asyncio.create_task(self._run_health_check(name, config))
            self._health_check_tasks[name][check_name] = task

    async def _run_health_check(self, name: str, config: HealthCheckConfig) -> None:
        """Run a health check task.

        Args:
            name: Process name
            config: Health check configuration
        """
        process_info = self._processes[name]

        while not self._shutdown_event.is_set() and process_info.monitored and config.enabled:
            try:
                # Run the check
                await self._perform_health_check(name, config)

                # Wait for next check
                await asyncio.sleep(config.interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Health check failed for '{name}': {e}")
                await asyncio.sleep(min(config.interval, 60))

    async def _perform_health_check(self, name: str, config: HealthCheckConfig) -> None:
        """Perform a single health check.

        Args:
            name: Process name
            config: Health check configuration
        """
        process_info = self._processes[name]

        if not process_info.process or not process_info.process.is_running():
            return

        check_passed = True
        metrics = {}

        try:
            if config.check_type == HealthCheckType.HEARTBEAT:
                # Update heartbeat timestamp
                process_info.last_heartbeat = datetime.now(timezone.utc)
                metrics["heartbeat"] = 1.0

            elif config.check_type == HealthCheckType.CPU_USAGE:
                cpu = process_info.process.cpu_percent(interval=1.0)
                metrics["cpu_percent"] = cpu
                if cpu > config.threshold:
                    check_passed = False

            elif config.check_type == HealthCheckType.MEMORY_USAGE:
                memory = process_info.process.memory_info().rss / 1024 / 1024
                metrics["memory_mb"] = memory
                if memory > config.threshold:
                    check_passed = False

            elif config.check_type == HealthCheckType.RESPONSE_TIME:
                # Would implement actual response time check
                # For now, simulate
                metrics["response_time"] = 100.0
                if metrics["response_time"] > config.threshold:
                    check_passed = False

            elif config.check_type == HealthCheckType.CUSTOM_ENDPOINT:
                # Would implement custom endpoint check
                if config.endpoint:
                    # Simulate check
                    metrics["endpoint_check"] = 1.0

        except Exception as e:
            self.logger.error(f"Health check error for '{name}': {e}")
            check_passed = False

        # Update process info with metrics
        if "cpu_percent" in metrics:
            process_info.cpu_percent = metrics["cpu_percent"]
        if "memory_mb" in metrics:
            process_info.memory_mb = metrics["memory_mb"]

        # Handle check failure
        if not check_passed:
            self.logger.warning(f"Health check failed for '{name}': {config.check_type.value}")

            # Publish event
            await self._publish_event(
                process_info,
                "health_failed",
                f"Health check failed: {config.check_type.value}",
                metrics=metrics
            )

    async def _stop_process(self, process_info: ProcessInfo, force: bool = False) -> bool:
        """Stop a process.

        Args:
            process_info: Process info to stop
            force: Whether to force kill

        Returns:
            True if stopped successfully
        """
        try:
            if not process_info.process:
                return True

            pid = process_info.pid
            self.logger.info(f"Stopping process '{process_info.name}' (pid: {pid})")

            if force:
                process_info.process.kill()
            else:
                process_info.process.terminate()

                # Wait for graceful shutdown
                try:
                    process_info.process.wait(timeout=10)
                except psutil.TimeoutExpired:
                    self.logger.warning(f"Process '{process_info.name}' did not terminate, killing...")
                    process_info.process.kill()

            # Update status
            process_info.status = ProcessStatus.STOPPED
            process_info.process = None
            process_info.pid = 0

            # Publish event
            await self._publish_event(
                process_info,
                "stopped",
                f"Process stopped (force={force})"
            )

            return True

        except psutil.NoSuchProcess:
            process_info.status = ProcessStatus.STOPPED
            process_info.process = None
            return True
        except Exception as e:
            self.logger.error(f"Failed to stop process '{process_info.name}': {e}")
            return False

    async def _publish_event(
        self,
        process_info: ProcessInfo,
        event_type: str,
        message: str,
        metrics: Optional[Dict[str, float]] = None,
        priority: EventPriority = EventPriority.NORMAL
    ) -> None:
        """Publish a process watchdog event.

        Args:
            process_info: Process information
            event_type: Type of event
            message: Event message
            metrics: Optional metrics
            priority: Event priority
        """
        event = ProcessWatchdogEvent(
            process_name=process_info.name,
            pid=process_info.pid,
            event_type=event_type,
            message=message,
            status=process_info.status,
            metrics=metrics or {
                "cpu_percent": process_info.cpu_percent,
                "memory_mb": process_info.memory_mb,
                "uptime": process_info.uptime,
                "restart_count": process_info.restart_count
            },
            priority=priority,
            source="process_watchdog"
        )

        await self.event_bus.publish(event)

    async def _register_event_handlers(self) -> None:
        """Register event handlers."""
        # Subscribe to health monitor events
        from ..utils.health_monitor import HealthEvent
        await self.event_bus.subscribe(HealthEvent, self._handle_health_event)

        # Subscribe to error events
        from ..utils.error_recovery import ErrorEvent
        await self.event_bus.subscribe(ErrorEvent, self._handle_error_event)

    async def _handle_health_event(self, event: Event) -> None:
        """Handle health monitoring events.

        Args:
            event: Health event
        """
        # If critical health event, check if any monitored processes need action
        if hasattr(event, 'severity') and hasattr(event.severity, 'name') and event.severity.name == "CRITICAL":
            self.logger.warning(f"Critical health event detected: {event.check_name}")

            # Could implement process recovery based on health events
            for name, process_info in self._processes.items():
                if process_info.status == ProcessStatus.RUNNING and event.check_name in name:
                    self.logger.info(f"Health issue detected for related process: {name}")

    async def _handle_error_event(self, event) -> None:
        """Handle error events.

        Args:
            event: Error event
        """
        # Check if error is related to a monitored process
        if hasattr(event, 'context') and event.context:
            process_name = event.context.get("process_name")
            if process_name and process_name in self._processes:
                self.logger.warning(f"Error event for monitored process: {process_name}")

                # Could implement proactive restart on certain errors
                if hasattr(event, 'error_severity') and event.error_severity.name == "CRITICAL":
                    process_info = self._processes[process_name]
                    if process_info.auto_restart and process_info.restart_count < process_info.max_restarts:
                        self.logger.info(f"Proactively restarting process due to critical error: {process_name}")
                        await self.restart_process(process_name, "error_recovery")

    async def _monitoring_loop(self) -> None:
        """Main monitoring loop."""
        self.logger.info("Starting process monitoring loop")

        while not self._shutdown_event.is_set():
            try:
                # Update statistics
                total_uptime = 0.0
                running_count = 0

                for name, process_info in self._processes.items():
                    if process_info.status == ProcessStatus.RUNNING and process_info.start_time:
                        uptime = (datetime.now(timezone.utc) - process_info.start_time).total_seconds()
                        total_uptime += uptime
                        running_count += 1

                self._stats["uptime_total"] = total_uptime

                await asyncio.sleep(60)  # Update every minute

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(10)

    async def _cleanup_loop(self) -> None:
        """Cleanup old data."""
        self.logger.info("Starting cleanup loop")

        while not self._shutdown_event.is_set():
            try:
                # Clean old restart history (keep last 7 days)
                cutoff = datetime.now(timezone.utc) - timedelta(days=7)
                while self._restart_history and self._restart_history[0].timestamp < cutoff:
                    self._restart_history.popleft()

                # Run every hour
                await asyncio.sleep(3600)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in cleanup loop: {e}")
                await asyncio.sleep(60)

    async def _load_process_configs(self) -> None:
        """Load process configurations from file."""
        config_file = self.config.paths.config_path / "process_watchdog.json"

        if not config_file.exists():
            return

        try:
            async with aiofiles.open(config_file, 'r') as f:
                data = json.loads(await f.read())

            for process_data in data.get("processes", []):
                await self.register_process(**process_data)

            self.logger.info(f"Loaded {len(data.get('processes', []))} process configurations")

        except Exception as e:
            self.logger.error(f"Failed to load process configs: {e}")

    async def _save_process_states(self) -> None:
        """Save process states to file."""
        config_file = self.config.paths.config_path / "process_watchdog.json"

        try:
            data = {
                "processes": [],
                "stats": self._stats,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

            for name, process_info in self._processes.items():
                process_data = {
                    "name": name,
                    "command": process_info.command,
                    "working_dir": process_info.working_dir,
                    "env": process_info.env,
                    "auto_restart": process_info.auto_restart,
                    "restart_strategy": process_info.restart_strategy.value,
                    "max_restarts": process_info.max_restarts,
                    "health_checks": [c.value for c in process_info.health_checks],
                    "metadata": process_info.metadata
                }
                data["processes"].append(process_data)

            # Ensure directory exists
            config_file.parent.mkdir(parents=True, exist_ok=True)

            async with aiofiles.open(config_file, 'w') as f:
                await f.write(json.dumps(data, indent=2))

            self.logger.info("Saved process states")

        except Exception as e:
            self.logger.error(f"Failed to save process states: {e}")

    def get_statistics(self) -> Dict[str, Any]:
        """Get watchdog statistics.

        Returns:
            Statistics dictionary
        """
        return {
            **self._stats,
            "monitored_processes": len(self._processes),
            "running_processes": len([
                p for p in self._processes.values()
                if p.status == ProcessStatus.RUNNING
            ]),
            "restart_history_size": len(self._restart_history)
        }


# Global instance
_process_watchdog: Optional[ProcessWatchdog] = None


def get_process_watchdog() -> ProcessWatchdog:
    """Get global process watchdog instance."""
    global _process_watchdog
    if _process_watchdog is None:
        _process_watchdog = ProcessWatchdog()
    return _process_watchdog


async def initialize_process_watchdog() -> None:
    """Initialize the global process watchdog."""
    watchdog = get_process_watchdog()
    await watchdog.initialize()


# Decorator for process monitoring
def monitor_process(
    name: str,
    auto_restart: bool = True,
    restart_strategy: RestartStrategy = RestartStrategy.EXPONENTIAL_BACKOFF,
    max_restarts: int = 5,
    **kwargs
):
    """Decorator to monitor a function as a process.

    Args:
        name: Process name
        auto_restart: Whether to auto-restart
        restart_strategy: Restart strategy
        max_restarts: Maximum restarts
        **kwargs: Additional process configuration
    """
    def decorator(func: Callable):
        async def wrapper(*args, **_kwargs):
            watchdog = get_process_watchdog()

            # Register process
            command = [func.__module__, func.__name__]
            await watchdog.register_process(
                name=name,
                command=command,
                auto_restart=auto_restart,
                restart_strategy=restart_strategy,
                max_restarts=max_restarts,
                **kwargs
            )

            # Start the function
            return await func(*args, **_kwargs)

        return wrapper
    return decorator