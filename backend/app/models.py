"""
models.py
---------
Defines ARYA's database tables using SQLAlchemy's ORM.
"""

from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.sql import func

from .database import Base


class Memory(Base):
    """A single stored memory."""

    __tablename__ = "memories"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(String, nullable=False)
    category = Column(String, nullable=False, default="Other")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Conversation(Base):
    """A single message in the chat conversation."""

    __tablename__ = "conversation"

    id = Column(Integer, primary_key=True, index=True)
    role = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Goal(Base):
    """A user goal tracked separately from memories."""

    __tablename__ = "goals"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    status = Column(String, nullable=False, default="active")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Task(Base):
    """A user task tracked separately from goals and memories."""

    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    status = Column(String, nullable=False, default="active")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class DeviceNode(Base):
    """A connected hardware or IoT device node."""

    __tablename__ = "device_nodes"

    id = Column(Integer, primary_key=True, index=True)
    node_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    device_type = Column(String, nullable=False, default="laptop")  # laptop, mobile, smarthome, light, tv, ac
    status = Column(String, nullable=False, default="offline")      # online, offline, busy
    ip_address = Column(String, nullable=True)
    capabilities = Column(Text, nullable=False, default="[]")       # JSON list of supported actions
    state_data = Column(Text, nullable=False, default="{}")         # JSON object of current device state
    last_seen = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())



class ScheduledRoutine(Base):
    """An autonomous background cron routine."""

    __tablename__ = "scheduled_routines"

    id = Column(Integer, primary_key=True, index=True)
    cron_expr = Column(String, nullable=False) # e.g. "0 8 * * *"
    command = Column(String, nullable=False)   # e.g. "turn on tv"
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
