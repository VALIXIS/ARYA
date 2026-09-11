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
    response_length: str | None = "Brief"


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


class DeviceNodeCreate(BaseModel):
    """Payload to register or update a device node."""
    node_id: str
    name: str
    device_type: str = "laptop"
    ip_address: str | None = None
    capabilities: list[str] = []
    state_data: dict = {}


class DeviceNodeResponse(BaseModel):
    """Device node info returned to client."""
    id: int
    node_id: str
    name: str
    device_type: str
    status: str
    ip_address: str | None = None
    capabilities: list[str] = []
    state_data: dict = {}
    last_seen: datetime | None = None

    class Config:
        from_attributes = True


class DeviceCommandRequest(BaseModel):
    """Command dispatched to a device node."""
    action: str
    params: dict = {}


class DeviceCommandResponse(BaseModel):
    """Response returned after executing a device command."""
    node_id: str
    action: str
    status: str
    result: dict | str | None = None


class GraphNode(BaseModel):
    """Node in the Memory Knowledge Graph."""
    id: str
    label: str
    category: str
    type: str  # core, category, memory, goal, task, device
    created_at: str | None = None
    detail: str | None = None
    status: str | None = None
    count: int | None = None
    raw_id: str | None = None


class GraphEdge(BaseModel):
    """Edge in the Memory Knowledge Graph."""
    id: str
    source: str
    target: str
    relationship: str


class MemoryGraphResponse(BaseModel):
    """Full Memory Knowledge Graph with nodes and links."""
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    total_memories: int
    total_goals: int
    total_tasks: int = 0
    total_devices: int = 0


