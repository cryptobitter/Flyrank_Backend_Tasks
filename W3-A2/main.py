"""
W3 · A2 — Connecting Your CRUD to the Database (FastAPI + SQLite)
Exposes the exact same CRUD endpoints as Assignment 1 (GET /tasks, GET /tasks/{id},
POST /tasks, PUT /tasks/{id}, DELETE /tasks/{id}) plus optional query filters and GET /stats.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
import database


@asynccontextmanager
async def lifespan(app: FastAPI):
    database.init_db()
    yield


app = FastAPI(title="Task CRUD API (SQLite)", lifespan=lifespan)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=400, content={"error": "Invalid request parameters or body"})


def _parse_bool_query(value: str | None) -> tuple[bool | None, bool]:
    """Parse ?done=true/false query parameter. Returns (parsed_bool, is_valid)."""
    if value is None:
        return None, True
    lowered = value.strip().lower()
    if lowered in ("true", "1", "yes"):
        return True, True
    if lowered in ("false", "0", "no"):
        return False, True
    return None, False


@app.get("/tasks")
def read_tasks(
    search: str | None = None,
    done: str | None = None,
    sort: str | None = None,
):
    parsed_done, is_valid = _parse_bool_query(done)
    if not is_valid:
        return JSONResponse(
            status_code=400,
            content={"error": "Query parameter 'done' must be 'true' or 'false'"},
        )
    return database.get_all_tasks(search=search, done=parsed_done, sort=sort)


@app.get("/stats")
def read_stats():
    """Optional Extra: Return task counts using SQL COUNT(*)."""
    return database.get_task_stats()


@app.get("/tasks/{task_id}")
def read_task(task_id: int):
    task = database.get_task_by_id(task_id)
    if task is None:
        return JSONResponse(status_code=404, content={"error": "Task not found"})
    return task


@app.post("/tasks", status_code=201)
async def create_task_endpoint(request: Request):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON body"})

    if not isinstance(body, dict):
        return JSONResponse(status_code=400, content={"error": "Request body must be a JSON object"})

    title = body.get("title")
    if not isinstance(title, str) or not title.strip():
        return JSONResponse(status_code=400, content={"error": "Title is required and cannot be empty"})

    done = body.get("done", False)
    if not isinstance(done, bool):
        return JSONResponse(status_code=400, content={"error": "Field 'done' must be a boolean"})

    created = database.create_task(title=title.strip(), done=done)
    return JSONResponse(status_code=201, content=created)


@app.put("/tasks/{task_id}")
async def update_task_endpoint(task_id: int, request: Request):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON body"})

    if not isinstance(body, dict) or ("title" not in body and "done" not in body):
        return JSONResponse(
            status_code=400,
            content={"error": "Request body must provide 'title' and/or 'done'"},
        )

    existing = database.get_task_by_id(task_id)
    if existing is None:
        return JSONResponse(status_code=404, content={"error": "Task not found"})

    title = body.get("title", existing["title"])
    done = body.get("done", existing["done"])

    if not isinstance(title, str) or not title.strip():
        return JSONResponse(status_code=400, content={"error": "Title must be a non-empty string"})
    if not isinstance(done, bool):
        return JSONResponse(status_code=400, content={"error": "Field 'done' must be a boolean"})

    updated = database.update_task(task_id=task_id, title=title.strip(), done=done)
    if updated is None:
        return JSONResponse(status_code=404, content={"error": "Task not found"})
    return updated


@app.delete("/tasks/{task_id}", status_code=204)
def delete_task_endpoint(task_id: int):
    deleted = database.delete_task(task_id)
    if not deleted:
        return JSONResponse(status_code=404, content={"error": "Task not found"})
    return Response(status_code=204)
