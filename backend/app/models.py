"""
models.py
---------
Defines ARYA's database tables using SQLAlchemy's ORM.
For Day 1, ARYA only needs one table: Memory.
"""

from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func

from .database import Base


class Memory(Base):
    """A single stored memory."""

    __tablename__ = "memories"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
