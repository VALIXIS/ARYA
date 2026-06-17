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


class MemoryResponse(BaseModel):
    """Data returned to the client for a stored memory."""
    id: int
    content: str
    created_at: datetime

    class Config:
        from_attributes = True  # lets this model read directly from SQLAlchemy objects


class ChatRequest(BaseModel):
    """Data required to send a message to the AI."""
    message: str


class ChatResponse(BaseModel):
    """The AI's reply."""
    reply: str
