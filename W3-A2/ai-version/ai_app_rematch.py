"""
Stage 6 (Bonus — The AI Rematch): Rematch AI Version (v2) in Quarantine.
Generated after refining our prompt to explicitly specify:
- Override FastAPI's 422 RequestValidationError to return 400 with {"error": "..."}
- Return {"error": "Task not found"} instead of {"detail": "..."} on 404
- Cast SQLite's 0/1 integer column back to Python bool in JSON responses
- Use modern FastAPI lifespan instead of deprecated @app.on_event("startup")
"""

from contextlib import asynccontextmanager, contextmanager
import sqlite3
from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

DB_FILE = "tasks.db"


@contextmanager
def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def format_row(row: sqlite3.Row) -> dict:
    return {"id": row["id"], "title": row["title"], "done": bool(row["done"])}


@asynccontextmanager
async def lifespan(app: FastAPI):
    with get_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                done BOOLEAN NOT NULL DEFAULT 0
            )
            """
        )
        count = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
        if count == 0:
            conn.executemany(
                "INSERT INTO tasks (title, done) VALUES (?, ?)",
                [
                    ("Buy groceries", 0),
                    ("Learn SQLite fundamentals", 0),
                    ("Connect CRUD API to database", 0),
                ],
            )
    yield


app = FastAPI(lifespan=lifespan)


@app.exception_handler(RequestValidationError)
async def handle_validation_error(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=400, content={"error": "Invalid request body"})


class TaskPayload(BaseModel):
    title: str = Field(..., min_length=1)
    done: bool = False


@app.get("/tasks")
def list_tasks():
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM tasks").fetchall()
        return [format_row(r) for r in rows]


@app.get("/tasks/{task_id}")
def get_task(task_id: int):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if not row:
            return JSONResponse(status_code=404, content={"error": "Task not found"})
        return format_row(row)


@app.post("/tasks", status_code=201)
def create_task(payload: TaskPayload):
    if not payload.title.strip():
        return JSONResponse(status_code=400, content={"error": "Title cannot be whitespace"})
    with get_db() as conn:
        row = conn.execute(
            "INSERT INTO tasks (title, done) VALUES (?, ?) RETURNING *",
            (payload.title.strip(), int(payload.done)),
        ).fetchone()
        return format_row(row)


@app.put("/tasks/{task_id}")
def update_task(task_id: int, payload: TaskPayload):
    if not payload.title.strip():
        return JSONResponse(status_code=400, content={"error": "Title cannot be whitespace"})
    with get_db() as conn:
        row = conn.execute(
            "UPDATE tasks SET title = ?, done = ? WHERE id = ? RETURNING *",
            (payload.title.strip(), int(payload.done), task_id),
        ).fetchone()
        if not row:
            return JSONResponse(status_code=404, content={"error": "Task not found"})
        return format_row(row)


@app.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: int):
    with get_db() as conn:
        cur = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        if cur.rowcount == 0:
            return JSONResponse(status_code=404, content={"error": "Task not found"})
        return Response(status_code=204)
