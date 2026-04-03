"""
Base model classes and declarative base for SQLAlchemy ORM.
All models inherit from Base to ensure table creation works properly.
"""

from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, DateTime
from datetime import datetime

# Create declarative base for all models
Base = declarative_base()


class BaseModel(Base):
    """
    Abstract base model with common fields.
    All models should inherit from this.
    """

    __abstract__ = True

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, index=True)

    def to_dict(self):
        """Convert model instance to dictionary."""
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
