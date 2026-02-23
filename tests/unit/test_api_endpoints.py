"""Unit tests for API endpoints."""

import pytest
import json
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient

from ai_employee.api.server import app


class TestHealthEndpoint:
    """Test health check endpoint."""

    def setup_method(self):
        """Setup test client."""
        self.client = TestClient(app)

    def test_health_check_success(self):
        """Test successful health check."""
        response = self.client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "services" in data
        assert "version" in data

    @patch('ai_employee.api.server.scheduler')
    def test_health_check_with_scheduler_error(self, mock_scheduler):
        """Test health check when scheduler fails."""
        mock_scheduler.get_schedule_status.side_effect = Exception("Scheduler error")

        response = self.client.get("/api/v1/health")

        assert response.status_code == 500
        data = response.json()
        assert "error" in data
        assert "user_message" in data


class TestBriefingEndpoints:
    """Test briefing generation endpoints."""

    def setup_method(self):
        """Setup test client."""
        self.client = TestClient(app)

    @patch('ai_employee.api.server.report_service')
    def test_generate_briefing_success(self, mock_service):
        """Test successful briefing generation."""
        # Mock briefing data
        mock_briefing = Mock()
        mock_briefing.week_start = datetime(2026, 2, 17)
        mock_briefing.week_end = datetime(2026, 2, 23)
        mock_briefing.financial_summary = Mock()
        mock_briefing.financial_summary.total_revenue = 5000
        mock_briefing.operational_metrics = Mock()
        mock_briefing.operational_metrics.total_tasks_completed = 25
        mock_briefing.social_media_summary = Mock()
        mock_briefing.social_media_summary.total_engagements = 150
        mock_briefing.key_highlights = ["Revenue up 20%", "All tasks completed"]
        mock_briefing.strategic_insights = []
        mock_briefing.proactive_suggestions = []
        mock_briefing.subscription_audit = []
        mock_briefing.bottleneck_analysis = Mock()
        mock_briefing.bottleneck_analysis.areas = []
        mock_briefing.bottleneck_analysis.severity.value = "low"
        mock_briefing.bottleneck_analysis.impact_description = "No issues"
        mock_briefing.bottleneck_analysis.suggested_solutions = []

        mock_service.generate_weekly_briefing = AsyncMock(return_value=mock_briefing)

        response = self.client.post(
            "/api/v1/briefing",
            json={"format": "json", "include_recommendations": True}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "briefing" in data
        assert "period" in data

    def test_generate_briefing_invalid_format(self):
        """Test briefing generation with invalid format."""
        response = self.client.post(
            "/api/v1/briefing",
            json={"format": "invalid"}
        )

        assert response.status_code == 400
        data = response.json()
        assert "error" in data
        assert "Validation" in data["error"]
        assert "format" in data["details"]["field"]

    def test_generate_briefing_future_date(self):
        """Test briefing generation with future date."""
        future_date = (datetime.now() + timedelta(days=7)).isoformat()

        response = self.client.post(
            "/api/v1/briefing",
            json={"week_start": future_date}
        )

        assert response.status_code == 400
        data = response.json()
        assert "future" in data["user_message"].lower()


class TestHelpEndpoints:
    """Test help endpoints."""

    def setup_method(self):
        """Setup test client."""
        self.client = TestClient(app)

    def test_help_overview(self):
        """Test help overview endpoint."""
        response = self.client.get("/api/v1/help")

        assert response.status_code == 200
        data = response.json()
        assert "categories" in data
        assert "usage" in data
        assert "quick_links" in data

    def test_help_by_category(self):
        """Test getting help by category."""
        response = self.client.get("/api/v1/help?category=getting_started")

        assert response.status_code == 200
        data = response.json()
        assert "title" in data
        assert "sections" in data

    def test_help_invalid_category(self):
        """Test help with invalid category."""
        response = self.client.get("/api/v1/help?category=invalid")

        assert response.status_code == 400
        data = response.json()
        assert "error" in data
        assert "Validation" in data["error"]

    def test_help_search(self):
        """Test searching help content."""
        response = self.client.get("/api/v1/help?search=odoo")

        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "query" in data
        assert data["query"] == "odoo"

    def test_help_contextual(self):
        """Test contextual help for endpoint."""
        response = self.client.get("/api/v1/help?endpoint=/api/v1/briefing")

        assert response.status_code == 200
        data = response.json()
        assert "description" in data

    def test_setup_checklist(self):
        """Test setup checklist endpoint."""
        response = self.client.get("/api/v1/help/setup-checklist")

        assert response.status_code == 200
        data = response.json()
        assert "title" in data
        assert "sections" in data

    def test_error_help(self):
        """Test error help endpoint."""
        response = self.client.get("/api/v1/help/error?error=Missing%20API%20key")

        assert response.status_code == 200
        data = response.json()
        assert "category" in data
        assert "suggestions" in data


class TestPerformanceEndpoints:
    """Test performance monitoring endpoints."""

    def setup_method(self):
        """Setup test client."""
        self.client = TestClient(app)

    @patch('ai_employee.api.server.performance_monitor')
    def test_performance_metrics(self, mock_monitor):
        """Test performance metrics endpoint."""
        mock_monitor.get_metrics.return_value = [
            {
                "operation": "test_operation",
                "duration_ms": 100,
                "success": True
            }
        ]

        response = self.client.get("/api/v1/performance/metrics")

        assert response.status_code == 200
        data = response.json()
        assert "metrics" in data
        assert "total_count" in data

    @patch('ai_employee.api.server.performance_monitor')
    def test_performance_statistics(self, mock_monitor):
        """Test performance statistics endpoint."""
        mock_monitor.metrics = {"test_op": []}
        mock_monitor.get_statistics.return_value = {
            "operation": "test_op",
            "total_operations": 10,
            "success_rate": 90.0
        }

        response = self.client.get("/api/v1/performance/statistics")

        assert response.status_code == 200
        data = response.json()
        assert "operations" in data
        assert "summary" in data

    @patch('ai_employee.api.server.performance_monitor')
    def test_slow_operations(self, mock_monitor):
        """Test slow operations endpoint."""
        mock_monitor.get_slow_operations.return_value = [
            {
                "operation": "slow_operation",
                "duration_ms": 2000
            }
        ]

        response = self.client.get("/api/v1/performance/slow?threshold_ms=1000")

        assert response.status_code == 200
        data = response.json()
        assert "threshold_ms" in data
        assert data["threshold_ms"] == 1000
        assert "slow_operations" in data

    @patch('ai_employee.api.server.cache_manager')
    def test_cache_statistics(self, mock_cache):
        """Test cache statistics endpoint."""
        mock_cache.get_stats = AsyncMock(return_value={
            "total_entries": 100,
            "active_entries": 95,
            "expired_entries": 5
        })

        response = self.client.get("/api/v1/performance/cache")

        assert response.status_code == 200
        data = response.json()
        assert data["total_entries"] == 100
        assert data["active_entries"] == 95

    @patch('ai_employee.api.server.cache_manager')
    def test_clear_cache(self, mock_cache):
        """Test clear cache endpoint."""
        mock_cache.clear_expired = AsyncMock()

        response = self.client.post("/api/v1/performance/cache/clear")

        assert response.status_code == 200
        data = response.json()
        assert "message" in data


class TestErrorHandling:
    """Test API error handling."""

    def setup_method(self):
        """Setup test client."""
        self.client = TestClient(app)

    def test_404_error(self):
        """Test 404 error handling."""
        response = self.client.get("/api/v1/nonexistent")

        assert response.status_code == 404

    @patch('ai_employee.api.server.report_service')
    def test_integration_error_handling(self, mock_service):
        """Test integration error handling."""
        from ai_employee.utils.error_handlers import IntegrationError

        mock_service.generate_weekly_briefing = AsyncMock(
            side_effect=IntegrationError(
                "Odoo connection failed",
                service="Odoo"
            )
        )

        response = self.client.post("/api/v1/briefing")

        assert response.status_code == 400
        data = response.json()
        assert "error" in data
        assert "IntegrationError" in data["error"]
        assert "user_message" in data
        assert "suggestions" in data

    @patch('ai_employee.api.server.report_service')
    def test_validation_error_handling(self, mock_service):
        """Test validation error handling."""
        from ai_employee.utils.error_handlers import ValidationError

        mock_service.generate_weekly_briefing = AsyncMock(
            side_effect=ValidationError(
                "Invalid data format",
                field="amount",
                value="invalid"
            )
        )

        response = self.client.post("/api/v1/briefing")

        assert response.status_code == 400
        data = response.json()
        assert "ValidationError" in data["error"]
        assert "amount" in data["details"]["field"]

    def test_method_not_allowed(self):
        """Test method not allowed error."""
        response = self.client.delete("/api/v1/health")

        assert response.status_code == 405


class TestRootEndpoint:
    """Test root endpoint."""

    def setup_method(self):
        """Setup test client."""
        self.client = TestClient(app)

    def test_root_endpoint(self):
        """Test root endpoint returns API info."""
        response = self.client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data
        assert "endpoints" in data
        assert "AI Employee API" in data["message"]