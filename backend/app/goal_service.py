"""
goal_service.py
---------------
Business logic for creating, listing, and completing goals.
Goals are stored separately from memories.
"""

from sqlalchemy import func
from sqlalchemy.orm import Session

from . import models


def create_goal(db: Session, title: str) -> models.Goal:
    """Create an active goal, or return an existing matching goal."""
    cleaned_title = title.strip(" \t\r\n.,!?;:")
    existing_goal = (
        db.query(models.Goal)
        .filter(func.lower(models.Goal.title) == cleaned_title.lower())
        .first()
    )
    if existing_goal:
        return existing_goal

    goal = models.Goal(title=cleaned_title, status="active")
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return goal


def get_goals(db: Session) -> list[models.Goal]:
    """Return all goals, newest first."""
    return db.query(models.Goal).order_by(models.Goal.created_at.desc()).all()


def complete_goal(db: Session, query: str) -> models.Goal | None:
    """Mark the first matching active goal as completed."""
    cleaned_query = query.strip(" \t\r\n.,!?;:")
    goal = (
        db.query(models.Goal)
        .filter(models.Goal.title.ilike(f"%{cleaned_query}%"))
        .filter(models.Goal.status == "active")
        .order_by(models.Goal.created_at.desc())
        .first()
    )
    if not goal:
        return None

    goal.status = "completed"
    db.commit()
    db.refresh(goal)
    return goal
