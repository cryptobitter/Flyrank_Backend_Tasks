"""
Stage 1: Read endpoints (GET /tasks and GET /tasks/{id}) backed by SQLite.
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
