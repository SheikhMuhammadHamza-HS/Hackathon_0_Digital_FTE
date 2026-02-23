"""Integration tests for data aggregation across domains."""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from ai_employee.domains.invoicing.models import Invoice
from ai_employee.domains.payments.models import Payment
from ai_employee.domains.social_media.models import SocialPost, BrandMention
from ai_employee.domains.reporting.services import ReportService


@pytest.fixture
def report_service():
    """Create ReportService instance for testing."""
    return ReportService()


@pytest.mark.asyncio
async def test_aggregate_invoice_data(report_service):
    """Test aggregation of invoice data for reporting."""
    # Create sample invoices
    invoices = [
        Invoice(
            id="INV-001",
            client_id="CLI-001",
            client_name="Tech Corp",
            amount=5000.0,
            status="paid",
            date_issued=datetime.now() - timedelta(days=10),
            date_due=datetime.now() - timedelta(days=5)
        ),
        Invoice(
            id="INV-002",
            client_id="CLI-002",
            client_name="Startup Inc",
            amount=7500.0,
            status="pending",
            date_issued=datetime.now() - timedelta(days=5),
            date_due=datetime.now() + timedelta(days=2)
        )
    ]

    aggregated = await report_service._aggregate_invoices(invoices)

    assert aggregated["total_value"] == 12500.0
    assert aggregated["paid_value"] == 5000.0
    assert aggregated["pending_value"] == 7500.0
    assert aggregated["paid_count"] == 1
    assert aggregated["pending_count"] == 1
    assert aggregated["avg_invoice_value"] == 6250.0


@pytest.mark.asyncio
async def test_aggregate_payment_data(report_service):
    """Test aggregation of payment data for reporting."""
    payments = [
        Payment(
            id="PAY-001",
            invoice_id="INV-001",
            amount=5000.0,
            status="matched",
            payment_date=datetime.now() - timedelta(days=8),
            reconciliation_status="completed"
        ),
        Payment(
            id="PAY-002",
            invoice_id="INV-003",
            amount=3000.0,
            status="unmatched",
            payment_date=datetime.now() - timedelta(days=3)
        )
    ]

    aggregated = await report_service._aggregate_payments(payments)

    assert aggregated["total_received"] == 8000.0
    assert aggregated["matched_amount"] == 5000.0
    assert aggregated["unmatched_amount"] == 3000.0
    assert aggregated["reconciliation_rate"] == 62.5  # 5000/8000 * 100


@pytest.mark.asyncio
async def test_aggregate_task_completion_data(report_service):
    """Test aggregation of task completion data."""
    # Create mock task data as dictionaries
    task_data = [
        {
            "id": "TASK-001",
            "title": "Create invoice for January",
            "status": "completed",
            "priority": "high",
            "due_date": (datetime.now() - timedelta(days=2)).isoformat(),
            "completed_at": (datetime.now() - timedelta(days=1)).isoformat()
        },
        {
            "id": "TASK-002",
            "title": "Process Q1 payments",
            "status": "in_progress",
            "priority": "medium",
            "due_date": (datetime.now() + timedelta(days=5)).isoformat()
        },
        {
            "id": "TASK-003",
            "title": "Update social media policy",
            "status": "completed",
            "priority": "low",
            "due_date": (datetime.now() - timedelta(days=10)).isoformat(),
            "completed_at": (datetime.now() - timedelta(days=8)).isoformat()
        }
    ]

    aggregated = await report_service._aggregate_task_data(task_data)

    assert aggregated["total_tasks"] == 3
    assert aggregated["completed_tasks"] == 2
    assert aggregated["in_progress_tasks"] == 1
    assert aggregated["completion_rate"] == 66.67  # 2/3 * 100
    assert len(aggregated["completed_this_week"]) == 1  # TASK-001


