"""
Stage 2: SQLite database layer with read and create queries (INSERT INTO tasks).
"""

import os
import sqlite3
from typing import Any

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("TASKS_DB_PATH", os.path.join(BASE_DIR, "tasks.db"))

SEED_TASKS = [
    ("Buy groceries", 0),
    ("Learn SQLite fundamentals", 0),
    ("Connect CRUD API to database", 0),
]


def get_connection(db_path: str | None = None) -> sqlite3.Connection:
    """Open a connection to the SQLite database file (creating it if missing)."""
    target_path = db_path or DB_PATH
    conn = sqlite3.connect(target_path)
    conn.row_factory = sqlite3.Row
    return conn


def row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    """Convert a sqlite3.Row into a task dictionary with boolean 'done'."""
    data = dict(row)
    data["done"] = bool(data["done"])
    return data


def init_db(db_path: str | None = None) -> None:
    """
    Create the 'tasks' table if it does not already exist, and insert three
    example tasks ONLY when the table is empty (count == 0).
    """
    conn = get_connection(db_path)
    try:
        with conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    done BOOLEAN NOT NULL DEFAULT 0
                )
                """
            )
            cursor = conn.execute("SELECT COUNT(*) AS count FROM tasks")
            row_count = cursor.fetchone()["count"]
            if row_count == 0:
                conn.executemany(
                    "INSERT INTO tasks (title, done) VALUES (?, ?)",
                    SEED_TASKS,
                )
    finally:
        conn.close()


def get_all_tasks(db_path: str | None = None) -> list[dict[str, Any]]:
    """Return every task from the database using SELECT * FROM tasks."""
    conn = get_connection(db_path)
    try:
        cursor = conn.execute("SELECT * FROM tasks")
        rows = cursor.fetchall()
        return [row_to_dict(row) for row in rows]
    finally:
        conn.close()


def get_task_by_id(task_id: int, db_path: str | None = None) -> dict[str, Any] | None:
    """Fetch a single task by id using a parameterized query placeholder (?)."""
    conn = get_connection(db_path)
    try:
        cursor = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        row = cursor.fetchone()
        return row_to_dict(row) if row is not None else None
    finally:
        conn.close()


def create_task(title: str, done: bool = False, db_path: str | None = None) -> dict[str, Any]:
    """Insert a new task row using parameterized INSERT INTO tasks (title, done) VALUES (?, ?)."""
    conn = get_connection(db_path)
    try:
        with conn:
            cursor = conn.execute(
                "INSERT INTO tasks (title, done) VALUES (?, ?)",
                (title, 1 if done else 0),
            )
            new_id = cursor.lastrowid
            row = conn.execute("SELECT * FROM tasks WHERE id = ?", (new_id,)).fetchone()
            return row_to_dict(row)
    finally:
        conn.close()
