"""Security utilities for AI Employee system."""

import hashlib
import secrets
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum
import logging
import re
import html
import json

logger = logging.getLogger(__name__)


class SecurityLevel(Enum):
    """Security levels for different operations."""
    PUBLIC = "public"
    USER = "user"
    ADMIN = "admin"
    SYSTEM = "system"


class ThreatLevel(Enum):
    """Threat levels for security events."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SecurityEvent:
    """Security event tracking."""
    event_type: str
    threat_level: ThreatLevel
    source_ip: str
    user_agent: Optional[str] = None
    user_id: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    resolved: bool = False


@dataclass
class RateLimitRule:
    """Rate limiting rule."""
    window_seconds: int
    max_requests: int
    block_duration_seconds: int = 300  # 5 minutes default


class SecurityConfig:
    """Security configuration."""

    def __init__(self):
        # Rate limiting rules by endpoint and user level
        self.rate_limits = {
            SecurityLevel.PUBLIC: {
                "/api/v1/health": RateLimitRule(60, 100),  # 100 requests/minute
                "/api/v1/help": RateLimitRule(60, 50),    # 50 requests/minute
                "default": RateLimitRule(60, 10)          # 10 requests/minute
            },
            SecurityLevel.USER: {
                "/api/v1/briefing": RateLimitRule(60, 20),
                "/api/v1/audit/*": RateLimitRule(3600, 100),  # 100 requests/hour
                "default": RateLimitRule(60, 30)
            },
            SecurityLevel.ADMIN: {
                "default": RateLimitRule(60, 200)  # 200 requests/minute
            }
        }

        # Security settings
        self.max_login_attempts = 5
        self.lockout_duration = 900  # 15 minutes
        self.session_timeout = 3600  # 1 hour
        self.password_min_length = 12
        self.require_2fa = False

        # IP whitelist/blacklist
        self.whitelisted_ips: Set[str] = set()
        self.blacklisted_ips: Set[str] = set()

        # Suspicious patterns
        self.suspicious_patterns = [
            r"<script[^>]*>.*?</script>",  # XSS
            r"union\s+select",            # SQL injection
            r"drop\s+table",              # SQL injection
            r"exec\s*\(",                # Code injection
            r"eval\s*\(",                # Code injection
        ]


class InputValidator:
    """Input validation and sanitization."""

    @staticmethod
    def sanitize_html(text: str) -> str:
        """Sanitize HTML input to prevent XSS."""
        # Basic HTML sanitization
        text = html.escape(text)
        # Remove potentially dangerous tags
        dangerous_tags = ["script", "iframe", "object", "embed", "link", "meta"]
        for tag in dangerous_tags:
            pattern = rf"<{tag}[^>]*>.*?</{tag}>"
            text = re.sub(pattern, "", text, flags=re.IGNORECASE | re.DOTALL)
        return text

    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format."""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))

    @staticmethod
    def validate_password(password: str) -> Dict[str, Any]:
        """Validate password strength."""
        result = {
            "valid": True,
            "errors": [],
            "score": 0
        }

        # Length check
        if len(password) < 12:
            result["valid"] = False
            result["errors"].append("Password must be at least 12 characters")

        # Complexity checks
        if not re.search(r"[A-Z]", password):
            result["errors"].append("Password must contain uppercase letters")
        else:
            result["score"] += 1

        if not re.search(r"[a-z]", password):
            result["errors"].append("Password must contain lowercase letters")
        else:
            result["score"] += 1

        if not re.search(r"\d", password):
            result["errors"].append("Password must contain numbers")
        else:
            result["score"] += 1

        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
            result["errors"].append("Password must contain special characters")
        else:
            result["score"] += 1

        return result

    @staticmethod
    def sanitize_sql(query: str) -> str:
        """Basic SQL injection prevention."""
        # Remove common SQL injection patterns
        dangerous = [
            "union select", "drop table", "delete from",
            "insert into", "update set", "exec(", "eval(",
            "system(", "xp_cmdshell", "sp_executesql"
        ]

        for pattern in dangerous:
            query = re.sub(pattern, "", query, flags=re.IGNORECASE)

        return query

    @staticmethod
    def validate_path(path: str) -> bool:
        """Validate file path to prevent directory traversal."""
        # Normalize path
        path = path.replace("\\", "/")
        # Check for directory traversal
        if ".." in path or path.startswith("/"):
            return False
        # Check for invalid characters
        invalid_chars = ["<", ">", ":", "\"", "|", "?", "*"]
        return not any(char in path for char in invalid_chars)


