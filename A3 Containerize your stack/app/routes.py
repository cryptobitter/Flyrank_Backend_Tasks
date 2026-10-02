"""
HTTP Routes Layer (`routes.py`).
Strictly calls `TaskService` methods and translates results to HTTP status codes.
Contains ZERO SQL strings or database imports — completely unchanged when swapping
`InMemoryTaskRepository` for `PostgresTaskRepository`.
"""

from typing import Callable, Optional
from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse
from app.service import TaskService, ValidationError


def create_task_router(
    service: TaskService,
    redis_ping_fn: Optional[Callable[[], str]] = None,
) -> APIRouter:
    router = APIRouter()

    @router.get("/health")
    def health_check():
        redis_status = redis_ping_fn() if redis_ping_fn else "not_configured"
        return {"status": "ok", "redis": redis_status}

    @router.get("/redis/ping")
    def redis_ping():
        """Stretch Goal: Ping Redis container from the FastAPI app."""
        pong = redis_ping_fn() if redis_ping_fn else "not_configured"
        status_code = 200 if pong == "PONG" else 503
        return JSONResponse(status_code=status_code, content={"redis": pong})

    @router.get("/tasks")
    def get_tasks():
        return service.list_tasks()

    @router.get("/tasks/{task_id}")
    def get_task(task_id: int):
        task = service.get_task(task_id)
        if task is None:
            return JSONResponse(status_code=404, content={"error": "Task not found"})
        return task

    @router.post("/tasks", status_code=201)
    async def create_task(request: Request):
        try:
            body = await request.json()
        except Exception:
            return JSONResponse(status_code=400, content={"error": "Invalid JSON body"})

        if not isinstance(body, dict):
            return JSONResponse(status_code=400, content={"error": "Request body must be a JSON object"})

        try:
            created = service.create_task(
                title=body.get("title"),
                done=body.get("done", False),
            )
            return JSONResponse(status_code=201, content=created)
        except ValidationError as exc:
            return JSONResponse(status_code=400, content={"error": str(exc)})

    @router.put("/tasks/{task_id}")
    async def update_task(task_id: int, request: Request):
        try:
            body = await request.json()
        except Exception:
            return JSONResponse(status_code=400, content={"error": "Invalid JSON body"})

        if not isinstance(body, dict):
            return JSONResponse(status_code=400, content={"error": "Request body must be a JSON object"})

        try:
            updated = service.update_task(
                task_id=task_id,
                title=body.get("title") if "title" in body else None,
                done=body.get("done") if "done" in body else None,
            )
        except ValidationError as exc:
            return JSONResponse(status_code=400, content={"error": str(exc)})

        if updated is None:
            return JSONResponse(status_code=404, content={"error": "Task not found"})
        return updated

    @router.delete("/tasks/{task_id}", status_code=204)
    def delete_task(task_id: int):
        deleted = service.delete_task(task_id)
        if not deleted:
            return JSONResponse(status_code=404, content={"error": "Task not found"})
        return Response(status_code=204)

    return router
