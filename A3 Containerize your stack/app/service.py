"""
Domain Service Layer (`TaskService`).
Strictly depends on the `TaskRepository` abstraction.
Contains ZERO database imports or SQL strings — completely unchanged when swapping
`InMemoryTaskRepository` for `PostgresTaskRepository`.
"""

from typing import Any, Dict, List, Optional
from app.repository import TaskRepository


class ValidationError(ValueError):
    """Raised when incoming task payload fails domain validation."""


class TaskService:
    """Business logic layer orchestrating task operations via TaskRepository."""

    def __init__(self, repo: TaskRepository) -> None:
        self.repo = repo

    def list_tasks(self) -> List[Dict[str, Any]]:
        return self.repo.get_all()

    def get_task(self, task_id: int) -> Optional[Dict[str, Any]]:
        return self.repo.get_by_id(task_id)

    def create_task(self, title: Any, done: Any = False) -> Dict[str, Any]:
        if not isinstance(title, str) or not title.strip():
            raise ValidationError("Title is required and cannot be empty")
        if not isinstance(done, bool):
            raise ValidationError("Field 'done' must be a boolean")
        return self.repo.create(title=title.strip(), done=done)

    def update_task(
        self,
        task_id: int,
        title: Any = None,
        done: Any = None,
    ) -> Optional[Dict[str, Any]]:
        if title is None and done is None:
            raise ValidationError("At least one of 'title' or 'done' must be provided")
        if title is not None and (not isinstance(title, str) or not title.strip()):
            raise ValidationError("Title must be a non-empty string")
        if done is not None and not isinstance(done, bool):
            raise ValidationError("Field 'done' must be a boolean")

        clean_title = title.strip() if isinstance(title, str) else None
        return self.repo.update(task_id=task_id, title=clean_title, done=done)

    def delete_task(self, task_id: int) -> bool:
        return self.repo.delete(task_id)
