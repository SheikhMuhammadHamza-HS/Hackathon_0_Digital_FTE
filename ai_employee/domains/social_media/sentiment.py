"""Sentiment analysis for social media mentions."""

import asyncio
import logging
from typing import Dict, List, Tuple
from dataclasses import dataclass, field

from .models import BrandMention

logger = logging.getLogger(__name__)


@dataclass
class SentimentResult:
    """Result of sentiment analysis."""
    score: float  # 0.0 (negative) to 1.0 (positive)
    label: str  # 'positive', 'negative', 'neutral'
    confidence: float
    keywords: List[str] = field(default_factory=list)


class SentimentAnalyzer:
    """Basic sentiment analysis for social media mentions."""

    def __init__(self):
        """Initialize sentiment analyzer with keyword dictionaries."""
        self.positive_keywords = [
            'great', 'amazing', 'love', 'excellent', 'fantastic', 'good',
            'awesome', 'wonderful', 'perfect', 'excellent', 'outstanding',
            'impressed', 'satisfied', 'pleased', 'happy', 'delighted',
            'recommend', 'best', 'quality', 'professional', 'helpful'
        ]

        self.negative_keywords = [
            'bad', 'terrible', 'hate', 'awful', 'poor', 'horrible',
            'disappointed', 'frustrated', 'angry', 'upset', 'worst',
            'issue', 'problem', 'broken', 'error', 'fail', 'sucks',
            'complaint', 'unhappy', 'dissatisfied', 'terrible'
        ]

        self.urgent_keywords = [
            'urgent', 'emergency', 'immediately', 'asap', 'critical',
            'breaking', 'stop', 'prevent', 'danger', 'warning'
        ]

        self.question_keywords = [
            'how', 'what', 'when', 'where', 'why', 'can', 'could',
            'would', 'help', 'assist', 'support', 'question'
        ]

    async def analyze(self, mention: BrandMention) -> SentimentResult:
        """Analyze sentiment of a brand mention."""
        try:
            content = mention.content.lower()

            # Count positive and negative keywords
            positive_count = sum(1 for keyword in self.positive_keywords if keyword in content)
            negative_count = sum(1 for keyword in self.negative_keywords if keyword in content)
            urgent_count = sum(1 for keyword in self.urgent_keywords if keyword in content)
            question_count = sum(1 for keyword in self.question_keywords if keyword in content)

            # Calculate base sentiment score
            if positive_count > negative_count:
                base_score = 0.7 + min(0.3, (positive_count - negative_count) * 0.1)
                label = 'positive'
            elif negative_count > positive_count:
                base_score = 0.3 - min(0.3, (negative_count - positive_count) * 0.1)
                label = 'negative'
            else:
                base_score = 0.5
                label = 'neutral'

            # Adjust for urgent issues (escalate negative sentiment)
            if urgent_count > 0 and label == 'negative':
                base_score = min(0.2, base_score)
                label = 'negative'

            # Calculate confidence based on keyword matches
            total_keywords = positive_count + negative_count + urgent_count + question_count
            confidence = min(0.95, 0.5 + total_keywords * 0.1)

            # Extract relevant keywords found
            keywords = []
            if positive_count > 0:
                keywords.extend([k for k in self.positive_keywords if k in content][:3])
            if negative_count > 0:
                keywords.extend([k for k in self.negative_keywords if k in content][:3])
            if urgent_count > 0:
                keywords.extend([k for k in self.urgent_keywords if k in content][:2])
            if question_count > 0:
                keywords.extend([k for k in self.question_keywords if k in content][:2])

            return SentimentResult(
                score=base_score,
                label=label,
                confidence=confidence,
                keywords=list(set(keywords))  # Remove duplicates
            )

        except Exception as e:
            logger.error(f"Sentiment analysis failed: {e}")
            # Return neutral sentiment with low confidence
            return SentimentResult(
                score=0.5,
                label='neutral',
                confidence=0.1,
                keywords=[]
            )

    def _enhance_with_emoji_analysis(self, content: str, result: SentimentResult) -> SentimentResult:
        """Enhance sentiment analysis with emoji detection."""
        positive_emojis = ['😊', '😄', '❤️', '👍', '🎉', '😍', '✨', '⭐', '🌟']
        negative_emojis = ['😞', '😢', '👎', '💔', '😠', '😡', '😕', '😟']

        positive_emoji_count = sum(1 for emoji in positive_emojis if emoji in content)
        negative_emoji_count = sum(1 for emoji in negative_emojis if emoji in content)

        if positive_emoji_count > negative_emoji_count:
            # Boost positive sentiment
            result.score = min(1.0, result.score + 0.2)
            if result.label == 'neutral':
                result.label = 'positive'
        elif negative_emoji_count > positive_emoji_count:
            # Boost negative sentiment
            result.score = max(0.0, result.score - 0.2)
            if result.label == 'neutral':
                result.label = 'negative'

        return result

    def _check_for_sarcasm(self, content: str) -> bool:
        """Simple sarcasm detection (basic implementation)."""
        sarcasm_indicators = [
            'yeah right', 'sure', 'great', 'wonderful', 'awesome',
            'just what i needed', 'exactly what i wanted'
        ]

        content_lower = content.lower()
        has_positive_word = any(word in content_lower for word in ['great', 'awesome', 'wonderful', 'perfect'])

        if has_positive_word:
            # Check for sarcastic context
            for indicator in sarcasm_indicators:
                if indicator in content_lower:
                    return True

        return False

    async def batch_analyze(self, mentions: List[BrandMention]) -> List[Tuple[BrandMention, SentimentResult]]:
        """Analyze sentiment for multiple mentions."""
        tasks = [self.analyze(mention) for mention in mentions]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        processed_results = []
        for mention, result in zip(mentions, results):
            if isinstance(result, Exception):
                logger.error(f"Sentiment analysis failed for mention: {result}")
                result = SentimentResult(score=0.5, label='neutral', confidence=0.1, keywords=[])
            processed_results.append((mention, result))

        return processed_results
