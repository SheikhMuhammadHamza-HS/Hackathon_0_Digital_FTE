"""FastAPI server for AI Employee system."""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, BackgroundTasks, Depends
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

from ..domains.reporting.services import ReportService
from ..domains.reporting.models import CEOBriefing, FinancialSummary, OperationalMetrics, SocialMediaSummary
from ..utils.briefing_scheduler import get_scheduler

# Initialize FastAPI app
app = FastAPI(
    title="AI Employee API",
    description="API for AI Employee system",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
report_service = ReportService()
scheduler = get_scheduler()

# Pydantic models for API
class BriefingRequest(BaseModel):
    week_start: Optional[datetime] = Field(None, description="Start date of the briefing week")
    include_recommendations: bool = Field(True, description="Include proactive recommendations")
    format: str = Field("json", description="Response format: json or markdown")


class BriefingResponse(BaseModel):
    briefing: Dict[str, Any]
    generated_at: datetime
    period: str
    status: str


class SubscriptionAuditResponse(BaseModel):
    subscriptions: List[Dict[str, Any]]
    total_monthly_cost: float
    potential_savings: float
    recommendations: List[str]


class BottleneckAnalysisResponse(BaseModel):
    bottlenecks: List[Dict[str, Any]]
    severity: str
    estimated_impact: str
    suggested_actions: List[str]


# API Endpoints

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "AI Employee API",
        "version": "1.0.0",
        "endpoints": {
            "briefing": "/api/v1/briefing",
            "subscription_audit": "/api/v1/audit/subscriptions",
            "bottlenecks": "/api/v1/analysis/bottlenecks",
            "health": "/api/v1/health"
        }
    }


@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now(),
        "services": {
            "reporting": "active",
            "scheduler": scheduler.get_schedule_status()["is_running"]
        }
    }


@app.post("/api/v1/briefing", response_model=BriefingResponse)
async def generate_ceo_briefing(
    request: BriefingRequest,
    background_tasks: BackgroundTasks
):
    """Generate CEO briefing for specified week."""
    try:
        # Determine week start
        if request.week_start:
            week_start = request.week_start
        else:
            # Default to current week
            today = datetime.now()
            days_since_monday = today.weekday()
            week_start = today - timedelta(days=days_since_monday)
            week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)

        # Generate briefing
        briefing = await report_service.generate_weekly_briefing(week_start)

        # Format response
        if request.format == "markdown":
            content = briefing.format_for_email()
            # Save to file and return
            filename = f"briefing_{week_start.strftime('%Y-%m-%d')}.md"
            filepath = Path("briefings") / filename
            filepath.parent.mkdir(exist_ok=True)
            filepath.write_text(content, encoding='utf-8')

            background_tasks.add_task(
                lambda: logger.info(f"Briefing saved to {filepath}")
            )

            return FileResponse(
                filepath,
                media_type="text/markdown",
                filename=filename
            )
        else:
            # Return JSON
            briefing_data = {
                "week_start": briefing.week_start.isoformat(),
                "week_end": briefing.week_end.isoformat(),
                "financial_summary": {
                    "total_revenue": briefing.financial_summary.total_revenue,
                    "total_expenses": briefing.financial_summary.total_expenses,
                    "net_profit": briefing.financial_summary.net_profit,
                    "profit_margin": briefing.financial_summary.profit_margin,
                    "outstanding_invoices": briefing.financial_summary.outstanding_invoices
                },
                "operational_metrics": {
                    "total_tasks_completed": briefing.operational_metrics.total_tasks_completed,
                    "active_projects": briefing.operational_metrics.active_projects,
                    "team_utilization": briefing.operational_metrics.team_utilization,
                    "completion_rate": briefing.operational_metrics.completion_rate,
                    "efficiency_score": briefing.operational_metrics.efficiency_score
                },
                "social_media_summary": {
                    "total_engagements": briefing.social_media_summary.total_engagements,
                    "sentiment_score": briefing.social_media_summary.sentiment_score,
                    "posting_frequency": briefing.social_media_summary.posting_frequency,
                    "top_performing_content": briefing.social_media_summary.top_performing_content
                },
                "key_highlights": briefing.key_highlights,
                "strategic_insights": [
                    {
                        "type": insight.insight_type,
                        "description": insight.description,
                        "impact": insight.impact_level.value,
                        "action": insight.recommended_action
                    }
                    for insight in briefing.strategic_insights
                ]
            }

            if request.include_recommendations:
                briefing_data["proactive_suggestions"] = briefing.proactive_suggestions
                briefing_data["subscription_audit"] = [
                    {
                        "service": sub.service,
                        "cost": sub.cost,
                        "usage": sub.usage,
                        "recommendation": sub.recommendation
                    }
                    for sub in briefing.subscription_audit
                ]
                briefing_data["bottleneck_analysis"] = {
                    "areas": briefing.bottleneck_analysis.areas,
                    "severity": briefing.bottleneck_analysis.severity.value,
                    "impact": briefing.bottleneck_analysis.impact_description,
                    "solutions": briefing.bottleneck_analysis.suggested_solutions
                }

            return BriefingResponse(
                briefing=briefing_data,
                generated_at=datetime.now(),
                period=f"{briefing.week_start.strftime('%Y-%m-%d')} to {briefing.week_end.strftime('%Y-%m-%d')}",
                status="success"
            )

    except Exception as e:
        logger.error(f"Error generating briefing: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/briefing/latest")
