import os
import sys

# Add the project root to sys.path to import local modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ai_employee.api.database import engine, Base
from ai_employee.api.models import UserDB, AuditLogDB  # MUST import models so Base knows about them
from sqlalchemy import text

try:
    print("Attempting to connect to the database...")
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1"))
        print("Successfully connected to the database!")
        print("Creating tables on Neon...")
        Base.metadata.create_all(bind=engine)
        print("Tables created successfully!")
except Exception as e:
    print(f"FAILED to connect to the database: {str(e)}")
    sys.exit(1)
