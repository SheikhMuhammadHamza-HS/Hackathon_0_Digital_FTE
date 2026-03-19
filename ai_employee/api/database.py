import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Find project root (where .env usually lives)
base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
env_path = os.path.join(base_dir, ".env")
load_dotenv(env_path)

# Use Neon PostgreSQL connection string from environment variables
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")

# Neon/SQLAlchemy compatibility fix: replace postgresql:// with postgresql+psycopg2:// if needed
if SQLALCHEMY_DATABASE_URL and SQLALCHEMY_DATABASE_URL.startswith("postgresql://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)

if not SQLALCHEMY_DATABASE_URL:
    # Fallback for development (sqlite) if no URL provided
    SQLALCHEMY_DATABASE_URL = "sqlite:///./sql_app.db"
    print("WARNING: DATABASE_URL not found, using SQLite fallback.")

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=True,  # Check connectivity before using a connection
    pool_recycle=300     # Recycle connections every 5 minutes
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