@pytest.mark.asyncio
async def test_aggregate_social_media_data(report_service):
    """Test aggregation of social media engagement data."""
    posts = [
        SocialPost(
            id="POST-001",
            platform="LinkedIn",
            content="Great week at the office!",
            status="published",
            publish_time=datetime.now() - timedelta(days=2),
            engagement_score=25.5
        ),
        SocialPost(
            id="POST-002",
            platform="Twitter",
            content="New blog post is live!",
            status="published",
            publish_time=datetime.now() - timedelta(days=1),
            engagement_score=42.3
        ),
        SocialPost(
            id="POST-003",
            platform="LinkedIn",
            content="Team achievements this month",
            status="published",
            publish_time=datetime.now() - timedelta(days=5),
            engagement_score=18.7
        )
    ]

    mentions = [
        BrandMention(
            id="MENTION-001",
            platform="Twitter",
            content="Great service from @company!",
            sentiment_score=0.85,
            engagement_score=12.4,
            timestamp=datetime.now() - timedelta(days=2)
        ),
        BrandMention(
            id="MENTION-002",
            platform="LinkedIn",
            content="Disappointed with the recent update",
            sentiment_score=0.25,
            engagement_score=8.2,
            timestamp=datetime.now() - timedelta(days=1)
        )
    ]

    aggregated = await report_service._aggregate_social_metrics(posts, mentions)

    assert aggregated["total_posts"] == 3
    assert aggregated["total_engagements"] == 66.5
    assert aggregated["avg_engagement_score"] == 22.17  # 66.5/3
    assert aggregated["mentions_count"] == 2
    assert aggregated["sentiment_score"] == 0.55  # (0.85 + 0.25)/2
    assert "LinkedIn" in aggregated["platform_breakdown"]
    assert "Twitter" in aggregated["platform_breakdown"]


@pytest.mark.asyncio
async def test_data_aggregation_with_time_windows(report_service):
    """Test aggregation with different time windows."""
    cutoff_date = datetime.now() - timedelta(days=7)

    # Create data across different time periods
    old_data = [
        Invoice(id="INV-OLD", client_id="CLI-001", client_name="Old Client", amount=1000.0, status="paid",
                date_issued=datetime.now() - timedelta(days=30))
    ]
    recent_data = [
        Invoice(id="INV-NEW", client_id="CLI-002", client_name="New Client", amount=2000.0, status="pending",
                date_issued=datetime.now() - timedelta(days=2))
    ]

    aggregated = await report_service._aggregate_invoices(recent_data)
    assert aggregated["total_value"] == 2000.0

    aggregated_old = await report_service._aggregate_invoices(old_data)
    assert aggregated_old["total_value"] == 1000.0


@pytest.mark.asyncio
async def test_comprehensive_data_aggregation(report_service):
    """Test comprehensive data aggregation across all domains."""
    financial = await report_service._aggregate_financial_data(
        datetime.now() - timedelta(days=7),
        datetime.now()
    )

    assert financial.total_revenue >= 0
    assert financial.total_expenses >= 0

    operational = await report_service._compile_operational_metrics(
        datetime.now() - timedelta(days=7)
    )

    assert operational.total_tasks_completed >= 0
    assert operational.team_utilization >= 0

    social = await report_service._aggregate_social_media_data(
        datetime.now() - timedelta(days=7),
        datetime.now()
    )

    assert social.total_engagements >= 0
    assert 0 <= social.sentiment_score <= 1.0


@pytest.mark.asyncio
async def test_data_quality_validation(report_service):
    """Test data quality validation during aggregation."""
    # Test with incomplete data
    incomplete_invoices = [
        Invoice(id="INV-001", client_id=None, client_name=None, amount=0.0, status="pending")
    ]

    with pytest.raises(ValueError):
        await report_service._validate_invoice_data(incomplete_invoices)

    # Test with properly formatted data
    valid_invoices = [
        Invoice(id="INV-002", client_id="CLI-001", client_name="Valid Client", amount=1000.0, status="paid",
                date_issued=datetime.now())
    ]

    assert await report_service._validate_invoice_data(valid_invoices) is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