class TokenManager:
    """JWT token management for authentication."""

    def __init__(self, secret_key: str):
        self.secret_key = secret_key
        self.tokens: Dict[str, Dict[str, Any]] = {}

    def generate_token(self, user_id: str, level: SecurityLevel, expires_in: int = 3600) -> str:
        """Generate a secure token."""
        payload = {
            "user_id": user_id,
            "level": level.value,
            "exp": time.time() + expires_in,
            "iat": time.time(),
            "jti": secrets.token_urlsafe(32)
        }

        # Simple token encoding (in production, use proper JWT library)
        token_data = json.dumps(payload)
        signature = hashlib.hmac(
            self.secret_key.encode(),
            token_data.encode(),
            hashlib.sha256
        ).hexdigest()

        token = f"{token_data}.{signature}"

        # Store token metadata
        self.tokens[payload["jti"]] = {
            "user_id": user_id,
            "level": level,
            "created_at": datetime.now(),
            "expires_at": datetime.fromtimestamp(payload["exp"])
        }

        return token

    def validate_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Validate a token."""
        try:
            token_data, signature = token.rsplit(".", 1)

            # Verify signature
            expected_signature = hashlib.hmac(
                self.secret_key.encode(),
                token_data.encode(),
                hashlib.sha256
            ).hexdigest()

            if not secrets.compare_digest(signature, expected_signature):
                return None

            # Parse payload
            payload = json.loads(token_data)

            # Check expiration
            if time.time() > payload.get("exp", 0):
                # Clean up expired token
                if "jti" in payload:
                    self.tokens.pop(payload["jti"], None)
                return None

            return payload

        except (ValueError, json.JSONDecodeError):
            return None

    def revoke_token(self, token: str):
        """Revoke a token."""
        try:
            token_data, _ = token.rsplit(".", 1)
            payload = json.loads(token_data)
            if "jti" in payload:
                self.tokens.pop(payload["jti"], None)
        except (ValueError, json.JSONDecodeError):
            pass

    def cleanup_expired(self):
        """Clean up expired tokens."""
        now = datetime.now()
        expired_tokens = [
            jti for jti, data in self.tokens.items()
            if data["expires_at"] < now
        ]
        for jti in expired_tokens:
            self.tokens.pop(jti, None)


class SecurityMiddleware:
    """Security middleware for API endpoints."""

    def __init__(self, config: Optional[SecurityConfig] = None):
        self.config = config or SecurityConfig()
        self.rate_limit_store: Dict[str, List[datetime]] = {}
        self.blocked_ips: Dict[str, datetime] = {}
        self.failed_attempts: Dict[str, int] = {}
        self.security_events: List[SecurityEvent] = []
        self.token_manager = TokenManager(secrets.token_urlsafe(32))

    def check_ip_whitelist(self, ip: str) -> bool:
        """Check if IP is whitelisted."""
        if not self.config.whitelisted_ips:
            return True  # No whitelist configured
        return ip in self.config.whitelisted_ips

    def check_ip_blacklist(self, ip: str) -> bool:
        """Check if IP is blacklisted."""
        if ip in self.config.blacklisted_ips:
            return True

        # Check temporary blocks
        if ip in self.blocked_ips:
            if datetime.now() < self.blocked_ips[ip]:
                return True
            else:
                # Block expired
                del self.blocked_ips[ip]

        return False

    def check_rate_limit(self, ip: str, endpoint: str, level: SecurityLevel = SecurityLevel.PUBLIC) -> tuple[bool, Optional[str]]:
        """Check rate limiting for an IP."""
        # Get appropriate rule
        rules = self.config.rate_limits.get(level, {})
        rule = rules.get(endpoint, rules.get("default", RateLimitRule(60, 10)))

        key = f"{ip}:{endpoint}"
        now = datetime.now()

        # Clean old entries
        if key in self.rate_limit_store:
            self.rate_limit_store[key] = [
                req_time for req_time in self.rate_limit_store[key]
                if now - req_time < timedelta(seconds=rule.window_seconds)
            ]
        else:
            self.rate_limit_store[key] = []

        # Check limit
        if len(self.rate_limit_store[key]) >= rule.max_requests:
            # Block the IP
            self.blocked_ips[ip] = now + timedelta(seconds=rule.block_duration_seconds)

            # Log security event
            self.log_security_event(
                "rate_limit_exceeded",
                ThreatLevel.MEDIUM,
                ip,
                details={
                    "endpoint": endpoint,
                    "requests": len(self.rate_limit_store[key]),
                    "limit": rule.max_requests
                }
            )

            return False, f"Rate limit exceeded. Try again in {rule.block_duration_seconds} seconds."

        # Add current request
        self.rate_limit_store[key].append(now)
        return True, None

    def detect_suspicious_input(self, data: Any) -> List[str]:
        """Detect suspicious patterns in input."""
        suspicious = []

        if isinstance(data, str):
            for pattern in self.config.suspicious_patterns:
                if re.search(pattern, data, re.IGNORECASE):
                    suspicious.append(f"Suspicious pattern detected: {pattern}")

        elif isinstance(data, dict):
            for value in data.values():
                suspicious.extend(self.detect_suspicious_input(value))

        elif isinstance(data, list):
            for item in data:
                suspicious.extend(self.detect_suspicious_input(item))

        return suspicious

    def log_security_event(self, event_type: str, threat_level: ThreatLevel,
                          source_ip: str, user_agent: Optional[str] = None,
                          user_id: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        """Log a security event."""
        event = SecurityEvent(
            event_type=event_type,
            threat_level=threat_level,
            source_ip=source_ip,
            user_agent=user_agent,
            user_id=user_id,
            details=details or {}
        )

        self.security_events.append(event)

        # Log based on threat level
        log_message = f"Security Event: {event_type} from {source_ip}"
        if threat_level == ThreatLevel.CRITICAL:
            logger.critical(log_message, extra={"event": event.to_dict()})
        elif threat_level == ThreatLevel.HIGH:
            logger.error(log_message, extra={"event": event.to_dict()})
        elif threat_level == ThreatLevel.MEDIUM:
            logger.warning(log_message, extra={"event": event.to_dict()})
        else:
            logger.info(log_message, extra={"event": event.to_dict()})

    def get_security_summary(self) -> Dict[str, Any]:
        """Get security summary."""
        now = datetime.now()
        last_24h = now - timedelta(hours=24)

        recent_events = [
            e for e in self.security_events
            if e.timestamp > last_24h
        ]

        threat_counts = {}
        for event in recent_events:
            level = event.threat_level.value
            threat_counts[level] = threat_counts.get(level, 0) + 1

        return {
            "total_events": len(recent_events),
            "threat_distribution": threat_counts,
            "blocked_ips": len(self.blocked_ips),
            "active_tokens": len(self.token_manager.tokens),
            "high_risk_sources": [
                event.source_ip for event in recent_events
                if event.threat_level in [ThreatLevel.HIGH, ThreatLevel.CRITICAL]
            ]
        }


class CSRFProtection:
    """Cross-Site Request Forgery protection."""

    def __init__(self, secret_key: str):
        self.secret_key = secret_key
        self.tokens: Dict[str, datetime] = {}

    def generate_token(self, session_id: str) -> str:
        """Generate CSRF token."""
        timestamp = str(int(time.time()))
        message = f"{session_id}:{timestamp}"

        token = hashlib.sha256(
            f"{message}:{self.secret_key}".encode()
        ).hexdigest()

        # Store token with expiration
        self.tokens[token] = datetime.now() + timedelta(hours=24)

        return token

    def validate_token(self, token: str, session_id: str) -> bool:
        """Validate CSRF token."""
        if token not in self.tokens:
            return False

        # Check expiration
        if datetime.now() > self.tokens[token]:
            del self.tokens[token]
            return False

        # Verify token
        # Note: In production, you'd want to verify the timestamp
        # This is a simplified version

        return True

    def cleanup_expired(self):
        """Clean up expired tokens."""
        now = datetime.now()
        expired = [t for t, exp in self.tokens.items() if exp < now]
        for t in expired:
            del self.tokens[t]


# Global security instance
security_middleware = SecurityMiddleware()
csrf_protection = CSRFProtection(secrets.token_urlsafe(32))
input_validator = InputValidator()