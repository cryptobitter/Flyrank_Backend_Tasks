"""
Domain and Request/Response Models for the Task Service.
Shared identically across InMemoryTaskRepository and PostgresTaskRepository.
"""

from typing import Optional
from pydantic import BaseModel


class TaskCreate(BaseModel):
    title: str
    done: bool = False


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    done: Optional[bool] = None


class Task(BaseModel):
    id: int
    title: str
    done: bool
