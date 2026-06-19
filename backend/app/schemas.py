"""
schemas.py
----------
Pydantic models that define the shape of data going into and out of
the API. FastAPI uses these for validation, parsing, and documentation.
"""

from datetime import datetime
from pydantic import BaseModel


class MemoryCreate(BaseModel):
    """Data required to create a new memory."""
    content: str
    category: str = "Other"


class MemoryResponse(BaseModel):
    """Data returned to the client for a stored memory."""
    id: int
    content: str
    category: str
    created_at: datetime

    class Config:
        from_attributes = True  # lets this model read directly from SQLAlchemy objects


class ChatRequest(BaseModel):
    """Data required to send a message to the AI."""
    message: str


class ChatResponse(BaseModel):
    """The AI's reply."""
    reply: str


class TaskCreate(BaseModel):
    """Data required to create a task."""
    title: str


class TaskResponse(BaseModel):
    """Data returned to the client for a task."""
    id: int
    title: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class GoalResponse(BaseModel):
    """Data returned to the client for a goal."""
    id: int
    title: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class NewsHeadline(BaseModel):
    """One news headline."""
    title: str
    link: str
    source: str


class NewsResponse(BaseModel):
    """Structured news payload for GET /news."""
    ai_news: list[NewsHeadline]
    technology_news: list[NewsHeadline]
    cached: bool
    last_updated: str | None
