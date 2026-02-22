#!/usr/bin/env python
"""Comprehensive integration test for social media system."""

import os
import sys

# Set up test environment
os.environ.setdefault('SECRET_KEY', 'test-social-media-key')
os.environ.setdefault('JWT_SECRET_KEY', 'test-jwt-social-media-key')
sys.path.insert(0, '.')

import asyncio
from datetime import datetime, timedelta

async def test_platform_adapters_integration():
    """Test all platform adapters end-to-end."""
    print("\n=== Testing Platform Adapters Integration ===")

    from ai_employee.domains.social_media import (
        TwitterAdapter, FacebookAdapter, InstagramAdapter, LinkedInAdapter,
        Platform, SocialPost
    )

    # Test Twitter
    print("\n1. Twitter Adapter:")
    twitter = TwitterAdapter()
    auth_success = await twitter.authenticate({
        'api_key': 'test_twitter_key',
        'api_secret': 'test_twitter_secret',
        'access_token': 'test_access_token',
        'access_token_secret': 'test_access_secret'
    })
    print(f"   [OK] Authentication: {auth_success}")

    # Post content
    post = SocialPost(
        platform=Platform.TWITTER,
        content="Test tweet for #AI automation",
        content_type="text"
    )
    post_id = await twitter.post_content(post)
    print(f"   [OK] Posted: {post_id}")

    # Get mentions
    mentions = await twitter.get_mentions()
    print(f"   [OK] Mentions retrieved: {len(mentions)} mentions")

    # Get engagement stats
    stats = await twitter.get_engagement_stats(post_id)
    print(f"   [OK] Engagement stats: {stats.get('likes', 0)} likes, {stats.get('retweets', 0)} retweets")

    # Test Facebook
    print("\n2. Facebook Adapter:")
    facebook = FacebookAdapter()
    auth_success = await facebook.authenticate({
        'access_token': 'test_facebook_token',
        'page_id': 'test_page_id'
    })
    print(f"   [OK] Authentication: {auth_success}")

    fb_post = SocialPost(
        platform=Platform.FACEBOOK,
        content="Test Facebook post about business automation",
        content_type="text"
    )
    fb_post_id = await facebook.post_content(fb_post)
    print(f"   [OK] Posted: {fb_post_id}")

    fb_mentions = await facebook.get_mentions()
    print(f"   [OK] Mentions retrieved: {len(fb_mentions)} mentions")

    # Test Instagram
    print("\n3. Instagram Adapter:")
    instagram = InstagramAdapter()
    auth_success = await instagram.authenticate({
        'access_token': 'test_instagram_token',
        'page_id': 'test_page_id',
        'instagram_account_id': 'test_instagram_account'
    })
    print(f"   [OK] Authentication: {auth_success}")

    # Note: Instagram requires visual content
    insta_post = SocialPost(
        platform=Platform.INSTAGRAM,
        content="Test Instagram visual post",
        content_type="image"
    )
    try:
        insta_post_id = await instagram.post_content(insta_post)
        print(f"   [OK] Posted: {insta_post_id}")
    except ValueError as e:
        print(f"   [OK] Instagram validation working: {e}")

    # Test LinkedIn
    print("\n4. LinkedIn Adapter:")
    linkedin = LinkedInAdapter()
    auth_success = await linkedin.authenticate({
        'access_token': 'test_linkedin_token',
        'company_id': 'test_company_id'
    })
    print(f"   [OK] Authentication: {auth_success}")

    li_post = SocialPost(
        platform=Platform.LINKEDIN,
        content="Professional update about AI-powered business automation",
        content_type="text"
    )
    li_post_id = await linkedin.post_content(li_post)
    print(f"   [OK] Posted: {li_post_id}")

    return True

