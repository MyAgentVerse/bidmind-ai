"""
Database configuration and session management.
Provides SQLAlchemy engine, session factory, and dependency injection.
"""

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool, QueuePool
from .config import get_settings
import logging

logger = logging.getLogger(__name__)

settings = get_settings()

# Create database engine
# Use QueuePool for production with connection pooling and recycling
# Use NullPool for SQLite development
if "sqlite" in settings.database_url:
    engine = create_engine(
        settings.database_url,
        echo=settings.debug,
        poolclass=NullPool,
        connect_args={"check_same_thread": False}
    )
else:
    engine = create_engine(
        settings.database_url,
        echo=settings.debug,
        pool_size=10,
        max_overflow=20,
        pool_recycle=3600,  # Recycle connections after 1 hour
        pool_pre_ping=True,  # Test connection before using it
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

    Note: The Procfile runs ``alembic upgrade head`` BEFORE the server
    starts, so migrations handle table creation. This function is a
    safety net that creates any tables Alembic missed.

    Phase 3 added pgvector support. We must enable the extension
    before ``create_all`` tries to create the ``document_embeddings``
    table with its ``VECTOR(1536)`` column.
    """
    from app.db.base import Base
    from sqlalchemy import text

    try:
        # Enable pgvector extension before creating tables that use it
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()
    except Exception as e:
        logger.warning(
            f"Could not enable pgvector extension (non-fatal): {e}. "
            f"The document_embeddings table may not be created by "
            f"create_all, but Alembic migration 012 handles it."
        )

    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        # Don't crash the server — Alembic already created the tables.
        # This only happens if create_all encounters an issue with a
        # type (like vector) that the DB doesn't support yet.
