"""Base database configuration and declarative base."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all database models."""
    
    pass


# Import all models here for Alembic to detect them
# This will be populated as models are created
__all__ = ["Base"]