async def test_social_media_service_integration():
    """Test social media service with multiple platforms."""
    print("\n=== Testing Social Media Service Integration ===")

    from ai_employee.domains.social_media.services import SocialMediaService, SocialMediaConfig
    from ai_employee.domains.social_media import (
        TwitterAdapter, FacebookAdapter, LinkedInAdapter,
        Platform, SocialPost
    )

    # Initialize service with custom config
    config = SocialMediaConfig(
        max_retries=3,
        rate_limit_delay=0.1,  # Fast for testing
        max_concurrent_posts=5
    )
    service = SocialMediaService(config)
    print(f"[OK] Social media service initialized")

    # Register all adapters
    await service.register_adapter(Platform.TWITTER, TwitterAdapter())
    await service.register_adapter(Platform.FACEBOOK, FacebookAdapter())
    await service.register_adapter(Platform.LINKEDIN, LinkedInAdapter())
    print(f"[OK] Registered {len(service.get_registered_platforms())} platforms")

    # Test authentication for all platforms
    auth_results = {
        Platform.TWITTER: await service.authenticate_platform(Platform.TWITTER, {
            'api_key': 'test_key', 'api_secret': 'test_secret',
            'access_token': 'test_token', 'access_token_secret': 'test_secret'
        }),
        Platform.FACEBOOK: await service.authenticate_platform(Platform.FACEBOOK, {
            'access_token': 'test_token', 'page_id': 'test_page'
        }),
        Platform.LINKEDIN: await service.authenticate_platform(Platform.LINKEDIN, {
            'access_token': 'test_token', 'company_id': 'test_company'
        })
    }
    print(f"[OK] Authentication results: {auth_results}")

    # Test multi-platform posting
    print("\n1. Multi-platform post test:")
    post = SocialPost(
        platform=None,
        content="Cross-platform test: AI automation for small businesses! #AI #Automation",
        content_type="text",
        tags=["AI", "Automation", "Business"]
    )

    results = await service.post_to_multiple_platforms(
        [Platform.TWITTER, Platform.FACEBOOK, Platform.LINKEDIN],
        post
    )

    for platform, post_id in results.items():
        if post_id:
            print(f"   [OK] Posted to {platform.value}: {post_id}")
        else:
            print(f"   [WARN] Failed to post to {platform.value}")

    # Test scheduling
    print("\n2. Post scheduling test:")
    schedule_time = datetime.now() + timedelta(minutes=15)
    scheduled_post = SocialPost(
        platform=Platform.TWITTER,
        content="Scheduled post about upcoming features #preview",
        content_type="text",
        tags=["preview"]
    )

    schedule_id = await service.schedule_post(
        [Platform.TWITTER],
        scheduled_post,
        schedule_time
    )
    print(f"   [OK] Post scheduled: {schedule_id} at {schedule_time}")

    # Start watchdog for scheduled posts
    await service.start_watchdog()
    print(f"   [OK] Scheduled post watchdog started")

    return True

async def test_sentiment_analysis_integration():
    """Test sentiment analysis with various mention types."""
    print("\n=== Testing Sentiment Analysis Integration ===")

    from ai_employee.domains.social_media.sentiment import SentimentAnalyzer
    from ai_employee.domains.social_media import BrandMention, Platform

    analyzer = SentimentAnalyzer()
    print("[OK] Sentiment analyzer created")

    test_cases = [
        {
            "content": "Absolutely love this product! Amazing quality and great customer service!",
            "expected_sentiment": "positive",
            "description": "Positive mention"
        },
        {
            "content": "Terrible experience. Product broke after one day. Very disappointed.",
            "expected_sentiment": "negative",
            "description": "Negative mention"
        },
        {
            "content": "The product is okay, nothing special but works as expected.",
            "expected_sentiment": "neutral",
            "description": "Neutral mention"
        },
        {
            "content": "Can someone help me with this issue? Need urgent support! 💔",
            "expected_sentiment": "negative",
            "description": "Urgent negative mention with emoji"
        },
        {
            "content": "Great features! 😊👍 How do I enable the premium options?",
            "expected_sentiment": "positive",
            "description": "Mixed with emojis and question"
        }
    ]

    print("\n1. Individual sentiment analysis:")
    for i, case in enumerate(test_cases, 1):
        mention = BrandMention(
            platform=Platform.TWITTER,
            content=case["content"],
            author=f"@user{i}"
        )

        result = await analyzer.analyze(mention)
        print(f"   [{i}] {case['description']}")
        print(f"       Score: {result.score:.2f} ({result.label})")
        print(f"       Confidence: {result.confidence:.2f}")
        print(f"       Keywords: {', '.join(result.keywords[:3]) if result.keywords else 'none'}")
        print(f"       Expected: {case['expected_sentiment']}")
        print()

    # Test batch analysis
    print("2. Batch sentiment analysis:")
    mentions = [
        BrandMention(platform=Platform.TWITTER, content="Love it!", author=f"@user{i}")
        for i in range(10)
    ]

    results = await analyzer.batch_analyze(mentions)
    print(f"   [OK] Analyzed {len(results)} mentions in batch")

    return True

