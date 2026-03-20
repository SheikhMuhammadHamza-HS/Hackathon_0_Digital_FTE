"""FastAPI server for AI Employee system."""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from pathlib import Path
import logging
import sys
import time

from fastapi import FastAPI, HTTPException, Query, BackgroundTasks, Depends, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
import uvicorn
import secrets

from ..domains.reporting.services import ReportService
from ..domains.reporting.models import CEOBriefing, FinancialSummary, OperationalMetrics, SocialMediaSummary
from ..utils.briefing_scheduler import get_scheduler
from ..utils.error_handlers import (
    AIEmployeeError,
    ConfigurationError,
    ValidationError,
    IntegrationError,
    ErrorHandler,
    get_error_message
)
from ..utils.user_guidance import user_guide, get_help_for_error
from ..utils.performance import performance_monitor, cache_manager
from ..utils.security import security_middleware, ThreatLevel
from .auth import (
    SecurityMiddlewareHTTP,
    get_current_user,
    get_optional_user,
    require_level,
    SecurityLevel,
    User,
    auth_manager,
    audit_logger,
    AuthenticationError
)
from .database import get_db, SessionLocal, engine
from sqlalchemy import text
from sqlalchemy.orm import Session
from .models import UserDB, Base
from .data_retention import router as retention_router
from .gdpr import router as gdpr_router
from .monitoring import router as monitoring_router
from .backup import router as backup_router
from ..utils.retention_scheduler import retention_task_manager
from ..utils.monitoring import monitoring_dashboard

from ..core.config import get_config, AppConfig

logger = logging.getLogger(__name__)

# Track server start time
START_TIME = time.time()

# Initialize FastAPI app
app = FastAPI(
    title="AI Employee API",
    description="API for AI Employee system",
    version="1.0.0"
)

# Include routers
@app.get("/health")
async def root_health():
    return {"status": "ok", "service": "AI Employee API", "timestamp": datetime.now().isoformat()}

app.include_router(retention_router)
app.include_router(gdpr_router)
app.include_router(monitoring_router)
app.include_router(backup_router)

# Add security middleware
app.add_middleware(SecurityMiddlewareHTTP)

# Add CORS middleware (restrict in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:8080",
        "https://hackathon-0-digital-fte.vercel.app"
    ],  # Restrict to known origins
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Initialize services
report_service = ReportService()
scheduler = get_scheduler()

@app.on_event("startup")
async def startup_event():
    """Execute startup tasks."""
    try:
        # Create database tables if they don't exist
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created/verified successfully")
        
        # Start the briefing scheduler
        scheduler.start()
        logger.info("Briefing scheduler started successfully on server startup")
    except Exception as e:
        logger.error(f"Failed to start scheduler on startup: {e}")

