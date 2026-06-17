"""
main.py
-------
Entry point for the ARYA Memory v0.1 backend. Defines the FastAPI app
and wires together the database, memory service, and AI service into
HTTP endpoints.

Endpoints:
    POST /memory          -> store a new memory
    GET  /memory          -> get all memories
    GET  /memory/search   -> search memories by keyword (?q=...)
    POST /chat            -> send a message to the local Ollama model
"""

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session

from . import models, schemas, memory_service, ai_service
from .database import engine, get_db

# Create database tables on startup if they don't already exist.
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="ARYA Memory v0.1")


@app.post("/memory", response_model=schemas.MemoryResponse)
def create_memory(memory: schemas.MemoryCreate, db: Session = Depends(get_db)):
    """Store a new memory."""
    return memory_service.save_memory(db, memory)


@app.get("/memory", response_model=list[schemas.MemoryResponse])
def list_memories(db: Session = Depends(get_db)):
    """Get all stored memories, newest first."""
    return memory_service.get_all_memories(db)


@app.get("/memory/search", response_model=list[schemas.MemoryResponse])
def search_memory(q: str, db: Session = Depends(get_db)):
    """Search memories containing the keyword 'q'."""
    return memory_service.search_memories(db, q)


@app.post("/chat", response_model=schemas.ChatResponse)
def chat(request: schemas.ChatRequest):
    """Send a message to the local Ollama model (qwen3:8b) and return its reply."""
    try:
        reply = ai_service.ask_ai(request.message)
        return schemas.ChatResponse(reply=reply)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI service error: {e}")
