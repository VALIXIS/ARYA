"""
Task Service for ARYA — Manages user To-Do tasks, status tracking, and priority.
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from .models import Task
from .database import SessionLocal


def create_task(title: str, db: Session = None) -> Dict[str, Any]:
    """Create a new task in the database."""
    close = False
    if db is None:
        db = SessionLocal()
        close = True

    try:
        task = Task(title=title.strip(), status="active")
        db.add(task)
        db.commit()
        db.refresh(task)
        return {"id": task.id, "title": task.title, "status": task.status, "created_at": str(task.created_at)}
    finally:
        if close:
            db.close()


def list_tasks(status: Optional[str] = "active", db: Session = None) -> List[Dict[str, Any]]:
    """List tasks, optionally filtered by status ('active', 'completed', or 'all')."""
    close = False
    if db is None:
        db = SessionLocal()
        close = True

    try:
        query = db.query(Task)
        if status and status.lower() != "all":
            query = query.filter(Task.status == status.lower())
        tasks = query.order_by(Task.id.desc()).all()
        return [{"id": t.id, "title": t.title, "status": t.status, "created_at": str(t.created_at)} for t in tasks]
    finally:
        if close:
            db.close()


def complete_task(task_identifier: str, db: Session = None) -> Dict[str, Any]:
    """Mark a task as completed by ID or substring matching."""
    close = False
    if db is None:
        db = SessionLocal()
        close = True

    try:
        # Search by ID if numeric
        task = None
        if task_identifier.isdigit():
            task = db.query(Task).filter(Task.id == int(task_identifier)).first()

        if not task:
            # Substring match
            task = db.query(Task).filter(Task.title.ilike(f"%{task_identifier}%")).first()

        if not task:
            return {"success": False, "error": f"Task matching '{task_identifier}' not found."}

        task.status = "completed"
        db.commit()
        return {"success": True, "task": {"id": task.id, "title": task.title, "status": "completed"}}
    finally:
        if close:
            db.close()


def delete_task(task_identifier: str, db: Session = None) -> Dict[str, Any]:
    """Delete a task by ID or title substring."""
    close = False
    if db is None:
        db = SessionLocal()
        close = True

    try:
        task = None
        if task_identifier.isdigit():
            task = db.query(Task).filter(Task.id == int(task_identifier)).first()

        if not task:
            task = db.query(Task).filter(Task.title.ilike(f"%{task_identifier}%")).first()

        if not task:
            return {"success": False, "error": f"Task matching '{task_identifier}' not found."}

        db.delete(task)
        db.commit()
        return {"success": True, "deleted_task": task.title}
    finally:
        if close:
            db.close()
