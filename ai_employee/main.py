"""
AI Employee System - Main Application Entry Point

Fully autonomous business operations assistant for small businesses.
Handles invoicing, payments, social media, and CEO reporting.
"""

import asyncio
import logging
import signal
import sys
import json
import click
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, Dict, Any, List

from ai_employee.core.config import get_config, reload_config
from ai_employee.core.environment import validate_environment, EnvironmentValidationError
from ai_employee.utils.logging_config import setup_logging, setup_file_logging
from ai_employee.core.event_bus import get_event_bus, start_event_bus
from ai_employee.core.workflow_engine import get_workflow_engine
from ai_employee.utils.file_monitor import get_file_monitor
from ai_employee.utils.approval_system import get_approval_system
from ai_employee.utils.health_monitor import get_health_monitor, initialize_health_monitor
from ai_employee.utils.error_recovery import ErrorRecoveryService
from ai_employee.utils.process_watchdog import ProcessWatchdog
from ai_employee.utils.cleanup_manager import get_cleanup_manager, initialize_cleanup_manager
from ai_employee.core.circuit_breaker import CircuitBreaker, CircuitBreakerConfig
from ai_employee.domains.invoicing.services import InvoiceService
from ai_employee.domains.payments.services import PaymentService
from ai_employee.integrations.email_service import get_email_service

logger = logging.getLogger(__name__)


