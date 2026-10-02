"""
Stage 2: Read and Create endpoints (GET /tasks, GET /tasks/{id}, POST /tasks).
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
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


@app.get("/tasks")
def read_tasks():
    return database.get_all_tasks()


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
