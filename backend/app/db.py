from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
import os
from pathlib import Path
from dotenv import load_dotenv


_env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(_env_path)

SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///gravel.db")


if SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)
elif SQLALCHEMY_DATABASE_URL.startswith("postgresql://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)

connect_args = {}
if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

#for self will delete later : For Neon, we need sslmode=require
engine_kwargs = {}
if "neon" in SQLALCHEMY_DATABASE_URL or "psycopg2" in SQLALCHEMY_DATABASE_URL:
    engine_kwargs["pool_pre_ping"] = True

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args=connect_args, **engine_kwargs
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_tables():
    """Create all tables in the database. Called on app startup."""
    Base.metadata.create_all(bind=engine)
