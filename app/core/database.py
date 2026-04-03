"""
Database configuration and session management.
Provides SQLAlchemy engine, session factory, and dependency injection.
"""

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool
from .config import get_settings
import logging

logger = logging.getLogger(__name__)

settings = get_settings()

# Create database engine
# Using NullPool for SQLite compatibility and simple deployments
# Switch to QueuePool for production with connection pooling
engine = create_engine(
    settings.database_url,
    echo=settings.debug,
    poolclass=NullPool,  # Use QueuePool in production
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {}
)

# Create session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False
)


def get_db() -> Session:
    """
    Dependency injection function to get database session.
    Yields a session that is automatically closed after use.

    Usage in routes:
        @router.get("/projects")
        def get_projects(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        db.rollback()
        logger.error(f"Database session error: {str(e)}", exc_info=True)
        raise
    finally:
        db.close()


def init_db():
    """
    Initialize database by creating all tables.
    This should be called once during application startup.
    In production, use Alembic migrations instead.
    """
    from app.db.base import Base
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully")
