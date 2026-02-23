"""Services for CEO briefing generation and reporting."""

import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
import logging
from statistics import mean

from .models import (
    CEOBriefing, FinancialSummary, OperationalMetrics, SocialMediaSummary,
    StrategicInsight, AlertLevel, SubscriptionInfo, BottleneckAnalysis,
    KeyPerformanceIndicator
)
from ...domains.invoicing.models import Invoice
from ...domains.payments.models import Payment
from ...domains.social_media.models import SocialPost, BrandMention
from ...utils.performance import (
    monitor_performance,
    cached,
    Optimizer,
    cache_manager
)

logger = logging.getLogger(__name__)


@dataclass
class ReportConfig:
    """Configuration for report generation."""

    template: str = "weekly"
    include_kpis: bool = True
    include_subscription_audit: bool = True
    include_suggestions: bool = True


class ReportService:
    """Service for generating CEO briefings and reports."""

    def __init__(self, config: Optional[ReportConfig] = None):
        """Initialize report service."""
        self.config = config or ReportConfig()
        self._subscription_services = [
            {"service": "Odoo", "cost": 29.99, "billing_cycle": "monthly"},
            {"service": "GitHub", "cost": 4.0, "billing_cycle": "monthly"},
            {"service": "Social Media Tools", "cost": 49.99, "billing_cycle": "monthly"},
        ]

    @monitor_performance("generate_weekly_briefing")
    async def generate_weekly_briefing(self, week_start: datetime) -> CEOBriefing:
        """Generate comprehensive weekly CEO briefing."""
        week_end = week_start + timedelta(days=7)

        # Run data aggregation in parallel for better performance
        tasks = await Optimizer.gather_with_concurrency(
            self._aggregate_financial_data(week_start, week_end),
            self._compile_operational_metrics(week_start),
            self._aggregate_social_media_data(week_start, week_end),
            max_concurrency=3
        )

        financial_data, operational_metrics, social_media_summary = tasks

        # Generate insights and suggestions
        strategic_insights = await self._generate_insights(
            financial_data, operational_metrics, social_media_summary
        )
        proactive_suggestions = await self._generate_suggestions(
            CEOBriefing(
                week_start=week_start,
                week_end=week_end,
                financial_summary=financial_data,
                operational_metrics=operational_metrics,
                strategic_insights=strategic_insights
            )
        )
        subscription_audit = await self._audit_subscriptions()
        bottleneck_analysis = await self._detect_bottlenecks(operational_metrics)

        # Create key highlights
        key_highlights = await self._create_highlights(
            financial_data, operational_metrics, social_media_summary
        )

        briefing = CEOBriefing(
            week_start=week_start,
            week_end=week_end,
            financial_summary=financial_data,
            operational_metrics=operational_metrics,
            social_media_summary=social_media_summary,
            key_highlights=key_highlights,
            strategic_insights=strategic_insights,
            proactive_suggestions=proactive_suggestions,
            subscription_audit=subscription_audit,
            bottleneck_analysis=bottleneck_analysis
        )

        logger.info(f"Generated weekly briefing for {week_start.strftime('%Y-%m-%d')}")
        return briefing

    @monitor_performance("aggregate_financial_data")
    @cached(ttl=300)  # Cache for 5 minutes
    async def _aggregate_financial_data(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> FinancialSummary:
        """Aggregate financial data from invoices and payments."""
        # Check cache first
        cache_key = f"financial_data:{start_date.isoformat()}:{end_date.isoformat()}"
        cached_result = await cache_manager.get(cache_key)
        if cached_result:
            return cached_result

        # This would normally fetch from database/integrations
        # For now, generate realistic mock data
        summary = FinancialSummary()

        # Mock invoice data
        summary.total_revenue = 250000.0
        summary.total_expenses = 180000.0
        summary.net_profit = summary.total_revenue - summary.total_expenses
        summary.profit_margin = (summary.net_profit / summary.total_revenue * 100) if summary.total_revenue > 0 else 0

        # Mock outstanding invoices (15% of revenue typically)
        summary.outstanding_invoices = summary.total_revenue * 0.15
        summary.overdue_invoices = summary.outstanding_invoices * 0.25  # 25% of outstanding

        # Calculate average invoice value
        summary.avg_invoice_value = summary.total_revenue / max(1, 20)  # Assume 20 invoices

        # Mock reconciliation rate
        summary.payment_reconciliation_rate = 85.0  # 85% of payments automatically matched

        summary.key_metrics = {
            "revenue_growth": 12.5,  # 12.5% growth vs last period
            "expense_ratio": summary.total_expenses / max(1, summary.total_revenue),
            "collection_efficiency": 95.0,  # 95% of invoices paid on time
            "avg_payment_delay": 3.2  # Average 3.2 days delay
        }

        return summary

    async def _compile_operational_metrics(self, start_date: datetime) -> OperationalMetrics:
        """Compile operational metrics from task data."""
        metrics = OperationalMetrics()

        # Based on task status from task list
        metrics.total_tasks_completed = 47
        metrics.active_projects = 3  # US1, US2, US4 completed
        metrics.team_utilization = 0.85  # 85% average utilization
        metrics.avg_task_completion_time = 2.5  # Average 2.5 days per task

        # Current status from task file (47 completed, 37 remaining)
        total_tasks = 84
        metrics.completion_rate = (metrics.total_tasks_completed / total_tasks) * 100

        # Identify bottlenecks based on remaining work
        metrics.bottleneck_areas = ["User Story 3", "Polish Phase", "Final Integration"]
        metrics.efficiency_score = metrics.calculate_efficiency()

        return metrics

    async def _aggregate_social_media_data(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> SocialMediaSummary:
        """Aggregate social media performance data."""
        summary = SocialMediaSummary()

        # Mock social media data
        summary.total_engagements = 1250
        summary.sentiment_score = 0.78  # 7.8/10 average sentiment
        summary.top_performing_content = [
            {"platform": "LinkedIn", "content": "Company milestone announcement", "engagement": 250},
            {"platform": "Twitter", "content": "New feature launch", "engagement": 180},
            {"platform": "Instagram", "content": "Team photo", "engagement": 150}
        ]
        summary.posting_frequency = 8  # Posts this week

        # Platform breakdown
        summary.platform_breakdown = {
            "LinkedIn": 3,
            "Twitter": 3,
            "Instagram": 2
        }

        summary.follower_growth = 45  # Net new followers
        summary.engagement_rate = 2.3  # 2.3% average engagement rate

        return summary

    async def _create_highlights(
        self,
        financial: FinancialSummary,
        operational: OperationalMetrics,
        social: SocialMediaSummary
    ) -> List[str]:
        """Create key highlights from data."""
        highlights = []

        if financial.profit_margin > 25:
            highlights.append(f"Strong profit margin of {financial.profit_margin:.1f}%")

        if operational.completion_rate > 50:
            highlights.append(f"Good progress with {operational.completion_rate:.0f}% tasks completed")

        if social.sentiment_score > 0.7:
            highlights.append(f"Positive social sentiment at {social.sentiment_score:.1f}/10")

        highlights.extend([
            f"Generated ${financial.total_revenue:,.0f} in revenue this period",
            f"Team operating at {operational.team_utilization:.0%} utilization",
            f"Social media engagement up {social.total_engagements} interactions"
        ])

        return highlights

    async def _generate_insights(
        self,
        financial: FinancialSummary,
        operational: OperationalMetrics,
        social: SocialMediaSummary
    ) -> List[StrategicInsight]:
        """Generate strategic insights from aggregated data."""
        insights = []

        # Financial insights
        if financial.overdue_invoices > financial.total_revenue * 0.1:
            insights.append(StrategicInsight(
                insight_type="Cash Flow Alert",
                description=f"High overdue invoices: ${financial.overdue_invoices:,.0f}",
                impact_level=AlertLevel.WARNING,
                recommended_action="Implement automated payment reminders"
            ))

        if financial.profit_margin < 20:
            insights.append(StrategicInsight(
                insight_type="Profit Margin",
                description=f"Profit margin below target: {financial.profit_margin:.1f}%",
                impact_level=AlertLevel.WARNING,
                recommended_action="Review expense allocation and pricing strategy"
            ))

        # Operational insights
        if len(operational.bottleneck_areas) > 2:
            insights.append(StrategicInsight(
                insight_type="Operational Bottlenecks",
                description=f"Multiple bottlenecks identified: {', '.join(operational.bottleneck_areas)}",
                impact_level=AlertLevel.CRITICAL,
                recommended_action="Prioritize bottleneck resolution to improve delivery"
            ))

        # Social media insights
        if social.sentiment_score < 0.5:
            insights.append(StrategicInsight(
                insight_type="Sentiment Alert",
                description=f"Negative sentiment detected: {social.sentiment_score:.1f}/10",
                impact_level=AlertLevel.CRITICAL,
                recommended_action="Address customer concerns and improve communication"
            ))

        # Growth opportunity
        if social.engagement_rate > 2.0:
            insights.append(StrategicInsight(
                insight_type="Growth Opportunity",
                description="High social media engagement rate",
                impact_level=AlertLevel.OPPORTUNITY,
                recommended_action="Increase posting frequency to capitalize on engagement"
            ))

        return insights

    async def _generate_suggestions(self, briefing: CEOBriefing) -> List[str]:
        """Generate proactive suggestions based on briefing data."""
        suggestions = []

        # Financial suggestions
        if briefing.financial_summary.overdue_invoices > 5000:
            suggestions.append("Implement automated payment reminders to reduce overdue invoices")

        if briefing.financial_summary.profit_margin < 20:
            suggestions.extend([
                "Review top expense categories for optimization opportunities",
                "Consider value-based pricing strategy review"
            ])

        # Operational suggestions
        if len(briefing.bottleneck_analysis.areas) > 0:
            suggestions.append("Focus team resources on bottleneck areas to improve throughput")

        if briefing.operational_metrics.efficiency_score < 75:
            suggestions.append("Implement process automation for repetitive tasks")

        # Social media suggestions
        if briefing.social_media_summary.sentiment_score < 0.6:
            suggestions.append("Develop response strategy for negative mentions")

        if briefing.social_media_summary.posting_frequency < 5:
            suggestions.append("Increase posting frequency to maintain engagement")

        # Subscription optimization
        high_cost_low_usage = [s for s in briefing.subscription_audit if s.cost > 50 and s.usage == "low"]
        if high_cost_low_usage:
            suggestions.append("Review high-cost, low-usage subscriptions for potential cancellation")

        # Strategic suggestions
        suggestions.extend([
            "Schedule quarterly business review with key clients",
            "Conduct team skills assessment for upcoming projects",
            "Review and update disaster recovery procedures"
        ])

        return suggestions[:5]  # Return top 5 suggestions

    async def _audit_subscriptions(self) -> List[SubscriptionInfo]:
        """Audit subscription services and costs."""
        subscriptions = []

        for service_data in self._subscription_services:
            sub = SubscriptionInfo(
                service=service_data["service"],
                cost=service_data["cost"],
                billing_cycle=service_data["billing_cycle"],
                usage="high" if service_data["cost"] < 50 else "medium",
                last_used=datetime.now() - timedelta(days=7)
            )

            # Update usage based on actual usage patterns
            if sub.service == "Odoo" and sub.cost < 50:
                sub.usage = "high"
            elif sub.service == "Social Media Tools":
                sub.usage = "high"  # US2 completion indicates high usage

            subscriptions.append(sub)

        return subscriptions

    async def _detect_bottlenecks(self, metrics: OperationalMetrics) -> BottleneckAnalysis:
        """Detect operational bottlenecks."""
        analysis = BottleneckAnalysis(
            areas=metrics.bottleneck_areas,
            severity=AlertLevel.WARNING,
            impact_description="Reduced overall project velocity"
        )

        if "User Story 3" in analysis.areas:
            analysis.suggested_solutions.extend([
                "Allocate dedicated resources to CEO Briefing feature",
                "Break down remaining tasks into smaller deliverables"
            ])
            analysis.estimated_time_savings = 10.0  # 10 hours/week

        if "Polish Phase" in analysis.areas:
            analysis.suggested_solutions.extend([
                "Prioritize critical polish items over nice-to-haves",
                "Consider phased deployment with polish in v2"
            ])

        if len(analysis.areas) >= 3:
            analysis.severity = AlertLevel.CRITICAL
            analysis.impact_description = "Significant impact on project delivery timeline"

        return analysis

    async def _calculate_weighted_sentiment(self, mentions: List[BrandMention]) -> float:
        """Calculate weighted sentiment score from mentions."""
        if not mentions:
            return 0.5  # Neutral if no data

        # Weight by engagement score
        total_weight = sum(m.engagement_score for m in mentions)
        if total_weight == 0:
            # Use simple average if no engagement data
            return mean(m.sentiment_score for m in mentions)

        weighted_sum = sum(m.sentiment_score * m.engagement_score for m in mentions)
        return min(1.0, max(0.0, weighted_sum / total_weight))

    # Data aggregation helpers
    async def _aggregate_invoices(self, invoices: List[Invoice]) -> Dict[str, Any]:
        """Aggregate invoice data for reporting."""
        if not invoices:
            return {
                "total_value": 0.0,
                "paid_value": 0.0,
                "pending_value": 0.0,
                "paid_count": 0,
                "pending_count": 0,
                "overdue_count": 0,
                "avg_invoice_value": 0.0
            }

        total_value = sum(float(inv.total_amount.amount) for inv in invoices)
        paid_value = sum(float(inv.total_amount.amount) for inv in invoices if inv.status.value == "paid")
        pending_value = sum(float(inv.total_amount.amount) for inv in invoices if inv.status.value == "sent")

        paid_count = sum(1 for inv in invoices if inv.status.value == "paid")
        pending_count = sum(1 for inv in invoices if inv.status.value == "sent")
        overdue_count = sum(1 for inv in invoices if inv.status.value == "overdue")

        return {
            "total_value": total_value,
            "paid_value": paid_value,
            "pending_value": pending_value,
            "paid_count": paid_count,
            "pending_count": pending_count,
            "overdue_count": overdue_count,
            "avg_invoice_value": total_value / len(invoices)
        }

    async def _aggregate_payments(self, payments: List[Payment]) -> Dict[str, Any]:
        """Aggregate payment data for reporting."""
        if not payments:
            return {
                "total_received": 0.0,
                "matched_amount": 0.0,
                "unmatched_amount": 0.0,
                "reconciliation_rate": 0.0
            }

        total_received = sum(float(p.amount.amount) for p in payments)
        matched_amount = sum(float(p.amount.amount) for p in payments if p.status.value == "reconciled")

        return {
            "total_received": total_received,
            "matched_amount": matched_amount,
            "unmatched_amount": total_received - matched_amount,
            "reconciliation_rate": (matched_amount / total_received * 100) if total_received > 0 else 0
        }

    async def _aggregate_task_data(self, task_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Aggregate task completion data."""
        if not task_data:
            return {
                "total_tasks": 0,
                "completed_tasks": 0,
                "in_progress_tasks": 0,
                "overdue_tasks": 0,
                "completion_rate": 0.0,
                "completed_this_week": []
            }

        completed = [task for task in task_data if task.get("status") == "completed"]
        in_progress = [task for task in task_data if task.get("status") == "in_progress"]

        week_ago = datetime.now() - timedelta(days=7)
        completed_this_week = [
            task for task in completed
            if task.get("completed_at") and datetime.fromisoformat(task.get("completed_at")) > week_ago
        ]

        return {
            "total_tasks": len(task_data),
            "completed_tasks": len(completed),
            "in_progress_tasks": len(in_progress),
            "overdue_tasks": sum(1 for task in task_data if task.get("status") == "overdue"),
            "completion_rate": (len(completed) / len(task_data) * 100) if task_data else 0,
            "completed_this_week": completed_this_week
        }

    async def _aggregate_social_metrics(
        self,
        posts: List[SocialPost],
        mentions: List[BrandMention]
    ) -> Dict[str, Any]:
        """Aggregate social media metrics."""
        if not posts and not mentions:
            return {
                "total_posts": 0,
                "total_engagements": 0,
                "avg_engagement_score": 0.0,
                "mentions_count": 0,
                "sentiment_score": 0.5,
                "platform_breakdown": {},
                "top_content": []
            }

        total_engagements = sum(post.metrics.get("engagement", 0) for post in posts) + sum(
            mention.engagement_score for mention in mentions)

        platform_breakdown = {}
        for post in posts:
            platform_breakdown[post.platform] = platform_breakdown.get(post.platform, 0) + 1

        return {
            "total_posts": len(posts),
            "total_engagements": total_engagements,
            "avg_engagement_score": total_engagements / max(1, len(posts) + len(mentions)),
            "mentions_count": len(mentions),
            "sentiment_score": await self._calculate_weighted_sentiment(mentions),
            "platform_breakdown": platform_breakdown,
            "top_content": sorted([
                {"platform": p.platform, "engagement": p.metrics.get("engagement", 0)}
                for p in posts
            ], key=lambda x: x["engagement"], reverse=True)[:3]
        }

    async def _validate_invoice_data(self, invoices: List[Invoice]) -> bool:
        """Validate invoice data quality."""
        if not invoices:
            return True  # Empty list is valid

        for invoice in invoices:
            if not all([invoice.id, invoice.client_id, float(invoice.total_amount.amount) > 0]):
                raise ValueError(f"Invalid invoice data: {invoice.id}")

        return True
