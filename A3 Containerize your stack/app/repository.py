"""
Repository Interface & In-Memory Repository Implementation.
Defines the strict contract (`TaskRepository`) that both `InMemoryTaskRepository`
and `PostgresTaskRepository` implement so `service.py` and `routes.py` never change.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class TaskRepository(ABC):
    """Abstract repository contract for Task persistence."""

    @abstractmethod
    def get_all(self) -> List[Dict[str, Any]]:
        """Return all tasks ordered by id."""
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, task_id: int) -> Optional[Dict[str, Any]]:
        """Return a single task by id, or None if not found."""
        raise NotImplementedError

    @abstractmethod
    def create(self, title: str, done: bool = False) -> Dict[str, Any]:
        """Create and persist a new task, returning the created task dict."""
        raise NotImplementedError

    @abstractmethod
    def update(
        self,
        task_id: int,
        title: Optional[str] = None,
        done: Optional[bool] = None,
    ) -> Optional[Dict[str, Any]]:
        """Update an existing task by id, or return None if not found."""
        raise NotImplementedError

    @abstractmethod
    def delete(self, task_id: int) -> bool:
        """Delete a task by id. Returns True if a row was deleted, False otherwise."""
        raise NotImplementedError


class InMemoryTaskRepository(TaskRepository):
    """Original A1/A2 in-memory task store implementing TaskRepository."""

    def __init__(self) -> None:
        self._tasks: List[Dict[str, Any]] = [
            {"id": 1, "title": "Run PostgreSQL in Docker with a persistent volume", "done": False},
            {"id": 2, "title": "Swap InMemoryTaskRepository for PostgresTaskRepository", "done": False},
            {"id": 3, "title": "Verify data survives container restarts", "done": False},
        ]
        self._next_id: int = 4

    def get_all(self) -> List[Dict[str, Any]]:
        return [dict(task) for task in self._tasks]

    def get_by_id(self, task_id: int) -> Optional[Dict[str, Any]]:
        for task in self._tasks:
            if task["id"] == task_id:
                return dict(task)
        return None

    def create(self, title: str, done: bool = False) -> Dict[str, Any]:
        new_task = {
            "id": self._next_id,
            "title": title,
            "done": bool(done),
        }
        self._next_id += 1
        self._tasks.append(new_task)
        return dict(new_task)

    def update(
        self,
        task_id: int,
        title: Optional[str] = None,
        done: Optional[bool] = None,
    ) -> Optional[Dict[str, Any]]:
        for task in self._tasks:
            if task["id"] == task_id:
                if title is not None:
                    task["title"] = title
                if done is not None:
                    task["done"] = bool(done)
                return dict(task)
        return None

    def delete(self, task_id: int) -> bool:
        for idx, task in enumerate(self._tasks):
            if task["id"] == task_id:
                self._tasks.pop(idx)
                return True
        return False
