"""Authentication and authorization middleware for FastAPI."""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from fastapi import HTTPException, Security, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.requests import Request
from fastapi.responses import Response
import logging
import bcrypt
from passlib.context import CryptContext
from .database import SessionLocal, engine, get_db
from .models import UserDB, Base, AuditLogDB
from sqlalchemy.orm import Session

from ..utils.security import (
    SecurityMiddleware,
    SecurityLevel,
    TokenManager,
    ThreatLevel,
    input_validator,
    security_middleware
)

logger = logging.getLogger(__name__)

# Tables are created via app startup, not module import
# Base.metadata.create_all(bind=engine)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# HTTP Bearer scheme for token authentication
bearer_scheme = HTTPBearer(auto_error=False)


class AuthenticationError(Exception):
    """Authentication error."""
    pass


class AuthorizationError(Exception):
    """Authorization error."""
    pass


class User:
    """User model for authentication."""

    def __init__(
        self,
        user_id: str,
        username: str,
        level: SecurityLevel,
        email: Optional[str] = None,
        full_name: Optional[str] = None,
        permissions: List[str] = None
    ):
        self.user_id = user_id
        self.username = username
        self.level = level
        self.email = email
        self.full_name = full_name
        self.permissions = permissions or []
        self.last_activity = datetime.now()


class AuthManager:
    """Authentication manager with Database support."""

    def __init__(self):
        # We'll use SessionLocal to create sessions for each request
        # No more in-memory storage for persistent users
        self.api_keys: Dict[str, UserDB] = {}
        
        # Verify if admin exists, if not create it
        db = SessionLocal()
        try:
            admin = db.query(UserDB).filter(UserDB.username == "admin").first()
            if not admin:
                # Use a password that passes validation: admin@123Admin
                self.create_user(db, "admin", "admin@123Admin", SecurityLevel.ADMIN, email="admin@vaultos.ai", full_name="System Administrator")
        finally:
            db.close()

    def get_password_hash(self, password):
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

    def verify_password(self, plain_password, hashed_password):
        try:
            return bcrypt.checkpw(
                plain_password.encode('utf-8'), 
                hashed_password.encode('utf-8')
            )
        except Exception:
            # Fallback for old passlib hashes if any
            try:
                return pwd_context.verify(plain_password, hashed_password)
            except Exception:
                return False

    def create_user(
        self,
        db: Session,
        username: str,
        password: str,
        level: SecurityLevel,
        email: Optional[str] = None,
        full_name: Optional[str] = None,
        permissions: List[str] = None
    ) -> User:
        """Create a new user in database."""
        # Validate password
        validation = input_validator.validate_password(password)
        if not validation["valid"]:
            raise AuthenticationError(f"Invalid password: {', '.join(validation['errors'])}")

        hashed_password = self.get_password_hash(password)
        
        db_user = UserDB(
            username=username,
            email=email or username,
            full_name=full_name,
            hashed_password=hashed_password,
            level=level.value,
            permissions=permissions or []
        )
        
        db.add(db_user)
        db.commit()
        db.refresh(db_user)

        return User(
            user_id=str(db_user.id),
            username=db_user.username,
            level=SecurityLevel(db_user.level),
            email=db_user.email,
            full_name=db_user.full_name,
            permissions=db_user.permissions
        )

    def authenticate(self, db: Session, username: str, password: str) -> Optional[User]:
        """Authenticate user with credentials from DB."""
        db_user = db.query(UserDB).filter(UserDB.username == username).first() or \
                  db.query(UserDB).filter(UserDB.email == username).first()

        if not db_user:
            return None

        if not self.verify_password(password, db_user.hashed_password):
            return None
        
        # Update last activity
        db_user.last_login = datetime.now()
        db.commit()

        user_obj = User(
            user_id=str(db_user.id),
            username=db_user.username,
            level=SecurityLevel(db_user.level),
            email=db_user.email,
            full_name=db_user.full_name,
            permissions=db_user.permissions
        )
        print(f"DEBUG AUTH: User obj has level: {hasattr(user_obj, 'level')}")
        return user_obj


    def authenticate_api_key(self, api_key: str) -> Optional[User]:
        """Authenticate using API key."""
        return self.api_keys.get(api_key)

    def get_user_by_id(self, db: Session, user_id: str) -> Optional[User]:
        """Get user by ID."""
        try:
            db_user = db.query(UserDB).filter(UserDB.id == int(user_id)).first()
            if not db_user:
                return None
            return User(
                user_id=str(db_user.id),
                username=db_user.username,
                level=SecurityLevel(db_user.level),
                email=db_user.email,
                full_name=db_user.full_name,
                permissions=db_user.permissions
            )
        except:
            return None

    def get_user_by_token(self, db: Session, token: str) -> Optional[User]:
        """Get user from token using DB."""
        payload = security_middleware.token_manager.validate_token(token)
        if not payload:
            return None

        user_id = payload.get("user_id")
        return self.get_user_by_id(db, user_id)

    def generate_api_key(self, user: User) -> str:
        """Generate API key for user."""
        api_key = f"ak_{secrets.token_urlsafe(32)}"
        self.api_keys[api_key] = user
        return api_key


