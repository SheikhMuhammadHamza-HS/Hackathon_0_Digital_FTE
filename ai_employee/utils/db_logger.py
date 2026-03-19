import logging
from datetime import datetime
from typing import Any, Dict, Optional
from ai_employee.api.database import SessionLocal
from ai_employee.api.models import AuditLogDB

logger = logging.getLogger(__name__)

def log_agent_activity(event_type: str, details: Dict[str, Any], user_id: str = "system_agent"):
    """
    Log agent activity to the AuditLogDB.
    This allows agents (Gmail, Odoo, etc.) to show up on the dashboard.
    """
    db = SessionLocal()
    try:
        log_entry = AuditLogDB(
            event_type=event_type,
            user_id=user_id,
            details=details,
            timestamp=datetime.utcnow(),
            ip_address="internal"
        )
        db.add(log_entry)
        db.commit()
    except Exception as e:
        logger.error(f"Failed to log agent activity to DB: {e}")
        db.rollback()
    finally:
        db.close()