# Exception handlers
@app.exception_handler(AIEmployeeError)
async def ai_employee_exception_handler(request: Request, exc: AIEmployeeError):
    """Handle AI Employee specific exceptions."""
    ErrorHandler.log_error(exc, context={"request": str(request.url)})
    return JSONResponse(
        status_code=400 if exc.severity.value in ["low", "medium"] else 500,
        content=exc.to_dict()
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions."""
    error = AIEmployeeError(
        message=f"Unexpected error: {str(exc)}",
        user_message="An unexpected error occurred. Please try again or contact support.",
        suggestions=[
            "Check the request parameters",
            "Try the operation again",
            "Contact support if the issue persists"
        ]
    )
    ErrorHandler.log_error(error, context={"request": str(request.url), "exception": str(exc)})
    return JSONResponse(
        status_code=500,
        content=error.to_dict()
    )


# Pydantic models for API
class BriefingRequest(BaseModel):
    week_start: Optional[datetime] = Field(None, description="Start date of the briefing week")
    include_recommendations: bool = Field(True, description="Include proactive recommendations")
    format: str = Field("json", description="Response format: json or markdown")

    @validator('format')
    def validate_format(cls, v):
        if v not in ['json', 'markdown']:
            raise ValidationError(
                message="Format must be 'json' or 'markdown'",
                field='format',
                value=v
            )
        return v

    @validator('week_start')
    def validate_week_start(cls, v):
        if v and v > datetime.now():
            raise ValidationError(
                message="Week start date cannot be in the future",
                field='week_start',
                value=v
            )
        return v


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


# Authentication Endpoints

@app.post("/api/v1/auth/login")
async def login(email: str, password: str, db: Session = Depends(get_db)):
    """Authenticate user and return token."""
    try:
        user = auth_manager.authenticate(db, email, password)
        if not user:
            security_middleware.log_security_event(
                "failed_login",
                ThreatLevel.MEDIUM,
                "unknown",
                details={"email": email}
            )
            raise HTTPException(
                status_code=401,
                detail="Invalid credentials"
            )

        # Generate token
        token = security_middleware.token_manager.generate_token(
            user.user_id,
            user.level,
            expires_in=3600
        )

        # Log successful login
        audit_logger.log(
            db=db,
            event_type="login",
            user_id=user.user_id,
            details={"email": email},
            ip_address="unknown"
        )

        return {
            "access_token": token,
            "token_type": "bearer",
            "expires_in": 3600,
            "user": {
                "id": user.user_id,
                "username": user.username,
                "full_name": user.full_name,
                "level": user.level.value
            }
        }

    except AIEmployeeError as e:
        logger.error(f"Login error: {e.message}")
        raise HTTPException(status_code=401, detail=e.user_message)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected login error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Authentication failed: {str(e)}")


@app.get("/api/v1/approvals")
def get_approvals(config: AppConfig = Depends(get_config)):
    """Fetch pending approvals from local filesystem."""
    try:
        # Check multiple potential paths for flexibility (local, cloud, different variants)
        potential_paths = []
        
        # 1. Path from config (the canonical one)
        potential_paths.append(config.paths.pending_approval_path)
        
        # 2. Hardcoded fallbacks based on project structure
        potential_paths.append(Path("Vault/Workflow/Pending_Approval"))
        potential_paths.append(Path("Vault/Pending_Approval"))
        potential_paths.append(Path("./Vault/Pending_Approval"))
        
        # Log search paths (visible in Render logs)
        print(f"DEBUG: Searching for approvals in: {[str(p) for p in potential_paths]}")
        
        files = []
        actual_path_used = None
        
        for p in potential_paths:
            if p.exists() and p.is_dir():
                found = list(p.glob("*.md"))
                if found:
                    files = found
                    actual_path_used = p
                    print(f"DEBUG: Found {len(files)} files in {p}")
                    break
        
        if not files:
            return {"approvals": [], "total": 0, "checked_paths": [str(p) for p in potential_paths]}

        approvals_list = []
        for f in files:
            try:
                content = f.read_text(encoding='utf-8')
                # Simple parsing for draft headers
                headers = {}
                for line in content.split('\n'):
                    if ':' in line:
                        k, v = line.split(':', 1)
                        headers[k.strip().lower()] = v.strip()
                    elif not line.strip():
                        break
                
                approvals_list.append({
                    "id": f.stem,
                    "type": headers.get("platform", "Email").capitalize(),
                    "title": f"Review {headers.get('platform', 'Email')} Draft",
                    "description": f"Subject: {headers.get('subject', 'No Subject')} | To: {headers.get('to', 'Unknown')}",
                    "priority": "Medium",
                    "time": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
                    "file_path": str(f.absolute())
                })
            except Exception as fe:
                print(f"DEBUG: Error reading {f.name}: {fe}")
                continue

        # Sort by newest first
        approvals_list.sort(key=lambda x: x["time"], reverse=True)
        
        return {
            "approvals": approvals_list,
            "total": len(approvals_list),
            "location": str(actual_path_used)
        }
    except Exception as e:
        print(f"DEBUG: Error fetching approvals: {e}")
        return {"approvals": [], "error": str(e), "total": 0}


@app.post("/api/v1/approvals/{approval_id}/approve")
def approve_draft(approval_id: str, config: AppConfig = Depends(get_config)):
    """Approve a pending draft: send the email and move file to Done."""
    try:
        # Find the draft file
        potential_paths = [
            config.paths.pending_approval_path,
            Path("Vault/Workflow/Pending_Approval"),
            Path("Vault/Pending_Approval"),
        ]

        draft_file = None
        for p in potential_paths:
            if p.exists():
                for f in p.glob("*.md"):
                    if f.stem == approval_id:
                        draft_file = f
                        break
            if draft_file:
                break

        if not draft_file:
            raise HTTPException(status_code=404, detail=f"Draft '{approval_id}' not found")

        # Move to Approved folder first
        approved_dir = Path("Vault/Workflow/Approved")
        approved_dir.mkdir(parents=True, exist_ok=True)
        approved_path = approved_dir / draft_file.name

        import shutil
        shutil.move(str(draft_file), str(approved_path))
        print(f"DEBUG: Moved draft to {approved_path}")

        # Try to send the email
        send_success = False
        try:
            from src.agents.email_sender import EmailSender
            sender = EmailSender()
            send_success = sender.send_draft(approved_path)
        except Exception as send_err:
            print(f"DEBUG: Email send error (non-fatal): {send_err}")

        # Move to Done folder
        done_dir = Path("Vault/Workflow/Done")
        done_dir.mkdir(parents=True, exist_ok=True)
        done_path = done_dir / draft_file.name
        shutil.move(str(approved_path), str(done_path))
        print(f"DEBUG: Moved to Done: {done_path}")

        return {
            "status": "approved",
            "email_sent": send_success,
            "message": f"Draft approved and {'sent' if send_success else 'archived (send failed)'}",
            "file": str(done_path)
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"DEBUG: Approve error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/approvals/{approval_id}/reject")
def reject_draft(approval_id: str, config: AppConfig = Depends(get_config)):
    """Reject a pending draft and move to Rejected folder."""
    try:
        potential_paths = [
            config.paths.pending_approval_path,
            Path("Vault/Workflow/Pending_Approval"),
            Path("Vault/Pending_Approval"),
        ]

        draft_file = None
        for p in potential_paths:
            if p.exists():
                for f in p.glob("*.md"):
                    if f.stem == approval_id:
                        draft_file = f
                        break
            if draft_file:
                break

        if not draft_file:
            raise HTTPException(status_code=404, detail=f"Draft '{approval_id}' not found")

        rejected_dir = Path("Vault/Workflow/Rejected")
        rejected_dir.mkdir(parents=True, exist_ok=True)
        rejected_path = rejected_dir / draft_file.name

        import shutil
        shutil.move(str(draft_file), str(rejected_path))
        print(f"DEBUG: Rejected draft moved to {rejected_path}")

        return {
            "status": "rejected",
            "message": "Draft rejected and archived",
            "file": str(rejected_path)
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"DEBUG: Reject error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/logs")
def get_audit_logs(limit: int = 50, db: Session = Depends(get_db)):
    """Fetch recent audit logs from the database."""
    try:
        # Import local AuditLogDB safely
        from .models import AuditLogDB
        logs = db.query(AuditLogDB).order_by(AuditLogDB.timestamp.desc()).limit(limit).all()
        
        # Format logs for frontend
        output = []
        for log in logs:
            output.append({
                "id": log.id,
                "event_type": log.event_type,
                "user_id": log.user_id,
                "details": log.details,
                "timestamp": log.timestamp.isoformat(),
                "ip_address": log.ip_address
            })
        return {"logs": output, "total": len(output)}
    except Exception as e:
        logger.error(f"Failed to fetch audit logs: {e}")
        return {"logs": [], "error": str(e)}

@app.post("/api/v1/auth/register")
async def register(email: str, password: str, full_name: str, db: Session = Depends(get_db)):
    """Register a new user."""
    try:
        # Prevent duplicate emails
        existing_user = db.query(UserDB).filter(UserDB.username == email).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already registered")

        # Create user
        user = auth_manager.create_user(db, email, password, SecurityLevel.USER, email=email, full_name=full_name)
        
        audit_logger.log(
            db=db,
            event_type="user_registered",
            user_id=user.user_id,
            details={"email": email},
            ip_address="unknown"
        )
        
        return {
            "message": "User registered successfully",
            "user": {
                "id": user.user_id,
                "username": user.username,
                "level": user.level.value
            }
        }
    except AuthenticationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        raise HTTPException(status_code=500, detail="Registration failed")


@app.post("/api/v1/auth/logout")
async def logout(user: UserDB = Depends(get_current_user), db: Session = Depends(get_db)):
    """Logout user and revoke token."""
    try:
        audit_logger.log(
            db=db,
            event_type="logout",
            user_id=str(user.id) if hasattr(user, 'id') else user.user_id,
            details={},
            ip_address="unknown"
        )

        return {"message": "Successfully logged out"}

    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        raise HTTPException(status_code=500, detail="Logout failed")


@app.get("/api/v1/auth/me")
async def get_current_user_info(user: User = Depends(get_current_user)):
    """Get current user information."""
    return {
        "id": user.user_id,
        "username": user.username,
        "level": user.level.value,
        "permissions": user.permissions,
        "last_activity": user.last_activity.isoformat()
    }


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
            "health": "/api/v1/health",
            "auth": "/api/v1/auth"
        }
    }


@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint with detailed service status."""
    try:
        from ..core.config import get_config
        config = get_config()
        
        # Initialize basic status
        services_status = {
            "reporting": "active",
            "scheduler": scheduler.is_running,
            "api": "active",
            "database": "unknown",
            "file_system": "unknown"
        }
        
        # Calculate uptime
        uptime_seconds = int(time.time() - START_TIME)
        days, rem = divmod(uptime_seconds, 86400)
        hours, rem = divmod(rem, 3600)
        minutes, seconds = divmod(rem, 60)
        uptime_str = f"{days}d {hours}h {minutes}m {seconds}s"
        
        env_info = {
            "python_version": sys.version.split()[0],
            "debug": config.debug,
            "platinum_mode": config.platinum_mode
        }
        
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.1",
            "uptime": uptime_str,
            "services": services_status,
            "environment": env_info
        }

        # Check Vault directory structure
        try:
            vault_path = config.paths.vault_path
            
            # Proactively try to create vault root
            if not vault_path.exists():
                try:
                    vault_path.mkdir(parents=True, exist_ok=True)
                except:
                    pass

            if vault_path.exists():
                required_dirs = ["Inbox", "Needs_Action", "Done", "Logs", "Pending_Approval", "Approved", "Rejected"]
                # Try to create all subdirs
                for d in required_dirs:
                    try:
                        (vault_path / d).mkdir(parents=True, exist_ok=True)
                    except:
                        pass
                
                missing_dirs = [d for d in required_dirs if not (vault_path / d).exists()]
                if missing_dirs:
                    services_status["file_system"] = f"missing_dirs: {missing_dirs}"
                else:
                    services_status["file_system"] = "healthy"
            else:
                services_status["file_system"] = "vault_directory_missing"
        except Exception as e:
            services_status["file_system"] = f"error: {str(e)}"

        # Check Database
        try:
            db = SessionLocal()
            db.execute(text("SELECT 1"))
            services_status["database"] = "healthy"
            db.close()
        except Exception as e:
            services_status["database"] = f"connection_error: {str(e)}"

        return health_status

    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise IntegrationError(
            message=f"Health check failed: {str(e)}",
            service="System Health Monitor",
            suggestions=[
                "Check system resources",
                "Verify all services are running",
                "Check application logs"
            ]
        )


