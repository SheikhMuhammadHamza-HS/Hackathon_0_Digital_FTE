"""
Example configuration and usage of the Process Watchdog system.

This example demonstrates how to configure and use the process watchdog
to monitor critical system processes with different restart strategies
and health checks.
"""

import asyncio
from pathlib import Path
from typing import Dict, Any

from utils.process_watchdog import (
    ProcessWatchdog, ProcessStatus, RestartStrategy, HealthCheckType,
    BackoffConfig, monitor_process
)
from utils.logging_config import configure_logging, get_logger
from core.config import get_config

logger = get_logger(__name__)


class CriticalSystemProcesses:
    """Configuration for critical system processes that need monitoring."""

    def __init__(self, watchdog: ProcessWatchdog):
        self.watchdog = watchdog

    async def register_all(self):
        """Register all critical processes."""
        await self.register_database_process()
        await self.register_web_server()
        await self.register_queue_worker()
        await self.register_scheduler()
        await self.register_cleanup_service()

    async def register_database_process(self):
        """Register database connection pool process."""
        # Example: PostgreSQL connection pool manager
        await self.watchdog.register_process(
            name="db_connection_pool",
            command=["python", "-m", "ai_employee.services.db_pool_manager"],
            working_dir=str(Path.cwd()),
            env={
                "DB_HOST": "localhost",
                "DB_PORT": "5432",
                "DB_NAME": "ai_employee",
                "POOL_SIZE": "20"
            },
            auto_restart=True,
            restart_strategy=RestartStrategy.IMMEDIATE,
            max_restarts=5,
            health_checks=[HealthCheckType.HEARTBEAT, HealthCheckType.MEMORY_USAGE],
            backoff_config=BackoffConfig(
                strategy=RestartStrategy.EXPONENTIAL_BACKOFF,
                base_delay=2.0,
                max_delay=60.0,
                multiplier=2.0,
                jitter=True
            ),
            critical=True
        )

    async def register_web_server(self):
        """Register web server process."""
        # Example: FastAPI web server
        await self.watchdog.register_process(
            name="web_server",
            command=["uvicorn", "ai_employee.api.main:app", "--host", "0.0.0.0", "--port", "8000"],
            env={
                "WORKERS": "4",
                "WORKER_CLASS": "uvicorn.workers.UvicornWorker"
            },
            auto_restart=True,
            restart_strategy=RestartStrategy.FIXED_INTERVAL,
            max_restarts=10,
            health_checks=[
                HealthCheckType.HEARTBEAT,
                HealthCheckType.CPU_USAGE,
                HealthCheckType.RESPONSE_TIME
            ],
            backoff_config=BackoffConfig(
                strategy=RestartStrategy.FIXED_INTERVAL,
                base_delay=5.0,
                max_delay=30.0
            ),
            port=8000,
            endpoint="/health"
        )

    async def register_queue_worker(self):
        """Register message queue worker process."""
        # Example: Celery/Redis worker
        await self.watchdog.register_process(
            name="queue_worker",
            command=["celery", "-A", "ai_employee.tasks.celery_app", "worker", "--loglevel=info"],
            auto_restart=True,
            restart_strategy=RestartStrategy.EXPONENTIAL_BACKOFF,
            max_restarts=3,
            health_checks=[HealthCheckType.HEARTBEAT, HealthCheckType.MEMORY_USAGE],
            backoff_config=BackoffConfig(
                strategy=RestartStrategy.EXPONENTIAL_BACKOFF,
                base_delay=1.0,
                max_delay=120.0,
                multiplier=1.5
            ),
            max_tasks_per_child=1000,
            prefetch_multiplier=1
        )

    async def register_scheduler(self):
        """Register task scheduler process."""
        # Example: APScheduler service
        await self.watchdog.register_process(
            name="task_scheduler",
            command=["python", "-m", "ai_employee.services.scheduler"],
            auto_restart=True,
            restart_strategy=RestartStrategy.LINEAR_BACKOFF,
            max_restarts=3,
            health_checks=[HealthCheckType.HEARTBEAT],
            backoff_config=BackoffConfig(
                strategy=RestartStrategy.LINEAR_BACKOFF,
                base_delay=5.0,
                max_delay=60.0
            ),
            timezone="UTC",
            max_instances=3
        )

    async def register_cleanup_service(self):
        """Register cleanup service process."""
        # Example: Periodic cleanup service
        await self.watchdog.register_process(
            name="cleanup_service",
            command=["python", "-m", "ai_employee.services.cleanup"],
            auto_restart=True,
            restart_strategy=RestartStrategy.EXPONENTIAL_BACKOFF,
            max_restarts=2,
            health_checks=[HealthCheckType.HEARTBEAT],
            interval_hours=24,
            retention_days=7
        )