async def get_latest_briefing():
    """Get the most recent generated briefing."""
    try:
        # Check briefing directory
        briefing_dir = Path("briefings/weekly")
        if not briefing_dir.exists():
            raise HTTPException(status_code=404, detail="No briefings found")

        # Find latest briefing
        briefings = list(briefing_dir.glob("*.md"))
        if not briefings:
            raise HTTPException(status_code=404, detail="No briefings found")

        latest = max(briefings, key=lambda p: p.stat().st_mtime)

        return FileResponse(
            latest,
            media_type="text/markdown",
            filename=latest.name
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting latest briefing: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/audit/subscriptions", response_model=SubscriptionAuditResponse)
async def get_subscription_audit():
    """Get subscription audit and cost-saving analysis."""
    try:
        subscriptions = await report_service._audit_subscriptions()

        total_cost = sum(sub.cost for sub in subscriptions)
        potential_savings = sum(
            sub.cost for sub in subscriptions
            if sub.cost > 50 and sub.usage == "low"
        )

        recommendations = [
            f"Cancel {sub.service} (${sub.cost}/month, {sub.usage} usage)"
            for sub in subscriptions
            if sub.cost > 50 and sub.usage == "low"
        ]

        return SubscriptionAuditResponse(
            subscriptions=[
                {
                    "service": sub.service,
                    "cost": sub.cost,
                    "usage": sub.usage,
                    "billing_cycle": sub.billing_cycle,
                    "recommendation": sub.recommendation
                }
                for sub in subscriptions
            ],
            total_monthly_cost=total_cost,
            potential_savings=potential_savings,
            recommendations=recommendations
        )

    except Exception as e:
        logger.error(f"Error in subscription audit: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/analysis/bottlenecks", response_model=BottleneckAnalysisResponse)
async def get_bottleneck_analysis():
    """Get current bottleneck analysis."""
    try:
        # Get operational metrics
        metrics = await report_service._compile_operational_metrics(
            datetime.now() - timedelta(days=7)
        )

        bottlenecks = await report_service._detect_bottlenecks(metrics)

        # Determine severity
        if len(bottlenecks.areas) >= 3:
            severity = "critical"
            impact = "Significant impact on project delivery timeline"
        elif len(bottlenecks.areas) >= 1:
            severity = "warning"
            impact = "Reduced overall project velocity"
        else:
            severity = "info"
            impact = "No significant bottlenecks detected"

        return BottleneckAnalysisResponse(
            bottlenecks=[
                {
                    "area": area,
                    "description": f"Bottleneck detected in {area}",
                    "estimated_delay": "2-3 days"
                }
                for area in bottlenecks.areas
            ],
            severity=severity,
            estimated_impact=impact,
            suggested_actions=bottlenecks.suggested_solutions
        )

    except Exception as e:
        logger.error(f"Error in bottleneck analysis: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/schedule/briefing")
async def schedule_briefing(
    week: Optional[str] = Query(None, description="Week in YYYY-MM-DD format"),
    briefing_type: str = Query("weekly", description="Type: weekly or monthly")
):
    """Schedule a briefing to be generated."""
    try:
        scheduler.generate_now(briefing_type, week)

        return {
            "message": f"{briefing_type.title()} briefing scheduled",
            "week": week or "current",
            "status": "scheduled"
        }

    except Exception as e:
        logger.error(f"Error scheduling briefing: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/schedule/status")
async def get_schedule_status():
    """Get scheduler status and next run times."""
    try:
        status = scheduler.get_schedule_status()

        return {
            "is_running": status["is_running"],
            "scheduled_jobs": status["scheduled_jobs"],
            "next_runs": status["next_runs"],
            "configuration": {
                "weekly_briefing": {
                    "enabled": status["config"]["schedule"]["weekly_briefing"]["enabled"],
                    "time": status["config"]["schedule"]["weekly_briefing"]["time"]
                },
                "monthly_summary": {
                    "enabled": status["config"]["schedule"]["monthly_summary"]["enabled"],
                    "time": status["config"]["schedule"]["monthly_summary"]["time"]
                }
            }
        }

    except Exception as e:
        logger.error(f"Error getting schedule status: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/scheduler/start")
async def start_scheduler():
    """Start the briefing scheduler."""
    try:
        from ..utils.briefing_scheduler import start_scheduler
        start_scheduler()

        return {
            "message": "Scheduler started successfully",
            "status": "running"
        }

    except Exception as e:
        logger.error(f"Error starting scheduler: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/scheduler/stop")
async def stop_scheduler():
    """Stop the briefing scheduler."""
    try:
        from ..utils.briefing_scheduler import stop_scheduler
        stop_scheduler()

        return {
            "message": "Scheduler stopped",
            "status": "stopped"
        }

    except Exception as e:
        logger.error(f"Error stopping scheduler: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# Error handlers
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


if __name__ == "__main__":
    import logging

    # Setup logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    # Run the server
    uvicorn.run(
        "ai_employee.api.server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )