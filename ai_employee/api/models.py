from sqlalchemy import Column, Integer, String, Enum, DateTime, JSON
from .database import Base
from ..utils.security import SecurityLevel
import datetime

class UserDB(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True) # This will be the email as per latest request
    email = Column(String, unique=True, index=True)
    full_name = Column(String)
    hashed_password = Column(String)
    level = Column(String, default=SecurityLevel.USER.value)
    permissions = Column(JSON, default=[])
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    last_login = Column(DateTime, nullable=True)

class AuditLogDB(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String)
    user_id = Column(String)
    details = Column(JSON)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    ip_address = Column(String)