# Global auth manager
auth_manager = AuthManager()


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Validate token
    user = auth_manager.get_user_by_token(db, credentials.credentials)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """Get current user if authenticated, otherwise None."""
    if not credentials:
        return None

    return auth_manager.get_user_by_token(db, credentials.credentials)


def require_level(level: SecurityLevel):
    """Decorator to require security level."""
    async def level_dependency(user: User = Depends(get_current_user)) -> User:
        if user.level.value < level.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires {level.value} level or higher"
            )
        return user

    return level_dependency


def require_permission(permission: str):
    """Decorator to require specific permission."""
    async def permission_dependency(user: User = Depends(get_current_user)) -> User:
        if permission not in user.permissions and user.level != SecurityLevel.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires permission: {permission}"
            )
        return user

    return permission_dependency


class SecurityMiddlewareHTTP(BaseHTTPMiddleware):
    """HTTP middleware for security."""

    async def dispatch(self, request: Request, call_next):
        """Process request through security middleware."""
        # Get client IP
        client_ip = request.client.host
        if "x-forwarded-for" in request.headers:
            client_ip = request.headers["x-forwarded-for"].split(",")[0].strip()

        # Check IP blacklist
        if security_middleware.check_ip_blacklist(client_ip):
            security_middleware.log_security_event(
                "blocked_ip_access",
                ThreatLevel.HIGH,
                client_ip,
                user_agent=request.headers.get("user-agent"),
                details={"path": str(request.url.path)}
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )

        # Check IP whitelist
        if not security_middleware.check_ip_whitelist(client_ip):
            security_middleware.log_security_event(
                "unauthorized_ip_access",
                ThreatLevel.MEDIUM,
                client_ip,
                user_agent=request.headers.get("user-agent"),
                details={"path": str(request.url.path)}
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )

        # Get security level from token if present
        user_level = SecurityLevel.PUBLIC
        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]
            payload = security_middleware.token_manager.validate_token(token)
            if payload:
                user_level = SecurityLevel(payload.get("level", "public"))

        # Rate limiting
        allowed, message = security_middleware.check_rate_limit(
            client_ip,
            str(request.url.path),
            user_level
        )
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=message
            )

        # Validate request body for suspicious content
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.body()
                if body:
                    body_str = body.decode()
                    suspicious = security_middleware.detect_suspicious_input(body_str)
                    if suspicious:
                        security_middleware.log_security_event(
                            "suspicious_input",
                            ThreatLevel.HIGH,
                            client_ip,
                            user_agent=request.headers.get("user-agent"),
                            details={
                                "path": str(request.url.path),
                                "patterns": suspicious
                            }
                        )
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Suspicious input detected"
                        )
            except Exception:
                pass  # If we can't read body, continue

        # Add security headers
        response = await call_next(request)

        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self'; "
            "connect-src 'self'"
        )

        return response


class AuditLogger:
    """Audit logging for security events with Database support."""

    def __init__(self):
        # Database session will be provided at log time or use SessionLocal
        pass

    def log(
        self,
        db: Session,
        event_type: str,
        user_id: Optional[str],
        details: Dict[str, Any],
        ip_address: str,
        user_agent: Optional[str] = None
    ):
        """Log an audit event to DB."""
        try:
            log_entry = AuditLogDB(
                event_type=event_type,
                user_id=user_id,
                details=details,
                ip_address=ip_address
            )
            db.add(log_entry)
            db.commit()
        except Exception as e:
            logger.error(f"Failed to log audit event: {str(e)}")

        # Also log to standard logger
        logger.info(f"Audit: {event_type} (user_id={user_id})")

    def get_user_activity(self, db: Session, user_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get activity for a specific user from DB."""
        logs = db.query(AuditLogDB).filter(AuditLogDB.user_id == user_id).order_by(AuditLogDB.timestamp.desc()).limit(limit).all()
        return [
            {
                "timestamp": log.timestamp.isoformat(),
                "event_type": log.event_type,
                "user_id": log.user_id,
                "ip_address": log.ip_address,
                "details": log.details
            } for log in logs
        ]

    def get_security_events(
        self,
        db: Session,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Get security events from DB within date range."""
        query = db.query(AuditLogDB)
        if start_date:
            query = query.filter(AuditLogDB.timestamp >= start_date)
        if end_date:
            query = query.filter(AuditLogDB.timestamp <= end_date)
            
        logs = query.order_by(AuditLogDB.timestamp.desc()).all()
        return [
            {
                "timestamp": log.timestamp.isoformat(),
                "event_type": log.event_type,
                "user_id": log.user_id,
                "ip_address": log.ip_address,
                "details": log.details
            } for log in logs
        ]


# Global audit logger
audit_logger = AuditLogger()


def audit_action(event_type: str):
    """Decorator to audit actions."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Try to extract user from kwargs
            user = None
            for key, value in kwargs.items():
                if isinstance(value, User):
                    user = value
                    break

            # Execute function
            result = await func(*args, **kwargs)

            # Log audit event
            audit_logger.log(
                event_type=event_type,
                user_id=user.user_id if user else None,
                details={"function": func.__name__},
                ip_address="",  # Would need to extract from request
                user_agent=None
            )

            return result
        return wrapper
    return decorator