class AIEmployeeSystem:
    """Main AI Employee system application."""

    def __init__(self):
        """Initialize the AI Employee system."""
        self.config = None
        self.running = False
        self.event_bus = get_event_bus()
        self.workflow_engine = get_workflow_engine()
        self.file_monitor = get_file_monitor()
        self.approval_system = get_approval_system()
        self.health_monitor = get_health_monitor()
        self.process_watchdog = ProcessWatchdog()
        self.cleanup_manager = get_cleanup_manager()

    async def initialize(self, env_file: Optional[str] = None) -> None:
        """Initialize the system.

        Args:
            env_file: Optional path to .env file

        Raises:
            EnvironmentValidationError: If environment validation fails
        """
        try:
            # Validate environment
            logger.info("Validating environment configuration...")
            env_vars = validate_environment(env_file)

            # Load configuration
            logger.info("Loading system configuration...")
            self.config = get_config()

            # Setup logging
            logger.info("Setting up logging...")
            await self._setup_logging()

            # Setup directories
            logger.info("Setting up directories...")
            await self._setup_directories()

            # Initialize core components
            logger.info("Initializing core components...")
            await self._initialize_components()

            logger.info("AI Employee system initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize system: {e}", exc_info=True)
            raise

    async def _setup_logging(self) -> None:
        """Setup logging configuration."""
        # Setup basic logging
        setup_logging(
            log_level=self.config.log_level,
            enable_console=True,
            enable_json=self.config.environment == "production"
        )

        # Setup file-based logging
        log_files = setup_file_logging(
            base_path=self.config.paths.logs_path,
            retention_days=self.config.data_retention_days
        )

        logger.info(f"Logging configured - Files: {list(log_files.keys())}")

    async def _setup_directories(self) -> None:
        """Setup required directories."""
        directories = [
            self.config.paths.vault_path,
            self.config.paths.inbox_path,
            self.config.paths.needs_action_path,
            self.config.paths.pending_approval_path,
            self.config.paths.approved_path,
            self.config.paths.rejected_path,
            self.config.paths.done_path,
            self.config.paths.logs_path,
            self.config.paths.reports_path,
            self.config.paths.archive_path,
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Ensured directory exists: {directory}")

    async def _initialize_components(self) -> None:
        """Initialize core system components."""
        # Start event bus background processing
        await self.event_bus.start_background_processing()

        # Initialize health monitor
        logger.info("Initializing health monitoring system...")
        await self.health_monitor.initialize()

        # Initialize error recovery with circuit breaker
        logger.info("Initializing error recovery system...")
        config = CircuitBreakerConfig(
            failure_threshold=5,
            recovery_timeout=60,
            expected_exception=Exception
        )
        circuit_breaker = CircuitBreaker(
            name="main_circuit_breaker",
            config=config
        )
        self.error_recovery = ErrorRecoveryService(
            circuit_breaker=circuit_breaker,
            config=self.config
        )
        await self.error_recovery.initialize()

        # Initialize process watchdog
        logger.info("Initializing process watchdog...")
        await self.process_watchdog.initialize()

        # Initialize cleanup manager
        logger.info("Initializing cleanup manager...")
        await self.cleanup_manager.start()

        # Start file monitoring
        monitor_paths = [
            self.config.paths.inbox_path,
            self.config.paths.needs_action_path,
            self.config.paths.pending_approval_path,
            self.config.paths.approved_path,
            self.config.paths.rejected_path,
        ]

        await self.file_monitor.start_monitoring(monitor_paths)

        logger.info("Core components initialized")

    async def start(self) -> None:
        """Start the AI Employee system."""
        if self.running:
            logger.warning("System is already running")
            return

        try:
            self.running = True
            logger.info("Starting AI Employee system...")

            # Start main monitoring loop
            await self._run_main_loop()

        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        except Exception as e:
            logger.error(f"System error: {e}", exc_info=True)
        finally:
            await self.shutdown()

    async def _run_main_loop(self) -> None:
        """Run the main application loop."""
        logger.info("AI Employee system is running")

        while self.running:
            try:
                # Monitor approval requests
                await self._monitor_approvals()

                # Cleanup expired items
                await self._cleanup_expired_items()

                # Wait before next iteration
                await asyncio.sleep(60)  # Check every minute

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                await asyncio.sleep(5)  # Brief pause before retry

    async def _monitor_approvals(self) -> None:
        """Monitor approval requests for status updates."""
        try:
            # Get pending requests
            pending_requests = await self.approval_system.get_pending_requests()

            if pending_requests:
                logger.debug(f"Checking {len(pending_requests)} pending approval requests")

                # Check each request
                for request in pending_requests:
                    updated_request = await self.approval_system.check_approval_status(request.request_id)

                    if updated_request and updated_request.status.value != "pending":
                        logger.info(f"Approval request {request.request_id} status: {updated_request.status.value}")

        except Exception as e:
            logger.error(f"Error monitoring approvals: {e}")

    async def _cleanup_expired_items(self) -> None:
        """Cleanup expired approval requests and old files."""
        try:
            # Cleanup expired approvals
            expired_count = await self.approval_system.cleanup_expired_requests()
            if expired_count > 0:
                logger.info(f"Cleaned up {expired_count} expired approval requests")

            # Cleanup old files (could be implemented here)
            # This would involve checking file ages and moving to archive

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    # API Endpoints
    async def create_invoice(self, invoice_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create invoice API endpoint.

        Args:
            invoice_data: Invoice data

        Returns:
            Created invoice data
        """
        try:
            invoice_service = InvoiceService(
                email_service=get_email_service(),
                approval_system=self.approval_system
            )

            invoice = await invoice_service.create_invoice(invoice_data)
            return invoice.to_dict()

        except Exception as e:
            logger.error(f"API error creating invoice: {e}")
            return {"error": str(e), "status": "error"}

    async def get_invoice(self, invoice_id: str) -> Dict[str, Any]:
        """Get invoice API endpoint.

        Args:
            invoice_id: Invoice ID

        Returns:
            Invoice data
        """
        try:
            invoice_service = InvoiceService()
            status = await invoice_service.get_invoice_status(invoice_id)
            return status

        except Exception as e:
            logger.error(f"API error getting invoice {invoice_id}: {e}")
            return {"error": str(e), "status": "error"}

    async def list_invoices(
        self,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """List invoices API endpoint.

        Args:
            status: Filter by status
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of invoices
        """
        try:
            invoice_service = InvoiceService()
            filters = {}
            if status:
                filters["status"] = status

            invoices = await invoice_service.list_invoices(filters)
            return {
                "invoices": [inv.to_dict() for inv in invoices],
                "total": len(invoices),
                "limit": limit,
                "offset": offset
            }

        except Exception as e:
            logger.error(f"API error listing invoices: {e}")
            return {"error": str(e), "status": "error"}

    async def post_invoice(self, invoice_id: str) -> Dict[str, Any]:
        """Post invoice API endpoint.

        Args:
            invoice_id: Invoice ID

        Returns:
            Post result
        """
        try:
            invoice_service = InvoiceService(
                email_service=get_email_service(),
                approval_system=self.approval_system
            )

            success = await invoice_service.post_invoice(invoice_id)
            return {"success": success, "invoice_id": invoice_id}

        except Exception as e:
            logger.error(f"API error posting invoice {invoice_id}: {e}")
            return {"error": str(e), "status": "error"}

    async def create_payment(self, payment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create payment API endpoint.

        Args:
            payment_data: Payment data

        Returns:
            Created payment data
        """
        try:
            payment_service = PaymentService(
                bank_service=None,  # Would be initialized
                approval_system=self.approval_system
            )

            # Create bank transaction from payment data
            transaction_data = {
                "amount": payment_data["amount"],
                "date": payment_data["payment_date"],
                "reference": payment_data.get("bank_reference", ""),
                "description": payment_data.get("description", "")
            }

            # Process transaction to create payment
            payments = await payment_service.process_bank_transactions()

            # Return first payment if any were created
            if payments:
                return payments[0].to_dict()

            return {"error": "No payment created", "status": "no_match"}

        except Exception as e:
            logger.error(f"API error creating payment: {e}")
            return {"error": str(e), "status": "error"}

    async def get_payment(self, payment_id: str) -> Dict[str, Any]:
        """Get payment API endpoint.

        Args:
            payment_id: Payment ID

        Returns:
            Payment data
        """
        try:
            payment_service = PaymentService()
            status = await payment_service.get_payment_status(payment_id)
            return status

        except Exception as e:
            logger.error(f"API error getting payment {payment_id}: {e}")
            return {"error": str(e), "status": "error"}

    async def list_payments(
        self,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """List payments API endpoint.

        Args:
            status: Filter by status
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of payments
        """
        try:
            payment_service = PaymentService()
            filters = {}
            if status:
                filters["status"] = status

            payments = await payment_service.list_payments(filters)
            return {
                "payments": [payment.to_dict() for payment in payments],
                "total": len(payments),
                "limit": limit,
                "offset": offset
            }

        except Exception as e:
            logger.error(f"API error listing payments: {e}")
            return {"error": str(e), "status": "error"}

    async def reconcile_payment(self, payment_id: str) -> Dict[str, Any]:
        """Reconcile payment API endpoint.

        Args:
            payment_id: Payment ID

        Returns:
            Reconciliation result
        """
        try:
            payment_service = PaymentService()
            success = await payment_service.reconcile_payment(payment_id)
            return {"success": success, "payment_id": payment_id}

        except Exception as e:
            logger.error(f"API error reconciling payment {payment_id}: {e}")
            return {"error": str(e), "status": "error"}

    async def process_bank_transactions(self) -> Dict[str, Any]:
        """Process bank transactions API endpoint.

        Returns:
            Processing results
        """
        try:
            payment_service = PaymentService(
                bank_service=None,  # Would be initialized
                approval_system=self.approval_system
            )

            payments = await payment_service.process_bank_transactions()
            return {
                "processed_count": len(payments),
                "payments": [payment.to_dict() for payment in payments]
            }

        except Exception as e:
            logger.error(f"API error processing bank transactions: {e}")
            return {"error": str(e), "status": "error"}

    # Social Media API Endpoints
    async def social_media_post(self, platform: str, content: str, content_type: str = "text",
                               tags: Optional[List[str]] = None, engagement_goals: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Post content to social media platform.

        Args:
            platform: Platform to post to (twitter, facebook, instagram, linkedin)
            content: Content to post
            content_type: Type of content (text, image, video, link)
            tags: Optional tags for the post
            engagement_goals: Optional engagement goals

        Returns:
            Post result
        """
        try:
            from ai_employee.integrations.social_platforms import UnifiedSocialClient
            from ai_employee.domains.social_media import Platform

            # Initialize social client if needed
            social_client = UnifiedSocialClient()
            await social_client.initialize()

            # Map platform string to Platform enum
            platform_map = {
                "twitter": Platform.TWITTER,
                "facebook": Platform.FACEBOOK,
                "instagram": Platform.INSTAGRAM,
                "linkedin": Platform.LINKEDIN
            }

            platform_enum = platform_map.get(platform.lower())
            if not platform_enum:
                return {"error": f"Unsupported platform: {platform}", "status": "error"}

            # Post content
            result = await social_client.create_and_post(
                platforms=[platform_enum],
                content=content,
                content_type=content_type,
                tags=tags,
                engagement_goals=engagement_goals
            )

            return {
                "success": True,
                "post_id": result.get(platform_enum),
                "platform": platform
            }

        except Exception as e:
            logger.error(f"API error posting to social media: {e}")
            return {"error": str(e), "status": "error"}

    async def social_media_schedule(self, platform: str, content: str, scheduled_time: str,
                                   content_type: str = "text", tags: Optional[List[str]] = None,
                                   engagement_goals: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Schedule content for future posting on social media.

        Args:
            platform: Platform to schedule on
            content: Content to schedule
            scheduled_time: ISO format datetime string
            content_type: Type of content
            tags: Optional tags
            engagement_goals: Optional engagement goals

        Returns:
            Schedule result
        """
        try:
            from ai_employee.integrations.social_platforms import UnifiedSocialClient
            from ai_employee.domains.social_media import Platform
            from datetime import datetime

            # Initialize social client
            social_client = UnifiedSocialClient()
            await social_client.initialize()

            # Parse scheduled time
            schedule_dt = datetime.fromisoformat(scheduled_time)

            # Map platform
            platform_map = {
                "twitter": Platform.TWITTER,
                "facebook": Platform.FACEBOOK,
                "instagram": Platform.INSTAGRAM,
                "linkedin": Platform.LINKEDIN
            }

            platform_enum = platform_map.get(platform.lower())
            if not platform_enum:
                return {"error": f"Unsupported platform: {platform}", "status": "error"}

            # Schedule content
            schedule_id = await social_client.schedule_content(
                platforms=[platform_enum],
                content=content,
                content_type=content_type,
                scheduled_time=schedule_dt,
                tags=tags,
                engagement_goals=engagement_goals
            )

            return {
                "success": True,
                "schedule_id": schedule_id,
                "scheduled_time": schedule_dt.isoformat(),
                "platform": platform
            }

        except Exception as e:
            logger.error(f"API error scheduling social media content: {e}")
            return {"error": str(e), "status": "error"}

    async def social_media_get_mentions(self, platform: Optional[str] = None) -> Dict[str, Any]:
        """Get brand mentions from social media platforms.

        Args:
            platform: Optional platform to filter by

        Returns:
            List of mentions
        """
        try:
            from ai_employee.integrations.social_platforms import UnifiedSocialClient

            social_client = UnifiedSocialClient()
            await social_client.initialize()

            mentions = await social_client.monitor_brand_mentions()

            # Filter by platform if specified
            if platform:
                mentions = [m for m in mentions if m.platform.value == platform.lower()]

            return {
                "mentions": [
                    {
                        "platform": m.platform.value,
                        "content": m.content,
                        "author": m.author,
                        "timestamp": m.timestamp.isoformat(),
                        "engagement_score": m.engagement_score,
                        "sentiment_score": m.sentiment_score or 0.5
                    }
                    for m in mentions
                ],
                "total": len(mentions)
            }

        except Exception as e:
            logger.error(f"API error getting social media mentions: {e}")
            return {"error": str(e), "status": "error"}

    async def social_media_platform_status(self) -> Dict[str, Any]:
        """Get status of social media platforms.

        Returns:
            Platform status information
        """
        try:
            from ai_employee.integrations.social_platforms import UnifiedSocialClient

            social_client = UnifiedSocialClient()
            await social_client.initialize()

            status = await social_client.get_platform_status()

            return status

        except Exception as e:
            logger.error(f"API error getting social media platform status: {e}")
            return {"error": str(e), "status": "error"}

    async def validate_financial_operation(self, operation: str, amount: float, **kwargs) -> Dict[str, Any]:
        """Validate financial operation rules.

        Args:
            operation: Type of operation
            amount: Amount involved
            **kwargs: Additional parameters

        Returns:
            Validation result
        """
        try:
            # Check amount threshold
            if amount > 500:
                return {
                    "valid": False,
                    "error": f"Amount ${amount} exceeds approval threshold of $500",
                    "requires_approval": True
                }

            # Check for suspicious patterns
            if "test" in str(kwargs).lower() or "demo" in str(kwargs).lower():
                return {
                    "valid": False,
                    "error": "Test/demo operations not allowed in production"
                }

            # Additional validation rules can be added here
            return {"valid": True}

        except Exception as e:
            logger.error(f"Error validating financial operation: {e}")
            return {"valid": False, "error": str(e)}

    def log_audit_trail(self, action: str, user: str, details: Dict[str, Any]) -> None:
        """Log audit trail entry.

        Args:
            action: Action performed
            user: User who performed action
            details: Additional details
        """
        audit_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "user": user,
            "details": details
        }

        logger.info(f"AUDIT: {json.dumps(audit_entry)}")

    def error_recovery_action(self, error: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Perform error recovery action.

        Args:
            error: Error message
            context: Error context

        Returns:
            Recovery action result
        """
        logger.error(f"ERROR RECOVERY: {error} - Context: {context}")

        # Categorize error and take appropriate action
        if "email" in error.lower():
            return {
                "action": "queue_email",
                "retry_after": 60,   # 1 minute
                "max_retries": 5
            }
        elif "timeout" in error.lower():
            return {
                "action": "increase_timeout",
                "factor": 2.0,
                "max_timeout": 300
            }
        else:
            return {
                "action": "log_and_continue",
                "escalate": False
            }

    async def shutdown(self) -> None:
        """Shutdown the AI Employee system."""
        if not self.running:
            return

        logger.info("Shutting down AI Employee system...")
        self.running = False

        try:
            # Shutdown health monitor
            if hasattr(self, 'health_monitor'):
                await self.health_monitor.shutdown()

            # Shutdown error recovery
            if hasattr(self, 'error_recovery'):
                await self.error_recovery.shutdown()

            # Shutdown process watchdog
            if hasattr(self, 'process_watchdog'):
                await self.process_watchdog.stop()

            # Shutdown cleanup manager
            if hasattr(self, 'cleanup_manager'):
                await self.cleanup_manager.stop()

            # Stop file monitoring
            await self.file_monitor.stop_monitoring()

            # Stop event bus
            await self.event_bus.stop_background_processing()

            # Cleanup workflows
            await self.workflow_engine.cleanup_completed_workflows()

            logger.info("AI Employee system shutdown complete")

        except Exception as e:
            logger.error(f"Error during shutdown: {e}")

    async def get_health_check(self) -> Dict[str, Any]:
        """Get comprehensive health check status.

        Returns:
            Detailed health check information
        """
        try:
            if not hasattr(self, 'health_monitor'):
                return {
                    "status": "unavailable",
                    "error": "Health monitor not initialized",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }

            # Get comprehensive health report
            health_report = await self.health_monitor.generate_health_report()

            # Get current alerts
            active_alerts = await self.health_monitor.get_active_alerts()

            # Get system metrics
            current_metrics = await self.health_monitor.get_current_metrics()

            # Check component health
            component_health = {}

            # Event bus health
            try:
                event_bus_stats = self.event_bus.get_statistics()
                component_health["event_bus"] = {
                    "status": "healthy" if event_bus_stats.get("events_processed", 0) >= 0 else "unhealthy",
                    "events_processed": event_bus_stats.get("events_processed", 0),
                    "active_subscriptions": event_bus_stats.get("active_subscriptions", 0)
                }
            except Exception as e:
                component_health["event_bus"] = {
                    "status": "unhealthy",
                    "error": str(e)
                }

            # Workflow engine health
            try:
                workflow_stats = self.workflow_engine.get_all_status()
                running_workflows = len([w for w in workflow_stats.values() if w.get("status") == "running"])
                component_health["workflow_engine"] = {
                    "status": "healthy",
                    "total_workflows": len(workflow_stats),
                    "running_workflows": running_workflows
                }
            except Exception as e:
                component_health["workflow_engine"] = {
                    "status": "unhealthy",
                    "error": str(e)
                }

            # File monitor health
            try:
                monitor_stats = await self.file_monitor.get_statistics()
                component_health["file_monitor"] = {
                    "status": "healthy" if self.file_monitor.is_monitoring else "stopped",
                    "files_processed": monitor_stats.get("files_processed", 0),
                    "monitoring_active": self.file_monitor.is_monitoring
                }
            except Exception as e:
                component_health["file_monitor"] = {
                    "status": "unhealthy",
                    "error": str(e)
                }

            # Error recovery health
            if hasattr(self, 'error_recovery'):
                try:
                    error_stats = await self.error_recovery.get_statistics()
                    component_health["error_recovery"] = {
                        "status": "healthy",
                        "total_errors": error_stats.get("total_errors", 0),
                        "resolved_errors": error_stats.get("resolved_errors", 0),
                        "pending_retries": error_stats.get("pending_retries", 0)
                    }
                except Exception as e:
                    component_health["error_recovery"] = {
                        "status": "unhealthy",
                        "error": str(e)
                    }

            return {
                "status": health_report.overall_status.value,
                "timestamp": health_report.timestamp.isoformat(),
                "uptime": health_report.uptime_seconds,
                "checks": {
                    check.name: {
                        "status": check.status.value,
                        "last_check": check.last_check.isoformat() if check.last_check else None,
                        "message": check.message,
                        "response_time_ms": check.response_time_ms
                    }
                    for check in health_report.checks
                },
                "metrics": {
                    name: {
                        "value": metric.value,
                        "unit": metric.unit,
                        "timestamp": metric.timestamp.isoformat()
                    }
                    for name, metric in current_metrics.items()
                },
                "alerts": [
                    {
                        "level": alert.level.value,
                        "message": alert.message,
                        "timestamp": alert.timestamp.isoformat(),
                        "acknowledged": alert.acknowledged
                    }
                    for alert in active_alerts
                ],
                "components": component_health,
                "summary": {
                    "total_checks": len(health_report.checks),
                    "healthy_checks": len([c for c in health_report.checks if c.status.value == "healthy"]),
                    "unhealthy_checks": len([c for c in health_report.checks if c.status.value == "unhealthy"]),
                    "active_alerts": len(active_alerts),
                    "critical_alerts": len([a for a in active_alerts if a.level.value == "critical"])
                }
            }

        except Exception as e:
            logger.error(f"Error in health check API: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

    async def get_status(self) -> dict:
        """Get system status.

        Returns:
            System status dictionary
        """
        try:
            # Get component statistics
            event_bus_stats = self.event_bus.get_statistics()
            workflow_stats = self.workflow_engine.get_all_status()
            monitor_stats = await self.file_monitor.get_statistics()
            approval_stats = await self.approval_system.get_statistics()

            # Get health status if available
            health_status = "unknown"
            if hasattr(self, 'health_monitor'):
                try:
                    health_report = await self.health_monitor.generate_health_report()
                    health_status = health_report.overall_status.value
                except Exception as e:
                    logger.error(f"Error getting health status: {e}")

            return {
                "running": self.running,
                "environment": self.config.environment,
                "uptime": "Running",  # Could track actual uptime
                "health_status": health_status,
                "components": {
                    "event_bus": event_bus_stats,
                    "workflows": {
                        "total": len(workflow_stats),
                        "running": len([w for w in workflow_stats.values() if w["status"] == "running"]),
                        "completed": len([w for w in workflow_stats.values() if w["status"] == "completed"]),
                        "failed": len([w for w in workflow_stats.values() if w["status"] == "failed"])
                    },
                    "file_monitor": monitor_stats,
                    "approval_system": approval_stats,
                    "health_monitor": {
                        "status": health_status
                    }
                }
            }

        except Exception as e:
            logger.error(f"Error getting system status: {e}")
            return {"error": str(e), "running": self.running}


# Global system instance
ai_system = AIEmployeeSystem()


async def main(env_file: Optional[str] = None) -> None:
    """Main application entry point.

    Args:
        env_file: Optional path to .env file
    """
    # Setup signal handlers
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}")
        asyncio.create_task(ai_system.shutdown())

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # Initialize and start system
        await ai_system.initialize(env_file)
        await ai_system.start()

    except EnvironmentValidationError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


@click.command()
@click.option('--env-file', '-e', help='Path to .env file')
@click.option('--config-check', is_flag=True, help='Check configuration and exit')
@click.option('--status', is_flag=True, help='Show system status')
@click.option('--health-check', is_flag=True, help='Show detailed health check')
@click.option('--generate-env', help='Generate .env template file')
def cli(env_file: Optional[str], config_check: bool, status: bool, health_check: bool, generate_env: Optional[str]) -> None:
    """AI Employee System - Autonomous Business Operations Assistant"""
    if generate_env:
        from ai_employee.core.environment import generate_env_template
        template = generate_env_template(generate_env)
        if generate_env:
            print(f"Generated .env template: {generate_env}")
        else:
            print(template)
        return

    if config_check:
        try:
            validate_environment(env_file)
            print("✅ Configuration is valid")
        except EnvironmentValidationError as e:
            print(f"❌ Configuration error:\n{e}")
            sys.exit(1)
        return

    if status:
        async def show_status():
            try:
                await ai_system.initialize(env_file)
                status_data = await ai_system.get_status()
                import json
                print(json.dumps(status_data, indent=2))
            except Exception as e:
                print(f"Error: {e}")
                sys.exit(1)

        asyncio.run(show_status())
        return

    if health_check:
        async def show_health_check():
            try:
                await ai_system.initialize(env_file)
                health_data = await ai_system.get_health_check()
                import json
                print(json.dumps(health_data, indent=2))
            except Exception as e:
                print(f"Error: {e}")
                sys.exit(1)

        asyncio.run(show_health_check())
        return

    # Run main application
    asyncio.run(main(env_file))


if __name__ == "__main__":
    import click
    cli()