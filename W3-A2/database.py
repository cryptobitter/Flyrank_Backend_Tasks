"""
SQLite Storage Layer for W3-A2 CRUD Task API.
Includes:
- Automatic database file creation (tasks.db) and schema setup
- Atomic transaction for one-time seeding of 3 starter tasks
- Indexes on 'done' and 'title' for fast filtering and searching
- Parameterized SQL queries (?) for all CRUD operations
- Optional Extras: SQL LIKE search, WHERE done filter, ORDER BY title sort,
  SQL COUNT(*) statistics, and created_at / updated_at ISO-8601 timestamps.
"""

from datetime import datetime, timezone
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


def utc_now_iso() -> str:
    """Return current UTC timestamp in ISO-8601 format."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


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


def _ensure_timestamp_columns(conn: sqlite3.Connection) -> None:
    """Ensure created_at and updated_at columns exist if migrating an older tasks.db."""
    columns = {
        row["name"]
        for row in conn.execute("PRAGMA table_info(tasks)").fetchall()
    }
    now = utc_now_iso()
    if "created_at" not in columns:
        conn.execute("ALTER TABLE tasks ADD COLUMN created_at TEXT")
        conn.execute("UPDATE tasks SET created_at = ? WHERE created_at IS NULL", (now,))
    if "updated_at" not in columns:
        conn.execute("ALTER TABLE tasks ADD COLUMN updated_at TEXT")
        conn.execute("UPDATE tasks SET updated_at = ? WHERE updated_at IS NULL", (now,))


def init_db(db_path: str | None = None) -> None:
    """
    Create the 'tasks' table and indexes if they do not already exist,
    and seed three example tasks inside a single atomic transaction ONLY
    when the table is empty (count == 0).
    """
    conn = get_connection(db_path)
    try:
        # Stretch Goal: Wrap table creation, index creation, and 3-task seeding in an atomic transaction
        with conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    done BOOLEAN NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            _ensure_timestamp_columns(conn)

            # Stretch Goal: Add indexes on columns used in search/filter queries
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_done ON tasks(done)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_title ON tasks(title)")

            cursor = conn.execute("SELECT COUNT(*) AS count FROM tasks")
            row_count = cursor.fetchone()["count"]
            if row_count == 0:
                now = utc_now_iso()
                conn.executemany(
                    "INSERT INTO tasks (title, done, created_at, updated_at) VALUES (?, ?, ?, ?)",
                    [(title, done, now, now) for title, done in SEED_TASKS],
                )
    finally:
        conn.close()


def get_all_tasks(
    search: str | None = None,
    done: bool | None = None,
    sort: str | None = None,
    db_path: str | None = None,
) -> list[dict[str, Any]]:
    """
    Return tasks from the database using parameterized SQL.
    Supports Optional Extras:
    - search: SQL LIKE operator (WHERE title LIKE ?)
    - done: SQL status filter (WHERE done = ?)
    - sort: SQL alphabetical ordering (ORDER BY title COLLATE NOCASE ASC)
    """
    conn = get_connection(db_path)
    try:
        query = "SELECT * FROM tasks"
        conditions: list[str] = []
        params: list[Any] = []

        if search is not None and search != "":
            conditions.append("title LIKE ?")
            params.append(f"%{search}%")

        if done is not None:
            conditions.append("done = ?")
            params.append(1 if done else 0)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        if sort and sort.lower() in ("title", "asc", "alpha"):
            query += " ORDER BY title COLLATE NOCASE ASC, id ASC"
        elif sort and sort.lower() == "desc":
            query += " ORDER BY title COLLATE NOCASE DESC, id ASC"
        else:
            query += " ORDER BY id ASC"

        cursor = conn.execute(query, tuple(params))
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
    """Insert a new task row using parameterized INSERT INTO tasks."""
    conn = get_connection(db_path)
    try:
        now = utc_now_iso()
        with conn:
            cursor = conn.execute(
                "INSERT INTO tasks (title, done, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (title, 1 if done else 0, now, now),
            )
            new_id = cursor.lastrowid
            row = conn.execute("SELECT * FROM tasks WHERE id = ?", (new_id,)).fetchone()
            return row_to_dict(row)
    finally:
        conn.close()


def update_task(
    task_id: int,
    title: str,
    done: bool,
    db_path: str | None = None,
) -> dict[str, Any] | None:
    """Update a task row using parameterized UPDATE tasks SET title = ?, done = ?, updated_at = ? WHERE id = ?."""
    conn = get_connection(db_path)
    try:
        now = utc_now_iso()
        with conn:
            cursor = conn.execute(
                "UPDATE tasks SET title = ?, done = ?, updated_at = ? WHERE id = ?",
                (title, 1 if done else 0, now, task_id),
            )
            if cursor.rowcount == 0:
                return None
            row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
            return row_to_dict(row) if row is not None else None
    finally:
        conn.close()


def delete_task(task_id: int, db_path: str | None = None) -> bool:
    """Delete a task row using parameterized DELETE FROM tasks WHERE id = ?."""
    conn = get_connection(db_path)
    try:
        with conn:
            cursor = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            return cursor.rowcount > 0
    finally:
        conn.close()


def get_task_stats(db_path: str | None = None) -> dict[str, int]:
    """
    Optional Extra: Return task statistics computed directly in SQLite using COUNT(*),
    not by iterating in Python.
    """
    conn = get_connection(db_path)
    try:
        total = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
        completed = conn.execute("SELECT COUNT(*) FROM tasks WHERE done = 1").fetchone()[0]
        pending = conn.execute("SELECT COUNT(*) FROM tasks WHERE done = 0").fetchone()[0]
        return {
            "total": total,
            "completed": completed,
            "pending": pending,
        }
    finally:
        conn.close()
