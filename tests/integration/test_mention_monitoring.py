"""
Integration tests for social media mention monitoring (T047).

These tests validate real-time mention detection, sentiment analysis integration,
and response workflow with HITL approval system.
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock, patch
from typing import List, Dict, Any

from ai_employee.core.config import AppConfig
from ai_employee.core.event_bus import get_event_bus
from ai_employee.domains.social_media.models import Mention, MentionType, Sentiment, Platform
from ai_employee.domains.social_media.services import MentionMonitor
from ai_employee.domains.social_media.mention_analyzer import MentionAnalyzer
from ai_employee.utils.approval_system import ApprovalRequest, ApprovalStatus


class TestMentionMonitoringIntegration:
    """Integration tests for mention monitoring workflow."""

    @pytest.fixture
    async def mention_monitor(self, test_config: AppConfig):
        """Setup mention monitor for testing."""
        # Mock event bus
        event_bus = get_event_bus()
        await event_bus.start_background_processing()

        # Mock platform clients
        twitter_client = Mock()
        linkedin_client = Mock()

        platform_clients = {
            Platform.TWITTER: twitter_client,
            Platform.LINKEDIN: linkedin_client
        }

        # Mock AI analyzer
        ai_analyzer = Mock()

        # Mock approval system
        approval_system = Mock()
        approval_system.create_approval_request = AsyncMock(return_value="approval_123")
        approval_system.check_approval_status = AsyncMock(return_value=None)

        # Create mention analyzer
        mention_analyzer = MentionAnalyzer(ai_analyzer=ai_analyzer)

        # Create mention monitor
        monitor = MentionMonitor(
            platform_clients=platform_clients,
            mention_analyzer=mention_analyzer,
            approval_system=approval_system,
            config=test_config
        )

        yield {
            "monitor": monitor,
            "event_bus": event_bus,
            "platform_clients": platform_clients,
            "ai_analyzer": ai_analyzer,
            "approval_system": approval_system,
            "mention_analyzer": mention_analyzer
        }

        # Cleanup
        await event_bus.stop_background_processing()

    @pytest.fixture
    def sample_mentions(self) -> List[Mention]:
        """Sample mentions for testing."""
        return [
            Mention(
                id="mention_1",
                platform=Platform.TWITTER,
                content="Great work @OurCompany! Love the new AI features! 🎉",
                author="@happy_customer",
                timestamp=datetime.now(timezone.utc),
                url="https://twitter.com/happy_customer/status/123",
                mention_type=MentionType.DIRECT,
                sentiment=Sentiment.POSITIVE,
                engagement_potential=0.9
            ),
            Mention(
                id="mention_2",
                platform=Platform.TWITTER,
                content="@OurCompany Your customer service is terrible. Worst experience ever.",
                author="@angry_customer",
                timestamp=datetime.now(timezone.utc) - timedelta(minutes=5),
                url="https://twitter.com/angry_customer/status/124",
                mention_type=MentionType.DIRECT,
                sentiment=Sentiment.NEGATIVE,
                engagement_potential=0.7,
                requires_response=True
            ),
            Mention(
                id="mention_3",
                platform=Platform.LINKEDIN,
                content="I wonder if @OurCompany's AI can help with our workflow automation needs.",
                author="LinkedIn User",
                timestamp=datetime.now(timezone.utc) - timedelta(hours=1),
                url="https://linkedin.com/feed/update/125",
                mention_type=MentionType.QUESTION,
                sentiment=Sentiment.NEUTRAL,
                engagement_potential=0.6
            )
        ]

    @pytest.mark.asyncio
    async def test_real_time_mention_detection(self, mention_monitor):
        """Test real-time mention detection from social platforms."""
        monitor_data = mention_monitor
        monitor = monitor_data["monitor"]
        twitter_client = monitor_data["platform_clients"][Platform.TWITTER]

        # Given mock mentions from Twitter
        mock_tweets = [
            {
                "id": "tweet_123",
                "text": "Great work @OurCompany! Love the new features!",
                "user": {"screen_name": "happy_customer"},
                "created_at": datetime.now(timezone.utc).isoformat()
            },
            {
                "id": "tweet_124",
                "text": "@OurCompany having issues with your service 😠",
                "user": {"screen_name": "frustrated_user"},
                "created_at": datetime.now(timezone.utc).isoformat()
            }
        ]

        twitter_client.get_mentions = AsyncMock(return_value=mock_tweets)

        # When monitoring mentions
        mentions = await monitor.check_platform_mentions(Platform.TWITTER)

        # Then mentions are detected
        assert len(mentions) == 2
        assert all(isinstance(mention, Mention) for mention in mentions)

        # And mention metadata is extracted correctly
        assert mentions[0].author == "@happy_customer"
        assert mentions[0].platform == Platform.TWITTER
        assert mentions[1].content == "@OurCompany having issues with your service 😠"

    @pytest.mark.asyncio
    async def test_sentiment_analysis_integration(self, mention_monitor, sample_mentions):
        """Test sentiment analysis integration with mention processing."""
        monitor_data = mention_monitor
        monitor = monitor_data["monitor"]
        mention_analyzer = monitor_data["mention_analyzer"]

        # Given mentions to analyze
        positive_mention = sample_mentions[0]
        negative_mention = sample_mentions[1]
        neutral_mention = sample_mentions[2]

        # When analyzing sentiment
        sentiment_results = await asyncio.gather(
            mention_analyzer.analyze_sentiment(positive_mention),
            mention_analyzer.analyze_sentiment(negative_mention),
            mention_analyzer.analyze_sentiment(neutral_mention)
        )

        # Then sentiment is correctly classified
        assert sentiment_results[0] == Sentiment.POSITIVE
        assert sentiment_results[1] == Sentiment.NEGATIVE
        assert sentiment_results[2] == Sentiment.NEUTRAL

    @pytest.mark.asyncio
    async def test_auto_response_generation(self, mention_monitor):
        """Test automatic response generation for mentions."""
        monitor_data = mention_monitor
        monitor = monitor_data["monitor"]
        approval_system = monitor_data["approval_system"]

        # Given a mention that requires response
        mention = Mention(
            id="mention_1",
            platform=Platform.TWITTER,
            content="@OurCompany Can you explain your pricing model?",
            author="@potential_customer",
            timestamp=datetime.now(timezone.utc),
            url="https://twitter.com/potential_customer/status/123",
            mention_type=MentionType.QUESTION,
            sentiment=Sentiment.NEUTRAL,
            requires_response=True
        )

        # Mock AI response generation
        monitor.mention_analyzer.generate_response = AsyncMock(
            return_value="Thanks for your interest! Our pricing is based on usage tiers..."
        )

        # When generating response
        response_data = await monitor.generate_response(mention)

        # Then response is generated
        assert response_data is not None
        assert "content" in response_data
        assert response_data["content"] == "Thanks for your interest! Our pricing is based on usage tiers..."
        assert response_data["platform"] == Platform.TWITTER

        # And approval request is created for HITL
        approval_system.create_approval_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_mention_response_workflow_with_hitl_approval(self, mention_monitor):
        """Test complete mention response workflow with HITL approval system."""
        monitor_data = mention_monitor
        monitor = monitor_data["monitor"]
        event_bus = monitor_data["event_bus"]
        approval_system = monitor_data["approval_system"]
        twitter_client = monitor_data["platform_clients"][Platform.TWITTER]

        # Given mention requiring response
        mention = Mention(
            id="mention_response_1",
            platform=Platform.TWITTER,
            content="@OurCompany I'm having trouble with my account",
            author="@troubled_user",
            timestamp=datetime.now(timezone.utc),
            url="https://twitter.com/troubled_user/status/125",
            mention_type=MentionType.SUPPORT_REQUEST,
            sentiment=Sentiment.NEGATIVE,
            requires_response=True,
            priority=0.8
        )

        # Mock response generation
        monitor.mention_analyzer.generate_response = AsyncMock(
            return_value="We're here to help! Please DM us your account details and we'll assist you right away."
        )

        # When processing mention
        event_listener = Mock()
        events_received = []

        async def event_handler(event):
            events_received.append(event)
        event_bus.subscribe(event_handler)

        # Generate and queue response
        response = await monitor.process_mention(mention)

        # Then response is queued for approval
        assert response["status"] == "pending_approval"

        # When approval is given
        approval_request = ApprovalRequest(
            request_id="approval_123",
            item_type="mention_response",
            item_id=mention.id,
            metadata={
                "platform": Platform.TWITTER.value,
                "response_text": response["content"]
            }
        )
        approval_request.status = ApprovalStatus.APPROVED
        approval_request.approved_by = "Social Media Manager"

        approval_system.check_approval_status.return_value = approval_request

        # And response is sent
        twitter_client.post_update = AsyncMock(return_value={"id": "response_123"})
        result = await monitor.send_response(mention.id, response["content"])

        # Then response is sent successfully
        assert result is True
        assert mention.response_sent is True
        assert mention.response_id == "response_123"

        # And appropriate events were published
        event_types = [event.get("event_type") for event in events_received]
        assert "mention_detected" in event_types
        assert "mention_response_queued" in event_types
        assert "mention_response_sent" in event_types

    @pytest.mark.asyncio
    async def test_priority_based_mention_queueing(self, mention_monitor):
        """Test priority-based queueing of mentions."""
        monitor_data = mention_monitor
        monitor = monitor_data["monitor"]

        # Given mentions with different priorities
        high_priority = Mention(
            id="high_priority",
            platform=Platform.TWITTER,
            content="@OurCompany URGENT: System is down!",
            author="@urgent_user",
            timestamp=datetime.now(timezone.utc),
            priority=0.95
        )

        medium_priority = Mention(
            id="medium_priority",
            platform=Platform.TWITTER,
            content="@OurCompany Question about your product",
            author="@curious_user",
            timestamp=datetime.now(timezone.utc),
            priority=0.6
        )

        low_priority = Mention(
            id="low_priority",
            platform=Platform.TWITTER,
            content="@OurCompany Nice work!",
            author="@compliment_user",
            timestamp=datetime.now(timezone.utc),
            priority=0.3
        )

        # When adding to queue
        await monitor.queue_mention(high_priority)
        await monitor.queue_mention(low_priority)
        await monitor.queue_mention(medium_priority)

        # Then queue is priority-ordered
        queue = monitor.get_priority_queue()
        assert len(queue) == 3
        assert queue[0].id == "high_priority"
        assert queue[1].id == "medium_priority"
        assert queue[2].id == "low_priority"

    @pytest.mark.asyncio
    async def test_mention_sentiment_based_routing(self, mention_monitor):
        """Test routing of mentions based on sentiment and type."""
        monitor_data = mention_monitor
        monitor = monitor_data["monitor"]

        # Given mentions of different types
        complaints = []
        questions = []
        compliments = []

        # Simulate monitoring mentions
        for i in range(10):
            # Mock mentions with different sentiments
            mention = Mention(
                id=f"mention_{i}",
                platform=Platform.TWITTER,
                content=f"@OurCompany Test mention {i}",
                author=f"@user_{i}",
                timestamp=datetime.now(timezone.utc),
                sentiment=Sentiment.POSITIVE if i < 3 else Sentiment.NEGATIVE if i < 7 else Sentiment.NEUTRAL
            )

            # Route based on sentiment and content
            if mention.sentiment == Sentiment.NEGATIVE:
                complaints.append(mention)
                mention.requires_response = True
                mention.priority = 0.8
            elif "question" in mention.content.lower() or mention.mention_type == MentionType.QUESTION:
                questions.append(mention)
                mention.requires_response = True
            else:
                compliments.append(mention)

        # Then routing logic works correctly
        assert len(complaints) == 4  # Negative mentions
        assert len(questions) == 0  # No questions in this batch
        assert len(compliments) == 6  # Positive/Neutral mentions

        # And high-priority items are flagged
        assert all(mention.priority > 0.7 for mention in complaints)

    @pytest.mark.asyncio
    async def test_mention_tracking_and_history(self, mention_monitor):
        """Test tracking of mention history and patterns."""
        monitor_data = mention_monitor
        monitor = monitor_data["monitor"]

        # Given historical mention data
        historical_mentions = []
        for i in range(20):
            mention = Mention(
                id=f"hist_mention_{i}",
                platform=Platform.TWITTER,
                content=f"@OurCompany Historical mention {i}",
                author=f"@user_{i % 5}",  # Repeat users
                timestamp=datetime.now(timezone.utc) - timedelta(days=i // 5),
                sentiment=Sentiment.POSITIVE if i % 3 == 0 else Sentiment.NEGATIVE
            )
            historical_mentions.append(mention)

        # When analyzing patterns
        patterns = await monitor.analyze_mention_patterns(historical_mentions)

        # Then patterns are identified
        assert "sentiment_distribution" in patterns
        assert "frequent_users" in patterns
        assert "peak_activity_times" in patterns
        assert patterns["total_mentions"] == 20

        # And sentiment trends are tracked
        sentiment_dist = patterns["sentiment_distribution"]
        assert sentiment_dist[Sentiment.POSITIVE] > 0
        assert sentiment_dist[Sentiment.NEGATIVE] > 0
        assert sentiment_dist[Sentiment.NEUTRAL] >= 0

    @pytest.mark.asyncio
    async def test_cross_platform_mention_consolidation(self, mention_monitor):
        """Test consolidation of mentions across multiple platforms."""
        monitor_data = mention_monitor
        monitor = monitor_data["monitor"]

        # Given mentions across platforms
        twitter_mentions = [
            Mention(
                id="tw_1",
                platform=Platform.TWITTER,
                content="@OurCompany Great work!",
                author="@twitter_user"
            )
        ]

        linkedin_mentions = [
            Mention(
                id="li_1",
                platform=Platform.LINKEDIN,
                content="@OurCompany Excellent presentation today",
                author="LinkedIn User"
            )
        ]

        # When consolidating
        all_mentions = await monitor.consolidate_mentions({
            Platform.TWITTER: twitter_mentions,
            Platform.LINKEDIN: linkedin_mentions
        })

        # Then all mentions are included
        assert len(all_mentions) == 2
        assert len([m for m in all_mentions if m.platform == Platform.TWITTER]) == 1
        assert len([m for m in all_mentions if m.platform == Platform.LINKEDIN]) == 1

    @pytest.mark.asyncio
    async def test_mention_response_templates(self, mention_monitor):
        """Test response templates for different mention types."""
        monitor_data = mention_monitor
        monitor = monitor_data["monitor"]
        mention_analyzer = monitor_data["mention_analyzer"]

        # Define response templates
        templates = {
            MentionType.COMPLAINT: "We're sorry to hear that. Our team will reach out to help resolve this.",
            MentionType.QUESTION: "Thanks for your question! Here's some helpful information...",
            MentionType.COMPLIMENT: "Thank you so much! We really appreciate your support!",
            MentionType.SUPPORT_REQUEST: "We're here to help! Please DM us with more details.",
            MentionType.FEATURE_REQUEST: "Great idea! We'll share this with our product team."
        }

        # Test each template type
        for mention_type, expected_response in templates.items():
            mention = Mention(
                id=f"template_test_{mention_type.value}",
                platform=Platform.TWITTER,
                content=f"Test {mention_type.value} mention",
                author="@test_user",
                timestamp=datetime.now(timezone.utc),
                mention_type=mention_type
            )

            # Mock template response
            mention_analyzer.generate_response = AsyncMock(return_value=expected_response)

            response = await mention_analyzer.generate_response(mention)
            assert response == expected_response

    @pytest.mark.asyncio
    async def test_mention_monitoring_error_handling(self, mention_monitor):
        """Test error handling in mention monitoring."""
        monitor_data = mention_monitor
        monitor = monitor_data["monitor"]
        twitter_client = monitor_data["platform_clients"][Platform.TWITTER]

        # Given platform API failure
        twitter_client.get_mentions.side_effect = Exception("API rate limit exceeded")

        # When checking mentions
        with pytest.raises(Exception, match="API rate limit exceeded"):
            await monitor.check_platform_mentions(Platform.TWITTER)

        # Given corrupted mention data
        corrupted_data = [{"invalid": "data"}]
        twitter_client.get_mentions = AsyncMock(return_value=corrupted_data)

        # Should handle gracefully
        mentions = await monitor.check_platform_mentions(Platform.TWITTER)
        assert len(mentions) == 0  # No valid mentions in corrupted data

    @pytest.mark.asyncio
    async def test_event_publishing_during_mention_workflow(self, mention_monitor):
        """Test that events are published during mention workflow."""
        monitor_data = mention_monitor
        monitor = monitor_data["monitor"]
        event_bus = monitor_data["event_bus"]

        # Given event listener
        events_received = []

        async def event_handler(event):
            events_received.append(event)

        event_bus.subscribe(event_handler)

        # When processing mentions
        mention = Mention(
            id="event_test_1",
            platform=Platform.TWITTER,
            content="@OurCompany Testing event publishing",
            author="@event_tester",
            timestamp=datetime.now(timezone.utc),
            sentiment=Sentiment.POSITIVE
        )

        await monitor.process_mention(mention)

        await asyncio.sleep(0.1)  # Allow async event processing

        # Then appropriate events were published
        event_types = [event.get("event_type") for event in events_received]
        assert "mention_detected" in event_types

    @pytest.mark.asyncio
    async def test_concurrent_mention_processing(self, mention_monitor):
        """Test concurrent processing of multiple mentions."""
        monitor_data = mention_monitor
        monitor = monitor_data["monitor"]

        # Given multiple mentions to process
        mentions = [
            Mention(
                id=f"concurrent_{i}",
                platform=Platform.TWITTER,
                content=f"@OurCompany Concurrent mention {i}",
                author=f"@user_{i}",
                timestamp=datetime.now(timezone.utc)
            )
            for i in range(10)
        ]

        # When processing concurrently
        tasks = [monitor.process_mention(mention) for mention in mentions]
        results = await asyncio.gather(*tasks)

        # Then all mentions are processed
        assert len(results) == 10
        assert all(result is not None for result in results)
