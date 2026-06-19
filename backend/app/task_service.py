"""
task_service.py
---------------
Business logic for creating, listing, and completing tasks.
Tasks are stored separately from goals and memories.
"""

from sqlalchemy import func
from sqlalchemy.orm import Session

from . import models


def add_task(db: Session, title: str) -> models.Task:
    """Create an active task, or return an existing matching task."""
    cleaned_title = title.strip(" \t\r\n.,!?;:")
    existing_task = (
        db.query(models.Task)
        .filter(func.lower(models.Task.title) == cleaned_title.lower())
        .first()
    )
    if existing_task:
        return existing_task

    task = models.Task(title=cleaned_title, status="active")
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def get_tasks(db: Session) -> list[models.Task]:
    """Return all tasks, newest first."""
    return db.query(models.Task).order_by(models.Task.created_at.desc()).all()


def complete_task(db: Session, query: str) -> models.Task | None:
    """Mark the first matching active task as completed."""
    cleaned_query = query.strip(" \t\r\n.,!?;:")
    task = (
        db.query(models.Task)
        .filter(models.Task.title.ilike(f"%{cleaned_query}%"))
        .filter(models.Task.status == "active")
        .order_by(models.Task.created_at.desc())
        .first()
    )
    if not task:
        return None

    task.status = "completed"
    db.commit()
    db.refresh(task)
    return task


def complete_task_by_id(db: Session, task_id: int) -> models.Task | None:
    """Mark a task as completed by id."""
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        return None

    task.status = "completed"
    db.commit()
    db.refresh(task)
    return task
