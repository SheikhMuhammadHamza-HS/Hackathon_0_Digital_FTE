"""
Integration tests for social media post scheduling (T046).

These tests validate the complete post scheduling workflow from creation to publication,
including scheduling conflicts, timezone handling, and engagement tracking.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
from zoneinfo import ZoneInfo

from ai_employee.core.config import AppConfig
from ai_employee.core.event_bus import get_event_bus
from ai_employee.domains.social_media.models import SocialMediaPost, PostStatus, Platform
from ai_employee.domains.social_media.services import SocialMediaScheduler
from ai_employee.utils.approval_system import ApprovalRequest, ApprovalStatus


class TestPostSchedulingIntegration:
    """Integration tests for post scheduling workflow."""

    @pytest.fixture
    async def social_components(self, test_config: AppConfig):
        """Setup social media components for testing."""
        # Mock event bus
        event_bus = get_event_bus()
        await event_bus.start_background_processing()

        # Mock platform clients
        twitter_client = Mock()
        twitter_client.post_update = AsyncMock(return_value={"id": "tweet_123", "url": "https://twitter.com/status/123"})
        twitter_client.get_engagement = AsyncMock(return_value={"likes": 10, "retweets": 5, "replies": 2})

        linkedin_client = Mock()
        linkedin_client.post_update = AsyncMock(return_value={"id": "linkedin_123", "url": "https://linkedin.com/feed/update/123"})
        linkedin_client.get_engagement = AsyncMock(return_value={"likes": 15, "comments": 3, "shares": 8})

        platform_clients = {
            Platform.TWITTER: twitter_client,
            Platform.LINKEDIN: linkedin_client
        }

        # Mock approval system
        approval_system = Mock()
        approval_system.create_approval_request = AsyncMock(return_value="approval_123")
        approval_system.check_approval_status = AsyncMock(return_value=None)

        # Mock scheduler service
        scheduler_service = SocialMediaScheduler(
            platform_clients=platform_clients,
            approval_system=approval_system,
            config=test_config
        )

        yield {
            "event_bus": event_bus,
            "platform_clients": platform_clients,
            "approval_system": approval_system,
            "scheduler_service": scheduler_service,
            "config": test_config
        }

        # Cleanup
        await event_bus.stop_background_processing()

    @pytest.fixture
    def sample_post_data(self):
        """Sample post data for testing."""
        return {
            "platform": Platform.TWITTER,
            "content": "Excited to announce our new AI automation features! 🚀 #AI #Automation",
            "scheduled_at": datetime.now(ZoneInfo("UTC")) + timedelta(hours=2),
            "media_urls": ["https://example.com/image.png"],
            "hashtags": ["#AI", "#Automation"],
            "engagement_targets": {
                "target_likes": 50,
                "target_retweets": 20
            }
        }

    @pytest.mark.asyncio
    async def test_complete_post_scheduling_workflow(self, social_components, sample_post_data):
        """Test complete post scheduling workflow from creation to publication."""
        event_bus = social_components["event_bus"]
        twitter_client = social_components["platform_clients"][Platform.TWITTER]
        approval_system = social_components["approval_system"]
        scheduler_service = social_components["scheduler_service"]

        # When creating scheduled post
        post = await scheduler_service.schedule_post(sample_post_data)

        # Then post is created with correct properties
        assert post is not None
        assert post.status == PostStatus.SCHEDULED
        assert post.platform == Platform.TWITTER
        assert post.content == sample_post_data["content"]
        assert post.scheduled_at == sample_post_data["scheduled_at"]

        # And approval request was created
        approval_system.create_approval_request.assert_called_once()

        # When post is approved
        approval_request = ApprovalRequest(
            request_id="approval_123",
            item_type="social_post",
            item_id=post.id,
            metadata={"platform": Platform.TWITTER.value}
        )
        approval_request.status = ApprovalStatus.APPROVED
        approval_request.approved_by = "Marketing Manager"

        approval_system.check_approval_status.return_value = approval_request

        # And waiting for scheduled time (simulated)
        with patch('ai_employee.domains.social_media.services.time') as mock_time:
            mock_time.time.return_value = sample_post_data["scheduled_at"].timestamp()

            # Publish the post
            result = await scheduler_service.publish_post(post.id)

            # Then post is published successfully
            assert result is True
            assert post.status == PostStatus.PUBLISHED
            assert post.published_at is not None

            # And platform API was called
            twitter_client.post_update.assert_called_once()

    @pytest.mark.asyncio
    async def test_scheduling_conflict_detection(self, social_components, sample_post_data):
        """Test detection of scheduling conflicts."""
        scheduler_service = social_components["scheduler_service"]
        approval_system = social_components["approval_system"]

        # Given first post scheduled at specific time
        post1 = await scheduler_service.schedule_post(sample_post_data)
        approval_system.check_approval_status.return_value = None  # Auto-approve for testing

        # When trying to schedule second post at same time
        conflicting_data = sample_post_data.copy()
        conflicting_data["platform"] = Platform.LINKEDIN  # Different platform

        # Should not conflict on different platform
        post2 = await scheduler_service.schedule_post(conflicting_data)
        assert post2 is not None

        # When trying to schedule on same platform and time
        same_platform_data = sample_post_data.copy()
        same_platform_data["content"] = "Different content"

        # Should detect conflict
        with pytest.raises(ValueError, match="Scheduling conflict detected"):
            await scheduler_service.schedule_post(same_platform_data)

    @pytest.mark.asyncio
    async def test_timezone_handling_in_scheduling(self, social_components):
        """Test timezone handling in post scheduling."""
        scheduler_service = social_components["scheduler_service"]

        # Given post scheduled in different timezone
        ny_time = datetime.now(ZoneInfo("America/New_York")) + timedelta(hours=3)

        post_data = {
            "platform": Platform.TWITTER,
            "content": "Testing timezone handling",
            "scheduled_at": ny_time,
            "timezone": "America/New_York"
        }

        # When scheduling post
        post = await scheduler_service.schedule_post(post_data)

        # Then timezone is preserved and converted correctly
        assert post.scheduled_at.tzinfo is not None
        assert post.timezone == "America/New_York"

        # And UTC equivalent is stored
        utc_time = post.scheduled_at.astimezone(ZoneInfo("UTC"))
        assert utc_time.strftime("%H:%M") == ny_time.astimezone(ZoneInfo("UTC")).strftime("%H:%M")

    @pytest.mark.asyncio
    async def test_engagement_tracking_after_publication(self, social_components, sample_post_data):
        """Test engagement tracking and metrics collection after publication."""
        scheduler_service = social_components["scheduler_service"]
        twitter_client = social_components["platform_clients"][Platform.TWITTER]
        approval_system = social_components["approval_system"]

        # Given published post
        post = await scheduler_service.schedule_post(sample_post_data)
        approval_system.check_approval_status.return_value = None  # Auto-approve

        with patch('ai_employee.domains.social_media.services.time') as mock_time:
            mock_time.time.return_value = sample_post_data["scheduled_at"].timestamp()
            await scheduler_service.publish_post(post.id)

        # When collecting engagement metrics
        await scheduler_service.collect_engagement_metrics(post.id)

        # Then engagement data is collected
        twitter_client.get_engagement.assert_called_once()

        # And metrics are stored
        assert post.engagement_metrics is not None
        assert post.engagement_metrics["likes"] == 10
        assert post.engagement_metrics["retweets"] == 5
        assert post.engagement_metrics["replies"] == 2

        # And performance is calculated
        assert post.performance_score > 0
        if post.engagement_targets:
            assert post.engagement_targets_met is not None

    @pytest.mark.asyncio
    async def test_recurring_post_scheduling(self, social_components):
        """Test recurring post scheduling (e.g., weekly updates)."""
        scheduler_service = social_components["scheduler_service"]

        # Given recurring post schedule
        recurring_data = {
            "platform": Platform.TWITTER,
            "content": "Weekly AI insights thread",
            "scheduled_at": datetime.now(ZoneInfo("UTC")) + timedelta(hours=1),
            "recurring": True,
            "recurrence_pattern": {
                "frequency": "weekly",
                "interval": 1,
                "days_of_week": ["monday"]
            },
            "end_date": datetime.now(ZoneInfo("UTC")) + timedelta(weeks=4)
        }

        # When scheduling recurring post
        posts = await scheduler_service.schedule_recurring_posts(recurring_data)

        # Then multiple posts are created
        assert len(posts) > 1
        assert all(post.recurring_parent_id == posts[0].id for post in posts[1:])
        assert all(post.status == PostStatus.SCHEDULED for post in posts)

    @pytest.mark.asyncio
    async def test_scheduled_post_modification(self, social_components, sample_post_data):
        """Test modification of scheduled posts."""
        scheduler_service = social_components["scheduler_service"]
        approval_system = social_components["approval_system"]

        # Given scheduled post
        post = await scheduler_service.schedule_post(sample_post_data)
        original_time = post.scheduled_at

        # When modifying scheduled time
        new_time = original_time + timedelta(hours=1)
        updated_post = await scheduler_service.update_scheduled_post(
            post.id,
            {"scheduled_at": new_time}
        )

        # Then post is updated
        assert updated_post.scheduled_at == new_time
        assert updated_post.status == PostStatus.SCHEDULED
        assert updated_post.modified_count == 1

        # And modification is logged
        assert len(updated_post.modification_history) > 0
        assert updated_post.modification_history[-1]["field"] == "scheduled_at"

    @pytest.mark.asyncio
    async def test_bulk_post_scheduling(self, social_components):
        """Test bulk scheduling of multiple posts."""
        scheduler_service = social_components["scheduler_service"]

        # Given multiple posts to schedule
        posts_data = [
            {
                "platform": Platform.TWITTER,
                "content": f"Post {i} for bulk scheduling",
                "scheduled_at": datetime.now(ZoneInfo("UTC")) + timedelta(hours=i+1)
            }
            for i in range(5)
        ]

        # When bulk scheduling
        results = await scheduler_service.bulk_schedule_posts(posts_data)

        # Then all posts are scheduled
        assert len(results["successful"]) == 5
        assert len(results["failed"]) == 0

        # And conflicts are detected
        conflict_data = posts_data[0].copy()
        conflict_data["scheduled_at"] = posts_data[0]["scheduled_at"]  # Same time

        results_with_conflict = await scheduler_service.bulk_schedule_posts([conflict_data])
        assert len(results_with_conflict["failed"]) > 0
        assert "conflict" in results_with_conflict["failed"][0]["reason"]

    @pytest.mark.asyncio
    async def test_scheduled_post_cancellation(self, social_components, sample_post_data):
        """Test cancellation of scheduled posts."""
        scheduler_service = social_components["scheduler_service"]

        # Given scheduled post
        post = await scheduler_service.schedule_post(sample_post_data)
        assert post.status == PostStatus.SCHEDULED

        # When cancelling post
        cancelled_post = await scheduler_service.cancel_scheduled_post(post.id)

        # Then post is cancelled
        assert cancelled_post.status == PostStatus.CANCELLED
        assert cancelled_post.cancelled_at is not None
        assert cancelled_post.cancelled_reason is not None

        # And post cannot be published
        with pytest.raises(ValueError, match="Post has been cancelled"):
            await scheduler_service.publish_post(post.id)

    @pytest.mark.asyncio
    async def test_post_performance_analytics(self, social_components, sample_post_data):
        """Test post performance analytics generation."""
        scheduler_service = social_components["scheduler_service"]
        approval_system = social_components["approval_system"]

        # Given multiple published posts with engagement data
        posts = []
        for i in range(3):
            post_data = sample_post_data.copy()
            post_data["content"] = f"Performance test post {i}"
            post_data["scheduled_at"] = datetime.now(ZoneInfo("UTC")) + timedelta(hours=i+1)

            post = await scheduler_service.schedule_post(post_data)
            approval_system.check_approval_status.return_value = None  # Auto-approve

            with patch('ai_employee.domains.social_media.services.time') as mock_time:
                mock_time.time.return_value = post_data["scheduled_at"].timestamp()
                await scheduler_service.publish_post(post.id)

            await scheduler_service.collect_engagement_metrics(post.id)
            posts.append(post)

        # When generating analytics report
        analytics = await scheduler_service.generate_performance_analytics(
            platform=Platform.TWITTER,
            days=7
        )

        # Then analytics are generated
        assert analytics is not None
        assert analytics["total_posts"] == 3
        assert analytics["average_engagement_rate"] > 0
        assert analytics["top_performing_posts"] is not None
        assert "best_posting_times" in analytics

    @pytest.mark.asyncio
    async def test_scheduling_graceful_error_handling(self, social_components, sample_post_data):
        """Test graceful error handling in scheduling workflow."""
        scheduler_service = social_components["scheduler_service"]
        approval_system = social_components["approval_system"]

        # Given approval system failure
        approval_system.create_approval_request.side_effect = Exception("Approval system error")

        # When creating post
        with pytest.raises(Exception, match="Failed to create approval request"):
            await scheduler_service.schedule_post(sample_post_data)

        # Given invalid platform data
        invalid_data = sample_post_data.copy()
        invalid_data["platform"] = "invalid_platform"

        # Should validate platform
        with pytest.raises(ValueError, match="Invalid platform"):
            await scheduler_service.schedule_post(invalid_data)

        # Given malformed date
        invalid_data["platform"] = Platform.TWITTER
        invalid_data["scheduled_at"] = "invalid_date"

        # Should handle date parsing error
        with pytest.raises(ValueError, match="Invalid schedule time"):
            await scheduler_service.schedule_post(invalid_data)

    @pytest.mark.asyncio
    async def test_event_publishing_during_workflow(self, social_components, sample_post_data):
        """Test that events are published during scheduling workflow."""
        event_bus = social_components["event_bus"]
        approval_system = social_components["approval_system"]
        scheduler_service = social_components["scheduler_service"]

        # Given event listener
        events_received = []

        async def event_handler(event):
            events_received.append(event)

        event_bus.subscribe(event_handler)

        # When creating, approving, and publishing post
        post = await scheduler_service.schedule_post(sample_post_data)

        await asyncio.sleep(0.1)  # Allow async event processing

        # Approve post
        approval_request = ApprovalRequest(
            request_id="approval_123",
            item_type="social_post",
            item_id=post.id
        )
        approval_request.status = ApprovalStatus.APPROVED
        approval_system.check_approval_status.return_value = approval_request

        with patch('ai_employee.domains.social_media.services.time') as mock_time:
            mock_time.time.return_value = sample_post_data["scheduled_at"].timestamp()
            await scheduler_service.publish_post(post.id)

        await asyncio.sleep(0.1)  # Allow async event processing

        # Then appropriate events were published
        event_types = [event.get("event_type") for event in events_received]
        assert "social_post_scheduled" in event_types
        assert "social_post_published" in event_types

    @pytest.mark.asyncio
    async def test_concurrent_post_scheduling(self, social_components):
        """Test concurrent scheduling of multiple posts."""
        scheduler_service = social_components["scheduler_service"]

        # Given multiple posts to schedule concurrently
        async def schedule_post(i):
            post_data = {
                "platform": Platform.TWITTER,
                "content": f"Concurrent post {i}",
                "scheduled_at": datetime.now(ZoneInfo("UTC")) + timedelta(hours=i+1)
            }
            return await scheduler_service.schedule_post(post_data)

        # When scheduling concurrently
        tasks = [schedule_post(i) for i in range(10)]
        posts = await asyncio.gather(*tasks)

        # Then all posts are scheduled successfully
        assert len(posts) == 10
        assert all(post.status == PostStatus.SCHEDULED for post in posts)
        assert all(post.id is not None for post in posts)