@app.post("/api/v1/briefing", response_model=BriefingResponse)
async def generate_ceo_briefing(
    request: BriefingRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(require_level(SecurityLevel.USER))
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

    except ValidationError as e:
        logger.warning(f"Validation error in briefing request: {str(e)}")
        raise e
    except IntegrationError as e:
        logger.error(f"Integration error generating briefing: {str(e)}")
        raise e
    except Exception as e:
        logger.error(f"Unexpected error generating briefing: {str(e)}", exc_info=True)
        raise AIEmployeeError(
            message=f"Failed to generate CEO briefing: {str(e)}",
            user_message="Unable to generate CEO briefing due to a system error. Please try again.",
            suggestions=[
                "Check if all required services are available",
                "Verify the date range is valid",
                "Try generating a briefing for a different week",
                "Contact support if the issue persists"
            ],
            details={"original_error": str(e), "request_data": request.dict()}
        )


@app.get("/api/v1/briefing/latest")
async def get_latest_briefing(user: User = Depends(require_level(SecurityLevel.USER))):
    """Get the most recent generated briefing."""
    try:
        # Check briefing directory
        briefing_dir = Path("briefings/weekly")
        if not briefing_dir.exists():
            raise AIEmployeeError(
                message="No briefings directory found",
                user_message="No CEO briefings have been generated yet.",
                suggestions=[
                    "Generate your first CEO briefing using the /api/v1/briefing endpoint",
                    "Check if the briefing scheduler is running",
                    "Verify the briefings directory permissions"
                ]
            )

        # Find latest briefing
        briefings = list(briefing_dir.glob("*.md"))
        if not briefings:
            raise AIEmployeeError(
                message="No briefing files found",
                user_message="No CEO briefings have been generated yet.",
                suggestions=[
                    "Generate your first CEO briefing using the /api/v1/briefing endpoint",
                    "Check the briefing generation logs",
                    "Verify the briefing scheduler is configured correctly"
                ]
            )

        latest = max(briefings, key=lambda p: p.stat().st_mtime)

        return FileResponse(
            latest,
            media_type="text/markdown",
            filename=latest.name
        )

    except AIEmployeeError:
        raise
    except Exception as e:
        logger.error(f"Error getting latest briefing: {str(e)}", exc_info=True)
        raise AIEmployeeError(
            message=f"Failed to retrieve latest briefing: {str(e)}",
            user_message="Unable to retrieve the latest CEO briefing.",
            suggestions=[
                "Check if briefing files exist in the briefings directory",
                "Verify file permissions",
                "Try generating a new briefing"
            ]
        )


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

    except IntegrationError as e:
        logger.error(f"Integration error in subscription audit: {str(e)}")
        raise e
    except Exception as e:
        logger.error(f"Error in subscription audit: {str(e)}", exc_info=True)
        raise AIEmployeeError(
            message=f"Failed to audit subscriptions: {str(e)}",
            user_message="Unable to perform subscription audit at this time.",
            suggestions=[
                "Check if financial data sources are available",
                "Verify bank transaction access",
                "Try again later or contact support"
            ]
        )


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
        raise AIEmployeeError(
            message=f"Failed to stop scheduler: {str(e)}",
            user_message="Unable to stop the briefing scheduler.",
            suggestions=[
                "Check if scheduler is running",
                "Verify system permissions",
                "Try restarting the API server"
            ]
        )


@app.get("/api/v1/help")
async def get_help(
    category: Optional[str] = Query(None, description="Help category: getting_started, troubleshooting, best_practices, faq"),
    search: Optional[str] = Query(None, description="Search term for help content"),
    endpoint: Optional[str] = Query(None, description="API endpoint for contextual help")
):
    """Get help and guidance for using the AI Employee system."""
    try:
        if endpoint:
            # Get contextual help for API endpoint
            method = "GET"  # Default to GET
            if " " in endpoint:
                method, endpoint = endpoint.split(" ", 1)
            return user_guide.get_contextual_help(endpoint, method)

        elif search:
            # Search help content
            results = user_guide.search_guidance(search)
            return {
                "query": search,
                "results": results,
                "count": len(results)
            }

        elif category:
            # Get specific category guidance
            from ..utils.user_guidance import GuidanceCategory
            try:
                cat_enum = GuidanceCategory(category)
                return user_guide.get_guidance(cat_enum)
            except ValueError:
                raise ValidationError(
                    message=f"Invalid help category: {category}",
                    field="category",
                    value=category
                )

        else:
            # Return overview of available help
            return {
                "message": "AI Employee Help System",
                "categories": [
                    "getting_started",
                    "troubleshooting",
                    "best_practices",
                    "faq"
                ],
                "usage": {
                    "get_category": "/api/v1/help?category=getting_started",
                    "search": "/api/v1/help?search=odoo connection",
                    "contextual": "/api/v1/help?endpoint=/api/v1/briefing"
                },
                "quick_links": {
                    "setup_checklist": "/api/v1/help/setup-checklist",
                    "error_help": "/api/v1/help/error?error=error_message"
                }
            }

    except AIEmployeeError:
        raise
    except Exception as e:
        logger.error(f"Error retrieving help: {str(e)}")
        raise AIEmployeeError(
            message=f"Failed to retrieve help: {str(e)}",
            user_message="Help system temporarily unavailable.",
            suggestions=[
                "Try again later",
                "Check the API documentation at /docs",
                "Contact support if the issue persists"
            ]
        )


@app.get("/api/v1/help/setup-checklist")
async def get_setup_checklist():
    """Get personalized setup checklist."""
    try:
        return user_guide.generate_setup_checklist()
    except Exception as e:
        logger.error(f"Error generating setup checklist: {str(e)}")
        raise AIEmployeeError(
            message=f"Failed to generate setup checklist: {str(e)}",
            user_message="Unable to generate setup checklist."
        )


@app.get("/api/v1/help/error")
async def get_error_help(error: str = Query(..., description="Error message to get help for")):
    """Get help suggestions for a specific error."""
    try:
        return get_help_for_error(error)
    except Exception as e:
        logger.error(f"Error getting error help: {str(e)}")
        return {
            "category": "general",
            "suggestions": [
                "Check system logs for detailed error information",
                "Try the operation again",
                "Contact support with error details"
            ]
        }


@app.get("/api/v1/performance/metrics")
async def get_performance_metrics(
    operation: Optional[str] = Query(None, description="Filter by operation name"),
    limit: int = Query(100, description="Maximum number of metrics to return")
):
    """Get performance metrics."""
    try:
        metrics = performance_monitor.get_metrics(operation)
        return {
            "metrics": metrics[-limit:],  # Return most recent
            "total_count": len(metrics),
            "operation_filter": operation
        }
    except Exception as e:
        logger.error(f"Error getting performance metrics: {str(e)}")
        raise AIEmployeeError(
            message=f"Failed to get performance metrics: {str(e)}",
            user_message="Performance metrics unavailable."
        )


@app.get("/api/v1/performance/statistics")
async def get_performance_statistics(
    operation: Optional[str] = Query(None, description="Get statistics for specific operation")
):
    """Get performance statistics."""
    try:
        if operation:
            return performance_monitor.get_statistics(operation)

        # Return statistics for all operations
        all_stats = {}
        for op_name in performance_monitor.metrics.keys():
            all_stats[op_name] = performance_monitor.get_statistics(op_name)

        return {
            "operations": all_stats,
            "summary": {
                "total_operations": sum(
                    stats.get("total_operations", 0) for stats in all_stats.values()
                ),
                "average_success_rate": mean(
                    stats.get("success_rate", 0) for stats in all_stats.values()
                    if stats.get("success_rate") is not None
                ) if all_stats else 0
            }
        }
    except Exception as e:
        logger.error(f"Error getting performance statistics: {str(e)}")
        raise AIEmployeeError(
            message=f"Failed to get performance statistics: {str(e)}",
            user_message="Performance statistics unavailable."
        )


@app.get("/api/v1/performance/slow")
async def get_slow_operations(
    threshold_ms: float = Query(1000, description="Threshold in milliseconds"),
    limit: int = Query(20, description="Maximum number to return")
):
    """Get slow operations."""
    try:
        slow_ops = performance_monitor.get_slow_operations(threshold_ms)
        return {
            "threshold_ms": threshold_ms,
            "slow_operations": slow_ops[:limit],
            "count": len(slow_ops)
        }
    except Exception as e:
        logger.error(f"Error getting slow operations: {str(e)}")
        raise AIEmployeeError(
            message=f"Failed to get slow operations: {str(e)}",
            user_message="Slow operations data unavailable."
        )


@app.get("/api/v1/performance/cache")
async def get_cache_statistics():
    """Get cache performance statistics."""
    try:
        stats = await cache_manager.get_stats()
        return stats
    except Exception as e:
        logger.error(f"Error getting cache statistics: {str(e)}")
        raise AIEmployeeError(
            message=f"Failed to get cache statistics: {str(e)}",
            user_message="Cache statistics unavailable."
        )


@app.post("/api/v1/performance/cache/clear")
async def clear_expired_cache(user: User = Depends(require_level(SecurityLevel.ADMIN))):
    """Clear expired cache entries."""
    try:
        await cache_manager.clear_expired()
        audit_logger.log(
            event_type="cache_cleared",
            user_id=user.user_id,
            details={},
            ip_address="unknown"
        )
        return {"message": "Expired cache entries cleared"}
    except Exception as e:
        logger.error(f"Error clearing cache: {str(e)}")
        raise AIEmployeeError(
            message=f"Failed to clear cache: {str(e)}",
            user_message="Cache cleanup failed."
        )


# Security Management Endpoints (Admin only)

@app.get("/api/v1/admin/security/summary")
async def get_security_summary(user: User = Depends(require_level(SecurityLevel.ADMIN))):
    """Get security summary."""
    try:
        summary = security_middleware.get_security_summary()
        return summary
    except Exception as e:
        logger.error(f"Error getting security summary: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get security summary")


@app.get("/api/v1/admin/audit/log")
async def get_audit_log(
    limit: int = 100,
    user_id: Optional[str] = None,
    user: User = Depends(require_level(SecurityLevel.ADMIN))
):
    """Get audit log."""
    try:
        if user_id:
            events = audit_logger.get_user_activity(user_id, limit)
        else:
            events = audit_logger.audit_log[-limit:]

        return {
            "events": events,
            "total": len(events)
        }
    except Exception as e:
        logger.error(f"Error getting audit log: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get audit log")


@app.post("/api/v1/admin/users")
async def create_user(
    username: str,
    password: str,
    level: str,
    permissions: Optional[List[str]] = None,
    admin_user: User = Depends(require_level(SecurityLevel.ADMIN))
):
    """Create a new user."""
    try:
        # Validate security level
        try:
            user_level = SecurityLevel(level)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid security level")

        # Only admin can create admin users
        if user_level == SecurityLevel.ADMIN and admin_user.level != SecurityLevel.ADMIN:
            raise HTTPException(status_code=403, detail="Cannot create admin users")

        # Create user
        user = auth_manager.create_user(username, password, user_level, permissions)

        audit_logger.log(
            event_type="user_created",
            user_id=admin_user.user_id,
            details={
                "new_user_id": user.user_id,
                "username": username,
                "level": level
            },
            ip_address="unknown"
        )

        return {
            "message": "User created successfully",
            "user": {
                "id": user.user_id,
                "username": user.username,
                "level": user.level.value
            }
        }

    except AuthenticationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating user: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create user")


@app.post("/api/v1/admin/api-keys")
async def generate_api_key(
    user_id: str,
    admin_user: User = Depends(require_level(SecurityLevel.ADMIN))
):
    """Generate API key for user."""
    try:
        user = auth_manager.users.get(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        api_key = auth_manager.generate_api_key(user)

        audit_logger.log(
            event_type="api_key_generated",
            user_id=admin_user.user_id,
            details={
                "target_user_id": user_id
            },
            ip_address="unknown"
        )

        return {
            "api_key": api_key,
            "user_id": user_id,
            "username": user.username
        }

    except Exception as e:
        logger.error(f"Error generating API key: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate API key")


@app.post("/api/v1/admin/security/block-ip")
async def block_ip(
    ip_address: str,
    duration_hours: int = 24,
    user: User = Depends(require_level(SecurityLevel.ADMIN))
):
    """Block an IP address."""
    try:
        from datetime import timedelta
        security_middleware.blocked_ips[ip_address] = datetime.now() + timedelta(hours=duration_hours)

        security_middleware.log_security_event(
            "ip_blocked_by_admin",
            ThreatLevel.MEDIUM,
            ip_address,
            user_id=user.user_id,
            details={"duration_hours": duration_hours}
        )

        return {"message": f"IP {ip_address} blocked for {duration_hours} hours"}

    except Exception as e:
        logger.error(f"Error blocking IP: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to block IP")


# Data Retention Scheduler Endpoints

@app.get("/api/v1/retention/scheduler/status")
async def get_retention_scheduler_status(user: User = Depends(require_level(SecurityLevel.ADMIN))):
    """Get retention scheduler status."""
    return retention_task_manager.get_scheduler_status()


@app.post("/api/v1/retention/scheduler/start")
async def start_retention_scheduler(user: User = Depends(require_level(SecurityLevel.ADMIN))):
    """Start the retention scheduler."""
    try:
        if retention_task_manager.running:
            return {"message": "Scheduler is already running"}

        await retention_task_manager.start_scheduler()
        return {"message": "Retention scheduler started successfully"}

    except Exception as e:
        logger.error(f"Failed to start scheduler: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to start scheduler")


@app.post("/api/v1/retention/scheduler/stop")
async def stop_retention_scheduler(user: User = Depends(require_level(SecurityLevel.ADMIN))):
    """Stop the retention scheduler."""
    try:
        if not retention_task_manager.running:
            return {"message": "Scheduler is not running"}

        await retention_task_manager.stop_scheduler()
        return {"message": "Retention scheduler stopped successfully"}

    except Exception as e:
        logger.error(f"Failed to stop scheduler: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to stop scheduler")


@app.post("/api/v1/retention/scheduler/run-now")
async def run_retention_now(
    dry_run: bool = Query(False, description="Perform dry run"),
    user: User = Depends(require_level(SecurityLevel.ADMIN))
):
    """Run retention policies immediately."""
    try:
        result = await retention_task_manager.run_immediate_retention(dry_run=dry_run)
        return result
    except Exception as e:
        logger.error(f"Failed to run retention: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to run retention")


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