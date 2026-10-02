"""
Stage 6 (Bonus — The AI Rematch): Initial AI-Generated Version (v1) in Quarantine.
Generated from our first-pass specification prompt.

Notable differences discovered during code review & diff against our hand-built version:
1. What it did well: Used a context-manager helper `@contextmanager def get_db()` and `RETURNING *` on INSERT/UPDATE.
2. What it got wrong / quietly ignored:
   - Relying on FastAPI's default Pydantic validation caused invalid POST/PUT bodies to return
     422 Unprocessable Entity with `{"detail": ...}` instead of the required 400 Bad Request with `{"error": ...}`.
   - Raising standard `HTTPException(status_code=404, detail="Task not found")` returned `{"detail": "Task not found"}`
     instead of `{"error": "Task not found"}`.
   - Returning raw `dict(row)` from `sqlite3.Row` serialized `done` as integer `0` / `1` instead of boolean `false` / `true`.
"""

from contextlib import contextmanager
import sqlite3
from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel, Field

app = FastAPI()
DB_FILE = "tasks.db"


@contextmanager
def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


class TaskPayload(BaseModel):
    title: str = Field(..., min_length=1)
    done: bool = False


@app.on_event("startup")
def startup():
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


@app.get("/tasks")
def list_tasks():
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM tasks").fetchall()
        return [dict(r) for r in rows]


@app.get("/tasks/{task_id}")
def get_task(task_id: int):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Task not found")
        return dict(row)


@app.post("/tasks", status_code=201)
def create_task(payload: TaskPayload):
    with get_db() as conn:
        row = conn.execute(
            "INSERT INTO tasks (title, done) VALUES (?, ?) RETURNING *",
            (payload.title, int(payload.done)),
        ).fetchone()
        return dict(row)


@app.put("/tasks/{task_id}")
def update_task(task_id: int, payload: TaskPayload):
    with get_db() as conn:
        row = conn.execute(
            "UPDATE tasks SET title = ?, done = ? WHERE id = ? RETURNING *",
            (payload.title, int(payload.done), task_id),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Task not found")
        return dict(row)


@app.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: int):
    with get_db() as conn:
        cur = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Task not found")
        return Response(status_code=204)
