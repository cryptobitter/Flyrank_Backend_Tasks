"""
Stage 0: Create SQLite database (tasks.db), tasks table, and seed initial tasks once.
"""

import os
import sqlite3

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
