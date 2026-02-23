"""User guidance and help system for AI Employee."""

from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
from enum import Enum

class GuidanceCategory(Enum):
    """Categories of user guidance."""
    GETTING_STARTED = "getting_started"
    TROUBLESHOOTING = "troubleshooting"
    BEST_PRACTICES = "best_practices"
    FAQ = "faq"
    ERROR_RESOLUTION = "error_resolution"


class UserGuide:
    """Comprehensive user guidance system."""

    def __init__(self):
        self.guidance = {
            GuidanceCategory.GETTING_STARTED: {
                "title": "Getting Started with AI Employee",
                "sections": [
                    {
                        "name": "Initial Setup",
                        "content": [
                            "Ensure all directories in ~/Vault are created",
                            "Configure your .env file with required credentials",
                            "Test individual service connections",
                            "Run integration tests to verify setup"
                        ]
                    },
                    {
                        "name": "First Week Operations",
                        "content": [
                            "Monitor the system logs daily",
                            "Review all approval requests in Pending_Approval",
                            "Check CEO briefing on Monday morning",
                            "Verify social media posts are scheduled correctly"
                        ]
                    }
                ]
            },
            GuidanceCategory.TROUBLESHOOTING: {
                "title": "Troubleshooting Guide",
                "common_issues": [
                    {
                        "problem": "Odoo connection failed",
                        "symptoms": ["Invoice creation errors", "Payment reconciliation failures"],
                        "solutions": [
                            "Check Odoo server is running",
                            "Verify database credentials in .env",
                            "Test with curl: curl http://your-odoo-url:8069",
                            "Check Odoo user permissions"
                        ]
                    },
                    {
                        "problem": "Social media posts not publishing",
                        "symptoms": ["Posts stuck in queue", "Authentication errors"],
                        "solutions": [
                            "Refresh API tokens for affected platforms",
                            "Check rate limiting status",
                            "Verify platform developer console settings",
                            "Re-authenticate with platforms"
                        ]
                    },
                    {
                        "problem": "CEO briefing not generated",
                        "symptoms": ["No briefing file on Monday", "Scheduler errors"],
                        "solutions": [
                            "Check scheduler status: GET /api/v1/schedule/status",
                            "Verify data sources are accessible",
                            "Check logs for briefing generation errors",
                            "Manually trigger briefing generation"
                        ]
                    },
                    {
                        "problem": "Email notifications not sending",
                        "symptoms": ["No email alerts", "SMTP errors"],
                        "solutions": [
                            "Verify SMTP settings in .env",
                            "Use app-specific password for Gmail",
                            "Check email provider security settings",
                            "Test SMTP connection manually"
                        ]
                    }
                ]
            },
            GuidanceCategory.BEST_PRACTICES: {
                "title": "Best Practices",
                "recommendations": [
                    {
                        "area": "Daily Operations",
                        "tips": [
                            "Review Pending_Approval folder twice daily",
                            "Monitor system health via /api/v1/health",
                            "Keep backup of critical configuration files",
                            "Document any manual interventions"
                        ]
                    },
                    {
                        "area": "Security",
                        "tips": [
                            "Rotate API keys quarterly",
                            "Use environment variables for all secrets",
                            "Enable two-factor authentication on all platforms",
                            "Regularly review access logs"
                        ]
                    },
                    {
                        "area": "Performance",
                        "tips": [
                            "Archive old briefing files monthly",
                            "Monitor disk space in Vault directory",
                            "Optimize database queries for large datasets",
                            "Use rate limiting to avoid API throttling"
                        ]
                    },
                    {
                        "area": "Data Management",
                        "tips": [
                            "Implement 2-year data retention policy",
                            "Regular backup of Vault directory",
                            "Validate data integrity weekly",
                            "Monitor for duplicate records"
                        ]
                    }
                ]
            },
            GuidanceCategory.FAQ: {
                "title": "Frequently Asked Questions",
                "questions": [
                    {
                        "q": "How often should I check the system?",
                        "a": "Check twice daily for approvals and once daily for health status. CEO briefings are automatically generated on Mondays."
                    },
                    {
                        "q": "What happens if the system goes down?",
                        "a": "The system includes automatic error recovery and will queue operations. Critical issues will generate alerts for manual intervention."
                    },
                    {
                        "q": "Can I customize the briefing schedule?",
                        "a": "Yes, use the /api/v1/schedule/briefing endpoint or modify the scheduler configuration in briefing_scheduler.py"
                    },
                    {
                        "q": "How secure are my financial details?",
                        "a": "All sensitive data is encrypted at rest, API credentials are stored in environment variables, and human approval is required for financial transactions."
                    },
                    {
                        "q": "What's the retention policy for data?",
                        "a": "Default is 2 years for all business data. This can be configured via DATA_RETENTION_DAYS in your environment."
                    }
                ]
            },
            GuidanceCategory.ERROR_RESOLUTION: {
                "title": "Error Resolution Guide",
                "error_codes": {
                    "CONF_001": {
                        "message": "Configuration file missing or invalid",
                        "resolution": [
                            "Check .env file exists in ai_employee directory",
                            "Verify all required variables are set",
                            "Refer to .env.example for format"
                        ]
                    },
                    "AUTH_001": {
                        "message": "Authentication failed for external service",
                        "resolution": [
                            "Refresh API tokens",
                            "Check platform developer console",
                            "Verify callback URLs",
                            "Ensure app has required permissions"
                        ]
                    },
                    "RATE_001": {
                        "message": "API rate limit exceeded",
                        "resolution": [
                            "Wait for rate limit reset",
                            "Check platform rate limits",
                            "Implement request throttling",
                            "Consider upgrading API plan"
                        ]
                    },
                    "DATA_001": {
                        "message": "Data validation failed",
                        "resolution": [
                            "Check input data format",
                            "Verify required fields",
                            "Consult API documentation",
                            "Contact support for schema issues"
                        ]
                    },
                    "PERM_001": {
                        "message": "Insufficient permissions",
                        "resolution": [
                            "Check file/directory permissions",
                            "Run with appropriate user privileges",
                            "Verify Vault directory structure",
                            "Check service account permissions"
                        ]
                    }
                }
            }
        }

    def get_guidance(self, category: Union[GuidanceCategory, str], section: Optional[str] = None) -> Dict[str, Any]:
        """Get guidance for a specific category."""
        # Handle string input
        if isinstance(category, str):
            try:
                category = GuidanceCategory(category)
            except ValueError:
                return {"error": f"Category {category} not found"}

        if category not in self.guidance:
            return {"error": f"Category {category.value} not found"}

        content = self.guidance[category]

        if section:
            if "sections" in content:
                for sec in content["sections"]:
                    if sec["name"] == section:
                        return sec
            return {"error": f"Section {section} not found in {category.value}"}

        return content

    def search_guidance(self, query: str) -> List[Dict[str, Any]]:
        """Search guidance for specific keywords."""
        results = []
        query_lower = query.lower()

        for category, content in self.guidance.items():
            if "common_issues" in content:
                for issue in content["common_issues"]:
                    if (query_lower in issue["problem"].lower() or
                        any(query_lower in symptom.lower() for symptom in issue["symptoms"])):
                        results.append({
                            "category": category.value,
                            "type": "issue",
                            "title": issue["problem"],
                            "content": issue
                        })

            if "questions" in content:
                for qa in content["questions"]:
                    if (query_lower in qa["q"].lower() or
                        query_lower in qa["a"].lower()):
                        results.append({
                            "category": category.value,
                            "type": "faq",
                            "title": qa["q"],
                            "content": qa
                        })

            if "error_codes" in content:
                for code, error in content["error_codes"].items():
                    if (query_lower in error["message"].lower() or
                        any(query_lower in step.lower() for step in error["resolution"])):
                        results.append({
                            "category": category.value,
                            "type": "error",
                            "title": f"{code}: {error['message']}",
                            "content": error
                        })

        return results

    def get_contextual_help(self, endpoint: str, method: str = "GET") -> Dict[str, Any]:
        """Get contextual help for specific API endpoints."""
        help_map = {
            "GET /api/v1/health": {
                "description": "Check system health and service status",
                "expected_response": {
                    "status": "healthy",
                    "services": {
                        "reporting": "active",
                        "scheduler": True,
                        "api": "active"
                    }
                },
                "troubleshooting": [
                    "If status is 'unhealthy', check individual services",
                    "Verify all external connections are working",
                    "Check system resources (memory, disk space)"
                ]
            },
            "POST /api/v1/briefing": {
                "description": "Generate CEO briefing for specified week",
                "required_fields": [],
                "optional_fields": ["week_start", "include_recommendations", "format"],
                "common_errors": [
                    "Invalid date format - use ISO format (YYYY-MM-DD)",
                    "Future dates not allowed - week_start must be in past",
                    "Format must be 'json' or 'markdown'"
                ]
            },
            "GET /api/v1/audit/subscriptions": {
                "description": "Get subscription audit and cost analysis",
                "expected_response": {
                    "subscriptions": "list of subscription objects",
                    "total_monthly_cost": "number",
                    "potential_savings": "number",
                    "recommendations": "list of strings"
                },
                "data_sources": [
                    "Bank transactions for recurring charges",
                    "Credit card statements",
                    "Manual subscription entries"
                ]
            }
        }

        key = f"{method} {endpoint}"
        return help_map.get(key, {
            "description": f"No specific help available for {key}",
            "general_help": "Check API documentation at /docs"
        })

    def generate_setup_checklist(self) -> Dict[str, Any]:
        """Generate a personalized setup checklist."""
        return {
            "title": "AI Employee Setup Checklist",
            "sections": [
                {
                    "name": "Prerequisites",
                    "items": [
                        {"task": "Python 3.11+ installed", "check": "python --version"},
                        {"task": "Git repository cloned", "check": "ls -la ai_employee/"},
                        {"task": "Virtual environment created", "check": "which python"},
                        {"task": "Dependencies installed", "check": "pip list | grep fastapi"}
                    ]
                },
                {
                    "name": "Configuration",
                    "items": [
                        {"task": ".env file created from .env.example", "check": "ls ai_employee/.env"},
                        {"task": "Odoo credentials configured", "check": "grep ODOO_ ai_employee/.env"},
                        {"task": "Email settings configured", "check": "grep EMAIL_ ai_employee/.env"},
                        {"task": "Social media APIs configured", "check": "grep TWITTER_ ai_employee/.env"}
                    ]
                },
                {
                    "name": "Directory Structure",
                    "items": [
                        {"task": "Vault directory created", "check": "ls -la ~/Vault"},
                        {"task": "All subdirectories exist", "check": "ls ~/Vault/"},
                        {"task": "Proper permissions set", "check": "ls -ld ~/Vault/"}
                    ]
                },
                {
                    "name": "Service Verification",
                    "items": [
                        {"task": "API server starts successfully", "check": "curl http://localhost:8000/"},
                        {"task": "Health check passes", "check": "curl http://localhost:8000/api/v1/health"},
                        {"task": "Integration tests pass", "check": "python -m pytest tests/integration/"},
                        {"task": "First briefing generated", "check": "curl -X POST http://localhost:8000/api/v1/briefing"}
                    ]
                }
            ]
        }


