"""
database.py
------------
Sets up the SQLite database connection using SQLAlchemy.
This is the single place where ARYA configures how it talks to its database.
"""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./arya.db")

# check_same_thread=False is required for SQLite when used with FastAPI,
# because FastAPI may use the connection across different threads.
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """
    FastAPI dependency that provides a database session to each request
    and guarantees it is closed afterwards.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
