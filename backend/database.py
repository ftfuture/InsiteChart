"""
Database configuration and session management for InsiteChart platform.
"""

from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .config import get_settings
import sys
import os

# Get settings
settings = get_settings()

# Use SQLite for development environment if PostgreSQL is not available
database_url = settings.database_url
if database_url.startswith("postgresql://"):
    # Check if we're in development mode and use SQLite instead
    if settings.debug:
        print("Development mode detected: Using SQLite instead of PostgreSQL")
        database_url = "sqlite:///./insitechart_dev.db"
    else:
        print("Production mode: Attempting to use PostgreSQL")
        # Keep the original PostgreSQL URL for production

# Create database engine
if database_url.startswith("sqlite"):
    engine = create_engine(
        database_url,
        echo=settings.debug,
        connect_args={"check_same_thread": False}  # SQLite specific
    )
else:
    engine = create_engine(
        database_url,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        echo=settings.debug
    )

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()

# Metadata for migrations
metadata = MetaData()


def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """Create all database tables."""
    Base.metadata.create_all(bind=engine)


def drop_tables():
    """Drop all database tables."""
    Base.metadata.drop_all(bind=engine)