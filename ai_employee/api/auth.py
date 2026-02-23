"""Authentication and authorization middleware for FastAPI."""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from fastapi import HTTPException, Security, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.requests import Request
from fastapi.responses import Response
import logging

from ..utils.security import (
    SecurityMiddleware,
    SecurityLevel,
    TokenManager,
    ThreatLevel,
    input_validator,
    security_middleware
)

logger = logging.getLogger(__name__)

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
        permissions: List[str] = None
    ):
        self.user_id = user_id
        self.username = username
        self.level = level
        self.permissions = permissions or []
        self.last_activity = datetime.now()


class AuthManager:
    """Authentication manager."""

    def __init__(self):
        self.users: Dict[str, User] = {}
        self.api_keys: Dict[str, User] = {}
        self.sessions: Dict[str, User] = {}

        # Create default admin user
        self.create_user("admin", "admin123", SecurityLevel.ADMIN)

    def create_user(
        self,
        username: str,
        password: str,
        level: SecurityLevel,
        permissions: List[str] = None
    ) -> User:
        """Create a new user."""
        # Validate password
        validation = input_validator.validate_password(password)
        if not validation["valid"]:
            raise AuthenticationError(f"Invalid password: {', '.join(validation['errors'])}")

        user_id = f"user_{len(self.users) + 1}"
        user = User(
            user_id=user_id,
            username=username,
            level=level,
            permissions=permissions or []
        )

        # Store user (in production, store hashed password)
        self.users[user_id] = user

        return user

    def authenticate(self, username: str, password: str) -> Optional[User]:
        """Authenticate user with credentials."""
        # Find user by username
        user = next((u for u in self.users.values() if u.username == username), None)

        if not user:
            return None

        # In production, verify hashed password
        # For demo, accept any password for existing users
        return user

    def authenticate_api_key(self, api_key: str) -> Optional[User]:
        """Authenticate using API key."""
        return self.api_keys.get(api_key)

    def get_user_by_token(self, token: str) -> Optional[User]:
        """Get user from token."""
        payload = security_middleware.token_manager.validate_token(token)
        if not payload:
            return None

        user_id = payload.get("user_id")
        return self.users.get(user_id)

    def generate_api_key(self, user: User) -> str:
        """Generate API key for user."""
        api_key = f"ak_{secrets.token_urlsafe(32)}"
        self.api_keys[api_key] = user
        return api_key


# Global auth manager
auth_manager = AuthManager()


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme)
) -> User:
    """Get current authenticated user."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Validate token
    user = auth_manager.get_user_by_token(credentials.credentials)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Update last activity
    user.last_activity = datetime.now()

    return user


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme)
) -> Optional[User]:
    """Get current user if authenticated, otherwise None."""
    if not credentials:
        return None

    return auth_manager.get_user_by_token(credentials.credentials)


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
    """Audit logging for security events."""

    def __init__(self):
        self.audit_log: List[Dict[str, Any]] = []

    def log(
        self,
        event_type: str,
        user_id: Optional[str],
        details: Dict[str, Any],
        ip_address: str,
        user_agent: Optional[str] = None
    ):
        """Log an audit event."""
        event = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "user_id": user_id,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "details": details
        }

        self.audit_log.append(event)

        # Also log to standard logger
        logger.info(f"Audit: {event_type}", extra={"audit_event": event})

    def get_user_activity(self, user_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get activity for a specific user."""
        return [
            event for event in self.audit_log
            if event["user_id"] == user_id
        ][-limit:]

    def get_security_events(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Get security events within date range."""
        filtered = self.audit_log

        if start_date:
            filtered = [
                e for e in filtered
                if datetime.fromisoformat(e["timestamp"]) >= start_date
            ]

        if end_date:
            filtered = [
                e for e in filtered
                if datetime.fromisoformat(e["timestamp"]) <= end_date
            ]

        return filtered


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