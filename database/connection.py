"""
Database connection management.
Provides SQLAlchemy engine, session factory, and database initialization.
"""

import logging
from typing import Optional

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool

from config.settings import settings
from database.models import Base

logger = logging.getLogger(__name__)

_engine = None
_SessionFactory = None


def get_engine():
    """
    Get or create the SQLAlchemy engine.
    Uses a connection pool for efficient database access.
    """
    global _engine
    if _engine is None:
        _engine = create_engine(
            settings.DATABASE_URL,
            poolclass=QueuePool,
            pool_size=5,
            max_overflow=10,
            pool_timeout=30,
            pool_recycle=3600,
            echo=False,
        )
        logger.info("Database engine created.")
    return _engine


def get_session() -> Session:
    """
    Get a new database session.
    Must be closed after use.

    Usage:
        session = get_session()
        try:
            # do work
            session.commit()
        except:
            session.rollback()
            raise
        finally:
            session.close()
    """
    global _SessionFactory
    if _SessionFactory is None:
        _SessionFactory = sessionmaker(bind=get_engine())
    return _SessionFactory()


def init_database():
    """
    Initialize the database.
    Creates all tables if they don't exist.
    """
    engine = get_engine()
    try:
        Base.metadata.create_all(engine)
        logger.info("Database tables created/verified successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


def check_connection() -> bool:
    """
    Check if the database is accessible.
    Returns True if connection is successful.
    """
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Database connection verified.")
        return True
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False