class BackgroundServices:
    """Configuration for background services."""

    def __init__(self, watchdog: ProcessWatchdog):
        self.watchdog = watchdog

    async def register_all(self):
        """Register all background services."""
        await self.register_file_processor()
        await self.register_notification_service()
        await self.register_monitoring_service()

    async def register_file_processor(self):
        """Register file processing service."""
        await self.watchdog.register_process(
            name="file_processor",
            command=["python", "-m", "ai_employee.services.file_processor"],
            auto_restart=True,
            restart_strategy=RestartStrategy.EXPONENTIAL_BACKOFF,
            max_restarts=3,
            health_checks=[HealthCheckType.CPU_USAGE, HealthCheckType.MEMORY_USAGE],
            monitored_directories=["/tmp/inbox", "/tmp/processing"],
            batch_size=100,
            timeout_seconds=300
        )

    async def register_notification_service(self):
        """Register notification service."""
        await self.watchdog.register_process(
            name="notification_service",
            command=["python", "-m", "ai_employee.services.notifications"],
            auto_restart=False,  # Manual restart for notifications
            restart_strategy=RestartStrategy.NO_RESTART,
            max_restarts=0,
            health_checks=[HealthCheckType.HEARTBEAT],
            providers=["email", "sms", "webhook"],
            max_retries=3
        )

    async def register_monitoring_service(self):
        """Register monitoring/metrics service."""
        await self.watchdog.register_process(
            name="monitoring_service",
            command=["python", "-m", "ai_employee.services.monitoring"],
            auto_restart=True,
            restart_strategy=RestartStrategy.IMMEDIATE,
            max_restarts=5,
            health_checks=[HealthCheckType.HEARTBEAT],
            metrics_port=9090,
            prometheus_enabled=True
        )


class DevelopmentServices:
    """Development-specific services."""

    def __init__(self, watchdog: ProcessWatchdog):
        self.watchdog = watchdog

    async def register_all(self):
        """Register development services."""
        await self.register_mock_apis()
        await self.register_test_runner()

    async def register_mock_apis(self):
        """Register mock API servers for testing."""
        await self.watchdog.register_process(
            name="mock_payment_api",
            command=["python", "-m", "ai_employee.tests.mocks.payment_api"],
            auto_restart=True,
            restart_strategy=RestartStrategy.IMMEDIATE,
            max_restarts=999,  # Unlimited in development
            health_checks=[HealthCheckType.CUSTOM_ENDPOINT],
            endpoint="http://localhost:8001/health",
            debug=True
        )

    async def register_test_runner(self):
        """Register continuous test runner."""
        await self.watchdog.register_process(
            name="test_runner",
            command=["python", "-m", "ai_employee.tests.watch_runner"],
            auto_restart=True,
            restart_strategy=RestartStrategy.LINEAR_BACKOFF,
            max_restarts=3,
            test_dirs=["tests/unit", "tests/integration"],
            watch_patterns=["*.py"],
            poll_interval=2
        )


@monitor_process(
    name="example_service",
    auto_restart=True,
    restart_strategy=RestartStrategy.EXPONENTIAL_BACKOFF,
    max_restarts=3
)
async def example_monitored_service():
    """Example of using the monitor_process decorator."""
    logger.info("Starting monitored service")

    try:
        while True:
            # Do some work
            await asyncio.sleep(5)
            logger.debug("Service heartbeat")
    except asyncio.CancelledError:
        logger.info("Service shutting down")
        raise
    except Exception as e:
        logger.error(f"Service error: {e}")
        raise


async def setup_watchdog():
    """Setup and configure the process watchdog."""
    # Configure logging
    configure_logging()

    # Get configuration
    config = get_config()

    # Create watchdog instance
    watchdog = ProcessWatchdog(config=config)

    # Initialize
    await watchdog.initialize()

    # Register all processes based on environment
    environment = config.environment if hasattr(config, 'environment') else 'development'

    if environment == 'production':
        logger.info("Registering production processes")
        critical = CriticalSystemProcesses(watchdog)
        await critical.register_all()

        background = BackgroundServices(watchdog)
        await background.register_all()

    elif environment == 'staging':
        logger.info("Registering staging processes")
        critical = CriticalSystemProcesses(watchdog)
        await critical.register_all()

    else:  # development
        logger.info("Registering development processes")
        dev = DevelopmentServices(watchdog)
        await dev.register_all()

    return watchdog


async def monitor_dashboard(watchdog: ProcessWatchdog):
    """Simple monitoring dashboard."""
    while True:
        processes = await watchdog.get_all_processes()
        stats = watchdog.get_statistics()

        print("\n" + "=" * 60)
        print(f"Process Watchdog Dashboard - {stats['monitored_processes']} processes monitored")
        print(f"Running: {stats['running_processes']} | Total restarts: {stats['total_restarts']}")
        print("=" * 60)

        for name, info in processes.items():
            status_emoji = {
                ProcessStatus.RUNNING: "✅",
                ProcessStatus.STOPPED: "⏹️",
                ProcessStatus.CRASHED: "❌",
                ProcessStatus.RESTARTING: "🔄",
                ProcessStatus.DISABLED: "🚫"
            }.get(info.status, "❓")

            print(f"{status_emoji} {name:20} PID:{info.pid:6} {info.status.value:12} "
                  f"CPU:{info.cpu_percent:5.1f}% MEM:{info.memory_mb:6.1f}MB "
                  f"Restarts:{info.restart_count:2}")

        print("\nPress Ctrl+C to exit")
        await asyncio.sleep(10)


async def main():
    """Main entry point."""
    logger.info("Starting Process Watchdog Example")

    try:
        # Setup watchdog
        watchdog = await setup_watchdog()

        # Start monitoring dashboard
        await monitor_dashboard(watchdog)

    except KeyboardInterrupt:
        logger.info("Shutting down...")
        if 'watchdog' in locals():
            await watchdog.shutdown()
    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())