# Global guide instance
user_guide = UserGuide()


def get_help_for_error(error_message: str) -> Dict[str, Any]:
    """Get help suggestions based on error message."""
    error_lower = error_message.lower()

    # Configuration errors
    if any(keyword in error_lower for keyword in ["config", "env", "missing", "required"]):
        return {
            "category": "configuration",
            "suggestions": [
                "Check your .env file in ai_employee directory",
                "Ensure all required environment variables are set",
                "Compare with .env.example for missing values"
            ],
            "related_docs": ["QUICKSTART.md#Environment-Configuration"]
        }

    # Authentication errors
    if any(keyword in error_lower for keyword in ["auth", "unauthorized", "401", "token", "credential"]):
        return {
            "category": "authentication",
            "suggestions": [
                "Refresh API tokens for affected services",
                "Check platform developer console for app status",
                "Verify callback URLs and permissions",
                "Re-authenticate with social media platforms"
            ],
            "related_docs": ["QUICKSTART.md#Social-Media-APIs"]
        }

    # Network/connection errors
    if any(keyword in error_lower for keyword in ["connection", "network", "timeout", "unreachable"]):
        return {
            "category": "network",
            "suggestions": [
                "Check internet connectivity",
                "Verify service URLs are correct",
                "Check firewall settings",
                "Try again after a few minutes"
            ]
        }

    # Permission errors
    if any(keyword in error_lower for keyword in ["permission", "access denied", "forbidden", "403"]):
        return {
            "category": "permissions",
            "suggestions": [
                "Check file/directory permissions",
                "Ensure Vault directory structure exists",
                "Run with appropriate user privileges",
                "Check service account permissions"
            ]
        }

    # Default help
    return {
        "category": "general",
        "suggestions": [
            "Check system logs for detailed error information",
            "Try the operation again",
            "Contact support with error details",
            "Check troubleshooting guide in documentation"
        ]
    }