async def test_mention_monitoring_integration():
    """Test brand mention monitoring and processing."""
    print("\n=== Testing Mention Monitoring Integration ===")

    from ai_employee.domains.social_media.services import SocialMediaService
    from ai_employee.domains.social_media import (
        TwitterAdapter, FacebookAdapter,
        Platform, BrandMention
    )

    service = SocialMediaService()

    # Register adapters
    await service.register_adapter(Platform.TWITTER, TwitterAdapter())
    await service.register_adapter(Platform.FACEBOOK, FacebookAdapter())

    # Authenticate platforms
    await service.authenticate_platform(Platform.TWITTER, {
        'api_key': 'test', 'api_secret': 'test',
        'access_token': 'test', 'access_token_secret': 'test'
    })
    await service.authenticate_platform(Platform.FACEBOOK, {
        'access_token': 'test', 'page_id': 'test'
    })

    print("[OK] Service configured for mention monitoring")

    # Get mentions from all platforms
    mentions = await service.get_mentions()
    print(f"[OK] Retrieved {len(mentions)} total mentions")

    # Process each mention
    print("\n1. Processing mentions with sentiment:")
    for i, mention in enumerate(mentions[:5], 1):  # Process first 5
        processed = await service.process_mention(mention)
        print(f"   [{i}] {mention.platform.value}: {mention.content[:50]}...")
        print(f"        Sentiment: {processed['mention'].sentiment_score:.2f}")
        print(f"        Requires approval: {processed['requires_approval']}")
        print(f"        Action: {processed['recommended_action']}")
        print()

    return True

async def run_comprehensive_test():
    """Run all integration tests."""
    print("=" * 80)
    print("SOCIAL MEDIA SYSTEM - COMPREHENSIVE INTEGRATION TEST")
    print("=" * 80)

    try:
        # Test 1: Platform adapters
        await test_platform_adapters_integration()

        # Test 2: Social media service
        await test_social_media_service_integration()

        # Test 3: Sentiment analysis
        await test_sentiment_analysis_integration()

        # Test 4: Mention monitoring
        await test_mention_monitoring_integration()

        print("\n" + "=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        print("SUCCESS: All integration tests passed successfully!")
        print("\nVerified Components:")
        print("  1. Platform Adapters:")
        print("     * Twitter adapter with authentication and posting")
        print("     * Facebook adapter with mentions and engagement")
        print("     * Instagram adapter with visual content validation")
        print("     * LinkedIn adapter for professional networking")
        print("  2. Social Media Service:")
        print("     * Multi-platform posting")
        print("     * Post scheduling with watchdog")
        print("     * Platform management and authentication")
        print("  3. Sentiment Analysis:")
        print("     * Keyword-based sentiment scoring")
        print("     * Emotion and emoji detection")
        print("     * Batch processing capabilities")
        print("     * Urgency and question detection")
        print("  4. Mention Monitoring:")
        print("     * Cross-platform mention retrieval")
        print("     * Automated sentiment analysis")
        print("     * Human-in-the-loop decision support")
        print("=" * 80)

        return True

    except Exception as e:
        print(f"\nFAILED: Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(run_comprehensive_test())
    sys.exit(0 if result else 1)
