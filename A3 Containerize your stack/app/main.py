"""
Application Entrypoint & Dependency Injection Wiring (`main.py`).
This is the ONLY file that changes when swapping `InMemoryTaskRepository`
for `PostgresTaskRepository` — proving the layered architecture works.
"""

from contextlib import asynccontextmanager
import os
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
import redis

from app.postgres_repository import PostgresTaskRepository
from app.repository import InMemoryTaskRepository, TaskRepository
from app.routes import create_task_router
from app.service import TaskService

load_dotenv()


def build_repository(backend: Optional[str] = None) -> TaskRepository:
    """
    Swap storage implementation in one place:
    - 'postgres' (default): PostgresTaskRepository connected via DATABASE_URL from .env
    - 'memory': InMemoryTaskRepository (for unit testing or comparison)
    """
    selected = (backend or os.getenv("STORAGE_BACKEND", "postgres")).lower()
    if selected == "memory":
        return InMemoryTaskRepository()
    return PostgresTaskRepository(os.getenv("DATABASE_URL"))


def ping_redis() -> str:
    """Stretch Goal: Ping Redis instance configured via REDIS_URL in .env."""
    redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
    try:
        client = redis.from_url(redis_url, socket_connect_timeout=2, socket_timeout=2)
        if client.ping():
            return "PONG"
        return "NO_RESPONSE"
    except Exception as exc:
        return f"UNAVAILABLE ({type(exc).__name__})"


def create_app(repo: Optional[TaskRepository] = None) -> FastAPI:
    active_repo = repo or build_repository()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if isinstance(active_repo, PostgresTaskRepository):
            active_repo.ensure_schema()
        yield

    app = FastAPI(
        title="A3 Containerized Stack — FastAPI + PostgreSQL + Redis",
        lifespan=lifespan,
    )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(status_code=400, content={"error": "Invalid request parameters or body"})

    service = TaskService(repo=active_repo)
    app.include_router(create_task_router(service=service, redis_ping_fn=ping_redis))
    return app


app = create_app()
