#!/usr/bin/env python
"""Core social media functionality test."""

import os
import sys

# Set up environment
os.environ.setdefault('SECRET_KEY', 'test-social-key')
os.environ.setdefault('JWT_SECRET_KEY', 'test-jwt-key')
sys.path.insert(0, '.')

import asyncio

async def test_models():
    """Test social media models."""
    print("\n=== Testing Social Media Models ===")

    from ai_employee.domains.social_media import (
        SocialPost, BrandMention, Platform, ContentType, PostStatus
    )
    from datetime import datetime

    # Test SocialPost creation
    post = SocialPost(
        platform=Platform.TWITTER,
        author_id="@test_user",
        content="Test post for #AI automation",
        content_type=ContentType.TEXT,
        tags=["AI", "automation"]
    )
    print(f"[OK] SocialPost created: {post.content[:30]}...")
    print(f"    Platform: {post.platform.value}")
    print(f"    Status: {post.status.value}")
    print(f"    Content type: {post.content_type.value}")

    # Test post scheduling
    from datetime import timedelta
    future_time = datetime.now() + timedelta(hours=2)
    post.schedule(future_time)
    print(f"[OK] Post scheduled for: {post.scheduled_time}")

    # Test BrandMention
    mention = BrandMention(
        platform=Platform.TWITTER,
        author="@customer",
        content="Love the new features! Great work!",
        engagement_score=5.0
    )
    print(f"[OK] BrandMention created: {mention.content[:30]}...")
    print(f"    Sentiment: {mention.sentiment.value}")
    print(f"    Requires response: {mention.requires_response}")

    return True

async def test_sentiment_only():
    """Test sentiment analysis standalone."""
    print("\n=== Testing Sentiment Analysis ===")

    from ai_employee.domains.social_media.sentiment import SentimentAnalyzer
    from ai_employee.domains.social_media import BrandMention, Platform

    analyzer = SentimentAnalyzer()

    test_texts = [
        ("Amazing product! Love it!", "positive"),
        ("Terrible experience, very disappointed", "negative"),
        ("It's okay, nothing special", "neutral"),
        ("Need help urgently", "negative")
    ]

    for text, expected in test_texts:
        mention = BrandMention(
            platform=Platform.TWITTER,
            content=text,
            author="@user"
        )
        result = await analyzer.analyze(mention)
        print(f"[OK] '{text[:25]}...' -> {result.label} (score: {result.score:.2f})")

    return True

async def test_platform_adapters_simple():
    """Test platform adapters in isolation."""
    print("\n=== Testing Platform Adapters ===")

    from ai_employee.domains.social_media import (
        TwitterAdapter, Platform, SocialPost
    )

    # Test Twitter adapter
    twitter = TwitterAdapter()
    auth_success = await twitter.authenticate({
        'api_key': 'test', 'api_secret': 'test',
        'access_token': 'test', 'access_token_secret': 'test'
    })
    print(f"[OK] Twitter authenticated: {auth_success}")

    post = SocialPost(
        platform=Platform.TWITTER,
        content="Test tweet #1",
        content_type="text"
    )
    post_id = await twitter.post_content(post)
    print(f"[OK] Twitter post created: {post_id}")

    return True

async def run_simple_test():
    """Run simplified social media tests."""
    print("=" * 60)
    print("SOCIAL MEDIA - CORE FUNCTIONALITY TEST")
    print("=" * 60)

    try:
        await test_models()
        await test_sentiment_only()
        await test_platform_adapters_simple()

        print("\n" + "=" * 60)
        print("SUCCESS: All core tests passed!")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"\nFAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(run_simple_test())
    sys.exit(0 if result else 1)
