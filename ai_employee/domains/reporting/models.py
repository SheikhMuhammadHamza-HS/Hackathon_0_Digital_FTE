"""Models for CEO briefing and reporting domain."""

import asyncio
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class ReportType(Enum):
    """Types of reports available."""
    WEEKLY_BRIEFING = "weekly_briefing"
    MONTHLY_SUMMARY = "monthly_summary"
    QUARTERLY_REVIEW = "quarterly_review"
    CUSTOM = "custom"


class AlertLevel(Enum):
    """Alert severity levels for insights."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    OPPORTUNITY = "opportunity"


@dataclass
class FinancialSummary:
    """Financial performance summary for reporting period."""

    total_revenue: float = 0.0
    total_expenses: float = 0.0
    net_profit: float = 0.0
    profit_margin: float = 0.0
    outstanding_invoices: float = 0.0
    overdue_invoices: float = 0.0
    avg_invoice_value: float = 0.0
    payment_reconciliation_rate: float = 0.0
    key_metrics: Dict[str, Any] = field(default_factory=dict)

    def calculate_profit_margin(self) -> float:
        """Calculate profit margin percentage."""
        if self.total_revenue > 0:
            return (self.net_profit / self.total_revenue) * 100
        return 0.0


@dataclass
class OperationalMetrics:
    """Operational performance metrics."""

    total_tasks_completed: int = 0
    active_projects: int = 0
    team_utilization: float = 0.0
    avg_task_completion_time: float = 0.0  # in days
    completion_rate: float = 0.0
    bottleneck_areas: List[str] = field(default_factory=list)
    efficiency_score: float = 0.0

    def calculate_efficiency(self) -> float:
        """Calculate operational efficiency score (0-100)."""
        if self.total_tasks_completed > 0:
            task_completion_factor = min(self.total_tasks_completed / 50, 1.0)
            utilization_factor = min(self.team_utilization, 1.0)
            return (task_completion_factor * 0.6 + utilization_factor * 0.4) * 100
        return 0.0


@dataclass
class SocialMediaSummary:
    """Social media performance summary."""

    total_engagements: int = 0
    sentiment_score: float = 0.5  # 0-1 scale
    top_performing_content: List[Dict[str, Any]] = field(default_factory=list)
    posting_frequency: int = 0
    platform_breakdown: Dict[str, int] = field(default_factory=dict)
    follower_growth: int = 0
    engagement_rate: float = 0.0

    def calculate_overall_performance(self) -> float:
        """Calculate overall social media performance score (0-100)."""
        engagement_factor = min(self.total_engagements / 1000, 1.0)
        sentiment_factor = self.sentiment_score
        frequency_factor = min(self.posting_frequency / 20, 1.0)
        return (engagement_factor * 0.4 + sentiment_factor * 0.3 + frequency_factor * 0.3) * 100


@dataclass
class HealthStatus:
    """System health monitoring data."""

    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    disk_usage: float = 0.0
    process_count: int = 0
    uptime_hours: float = 0.0
    alert_count: int = 0
    last_check: datetime = field(default_factory=datetime.now)
    status: str = "healthy"  # healthy, warning, critical

    def is_healthy(self) -> bool:
        """Check if system is healthy."""
        return (self.cpu_usage < 80.0 and
                self.memory_usage < 80.0 and
                self.disk_usage < 80.0 and
                self.status != "critical")


@dataclass
class KeyPerformanceIndicator:
    """Individual KPI tracking."""

    name: str
    current_value: float
    target_value: float
    unit: str = ""
    trend: str = "stable"  # up, down, stable
    alert_level: AlertLevel = AlertLevel.INFO

    def calculate_variance(self) -> float:
        """Calculate variance from target (percentage)."""
        if self.target_value > 0:
            return ((self.current_value - self.target_value) / self.target_value) * 100
        return 0.0

    def is_on_track(self) -> bool:
        """Check if KPI is meeting target."""
        variance = abs(self.calculate_variance())
        return variance <= 10.0  # Within 10% of target


@dataclass
class StrategicInsight:
    """Strategic insight for decision making."""

    insight_type: str
    description: str
    impact_level: AlertLevel
    recommended_action: str
    data_points: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class SubscriptionInfo:
    """Subscription service information."""

    service: str
    cost: float
    billing_cycle: str  # monthly, yearly, etc.
    usage: str  # high, medium, low
    last_used: datetime
    auto_renew: bool = True
    recommendation: str = ""

    def __post_init__(self):
        """Calculate recommendations based on usage and cost."""
        if self.cost > 50 and self.usage == "low":
            self.recommendation = "Consider cancellation or downgrade"
        elif self.usage == "high":
            self.recommendation = "Continue subscription"
        else:
            self.recommendation = "Monitor usage"


@dataclass
class BottleneckAnalysis:
    """Bottleneck identification and analysis."""

    areas: List[str]
    severity: AlertLevel
    impact_description: str
    suggested_solutions: List[str] = field(default_factory=list)
    estimated_time_savings: float = 0.0  # in hours per week


@dataclass
class CEOBriefing:
    """Comprehensive CEO briefing document."""

    week_start: datetime
    week_end: datetime
    financial_summary: FinancialSummary = None
    operational_metrics: OperationalMetrics = None
    social_media_summary: SocialMediaSummary = None
    key_highlights: List[str] = field(default_factory=list)
    strategic_insights: List[StrategicInsight] = field(default_factory=list)
    proactive_suggestions: List[str] = field(default_factory=list)
    subscription_audit: List[SubscriptionInfo] = field(default_factory=list)
    bottleneck_analysis: BottleneckAnalysis = None
    system_health: HealthStatus = None
    kpis: List[KeyPerformanceIndicator] = field(default_factory=list)
    additional_notes: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Initialize default values if None."""
        if self.financial_summary is None:
            self.financial_summary = FinancialSummary()
        if self.operational_metrics is None:
            self.operational_metrics = OperationalMetrics()
        if self.social_media_summary is None:
            self.social_media_summary = SocialMediaSummary()
        if self.system_health is None:
            self.system_health = HealthStatus()
        if self.bottleneck_analysis is None:
            self.bottleneck_analysis = BottleneckAnalysis(
                areas=[],
                severity=AlertLevel.INFO,
                impact_description=""
            )

    def generate_overview(self) -> Dict[str, Any]:
        """Generate executive overview summary."""
        return {
            "week_period": f"{self.week_start.strftime('%Y-%m-%d')} to {self.week_end.strftime('%Y-%m-%d')}",
            "financial_performance": self.financial_summary.profit_margin,
            "task_completion_rate": self.operational_metrics.completion_rate,
            "social_sentiment": self.social_media_summary.sentiment_score,
            "system_health": self.system_health.status,
            "total_insights": len(self.strategic_insights),
            "bottlenecks": len(self.bottleneck_analysis.areas)
        }

    def format_for_email(self) -> str:
        """Format briefing as email text."""
        overview = self.generate_overview()

        email_text = f"""
CEO Weekly Briefing
===================

Period: {overview['week_period']}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}

EXECUTIVE SUMMARY
-----------------
• Financial Performance: {overview['financial_performance']:.1f}% profit margin
• Task Completion: {overview['task_completion_rate']:.1f}% completion rate
• Social Sentiment: {overview['social_sentiment']:.1f}/10
• System Health: {overview['system_health'].upper()}

KEY HIGHLIGHTS
--------------
"""

        for highlight in self.key_highlights[:5]:  # Top 5 highlights
            email_text += f"• {highlight}\n"

        email_text += f"""
STRATEGIC INSIGHTS
------------------
"""

        for insight in self.strategic_insights[:5]:
            alert_icon = "🚨" if insight.impact_level == AlertLevel.CRITICAL else "⚠️" if insight.impact_level == AlertLevel.WARNING else "💡"
            email_text += f"{alert_icon} {insight.description}\n"
            email_text += f"   Action: {insight.recommended_action}\n\n"

        if self.proactive_suggestions:
            email_text += """
PROACTIVE SUGGESTIONS
---------------------
"""
            for i, suggestion in enumerate(self.proactive_suggestions[:5], 1):
                email_text += f"{i}. {suggestion}\n"

        if self.bottleneck_analysis.areas:
            email_text += f"""
BOTTLENECK ALERTS
-----------------
Critical Areas: {', '.join(self.bottleneck_analysis.areas[:3])}
Impact: {self.bottleneck_analysis.impact_description}
"""

        email_text += f"""
FINANCIAL SUMMARY
-----------------
• Revenue: ${self.financial_summary.total_revenue:,.2f}
• Expenses: ${self.financial_summary.total_expenses:,.2f}
• Net Profit: ${self.financial_summary.net_profit:,.2f}
• Profit Margin: {self.financial_summary.profit_margin:.1f}%
• Outstanding Invoices: ${self.financial_summary.outstanding_invoices:,.2f}

OPERATIONAL METRICS
-------------------
• Tasks Completed: {self.operational_metrics.total_tasks_completed}
• Active Projects: {self.operational_metrics.active_projects}
• Team Utilization: {self.operational_metrics.team_utilization:.1%}
• Efficiency Score: {self.operational_metrics.efficiency_score:.1f}/100

SOCIAL MEDIA PERFORMANCE
-------------------------
• Total Engagements: {self.social_media_summary.total_engagements}
• Sentiment Score: {self.social_media_summary.sentiment_score:.1f}/10
• Posting Frequency: {self.social_media_summary.posting_frequency} posts
• Top Platform: {self.social_media_summary.top_performing_content[0]['platform'] if self.social_media_summary.top_performing_content else 'N/A'}

SUBSCRIPTION AUDIT
------------------
"""

        for sub in self.subscription_audit:
            if sub.cost > 50:
                email_text += f"• {sub.service}: ${sub.cost}/month ({sub.usage} usage) - {sub.recommendation}\n"

        email_text += """
For detailed analysis and next week's action items, please review the full report.

This briefing was automatically generated by the AI Employee system.
"""

        return email_text.strip()


@dataclass
class ReportTemplate:
    """Template for generating reports."""

    template_id: str
    name: str
    description: str
    sections: List[str]  # List of section identifiers
    required_data_sources: List[str]
    format_options: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ReportConfig:
    """Configuration for report generation."""

    template_id: str
    frequency: str  # weekly, monthly, quarterly
    recipients: List[str]
    delivery_method: str  # email, slack, dashboard
    include_sections: List[str] = field(default_factory=list)
    custom_filters: Dict[str, Any] = field(default_factory=dict)
