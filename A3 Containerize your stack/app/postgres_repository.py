"""
PostgreSQL Repository Implementation (`PostgresTaskRepository`).
Implements the exact same `TaskRepository` interface as `InMemoryTaskRepository`
using `psycopg2` and parameterized SQL queries (`%s`).
"""

from contextlib import contextmanager
import os
from typing import Any, Dict, Generator, List, Optional

from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

from app.repository import TaskRepository

load_dotenv()


class PostgresTaskRepository(TaskRepository):
    """PostgreSQL-backed repository implementing TaskRepository."""

    def __init__(self, database_url: Optional[str] = None) -> None:
        self.database_url = database_url or os.getenv("DATABASE_URL")
        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable is required for PostgresTaskRepository")

    @contextmanager
    def _get_cursor(self) -> Generator[RealDictCursor, None, None]:
        """Context manager ensuring connections and cursors close cleanly and transactions commit/rollback."""
        conn = psycopg2.connect(self.database_url)
        try:
            with conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    yield cur
        finally:
            conn.close()

    def ensure_schema(self, init_sql_path: Optional[str] = None) -> None:
        """Execute init.sql on startup if needed so the table and seed data exist."""
        if init_sql_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            init_sql_path = os.path.join(base_dir, "init.sql")
        if os.path.exists(init_sql_path):
            with open(init_sql_path, "r", encoding="utf-8") as f:
                sql_script = f.read()
            with self._get_cursor() as cur:
                cur.execute(sql_script)

    @staticmethod
    def _serialize(row: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": int(row["id"]),
            "title": str(row["title"]),
            "done": bool(row["done"]),
        }

    def get_all(self) -> List[Dict[str, Any]]:
        with self._get_cursor() as cur:
            cur.execute("SELECT id, title, done FROM tasks ORDER BY id ASC;")
            rows = cur.fetchall()
            return [self._serialize(r) for r in rows]

    def get_by_id(self, task_id: int) -> Optional[Dict[str, Any]]:
        with self._get_cursor() as cur:
            cur.execute(
                "SELECT id, title, done FROM tasks WHERE id = %s;",
                (task_id,),
            )
            row = cur.fetchone()
            return self._serialize(row) if row is not None else None

    def create(self, title: str, done: bool = False) -> Dict[str, Any]:
        with self._get_cursor() as cur:
            cur.execute(
                """
                INSERT INTO tasks (title, done)
                VALUES (%s, %s)
                RETURNING id, title, done;
                """,
                (title, bool(done)),
            )
            row = cur.fetchone()
            return self._serialize(row)

    def update(
        self,
        task_id: int,
        title: Optional[str] = None,
        done: Optional[bool] = None,
    ) -> Optional[Dict[str, Any]]:
        existing = self.get_by_id(task_id)
        if existing is None:
            return None

        new_title = title if title is not None else existing["title"]
        new_done = bool(done) if done is not None else existing["done"]

        with self._get_cursor() as cur:
            cur.execute(
                """
                UPDATE tasks
                SET title = %s, done = %s, updated_at = NOW()
                WHERE id = %s
                RETURNING id, title, done;
                """,
                (new_title, new_done, task_id),
            )
            row = cur.fetchone()
            return self._serialize(row) if row is not None else None

    def delete(self, task_id: int) -> bool:
        with self._get_cursor() as cur:
            cur.execute("DELETE FROM tasks WHERE id = %s;", (task_id,))
            return cur.rowcount > 0

    def ping(self) -> bool:
        """Verify PostgreSQL connectivity for health checks."""
        try:
            with self._get_cursor() as cur:
                cur.execute("SELECT 1 AS ok;")
                row = cur.fetchone()
                return bool(row and row["ok"] == 1)
        except Exception:
            return False
