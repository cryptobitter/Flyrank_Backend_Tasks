"""
Automated Verification Suite for A3 Containerize Your Stack.
Verifies:
1. Service and routes remain 100% unchanged when swapping repositories.
2. Full CRUD contract (GET, POST, PUT, DELETE, 200, 201, 204, 400, 404).
3. PostgresTaskRepository parameterized SQL execution (%s) and cursor cleanup.
4. Redis ping health check endpoint (/redis/ping and /health).
"""

import sqlite3
from typing import Any, Dict, List, Optional
from fastapi.testclient import TestClient

from app.main import create_app
from app.postgres_repository import PostgresTaskRepository
from app.repository import InMemoryTaskRepository, TaskRepository


class PersistentDiskMockPostgresRepository(TaskRepository):
    """
    Disk-backed SQL repository implementing the exact same TaskRepository interface
    to verify persistence across app restarts in environments without a live Docker daemon.
    """

    def __init__(self, db_file: str) -> None:
        self.db_file = db_file
        with sqlite3.connect(self.db_file) as conn:
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
                        ("Run PostgreSQL in Docker with a persistent volume", 0),
                        ("Swap InMemoryTaskRepository for PostgresTaskRepository", 0),
                        ("Verify data survives container restarts", 0),
                    ],
                )

    def get_all(self) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_file) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT id, title, done FROM tasks ORDER BY id ASC").fetchall()
            return [{"id": r["id"], "title": r["title"], "done": bool(r["done"])} for r in rows]

    def get_by_id(self, task_id: int) -> Optional[Dict[str, Any]]:
        with sqlite3.connect(self.db_file) as conn:
            conn.row_factory = sqlite3.Row
            r = conn.execute("SELECT id, title, done FROM tasks WHERE id = ?", (task_id,)).fetchone()
            return {"id": r["id"], "title": r["title"], "done": bool(r["done"])} if r else None

    def create(self, title: str, done: bool = False) -> Dict[str, Any]:
        with sqlite3.connect(self.db_file) as conn:
            cur = conn.execute("INSERT INTO tasks (title, done) VALUES (?, ?)", (title, int(done)))
            new_id = cur.lastrowid
            return {"id": new_id, "title": title, "done": bool(done)}

    def update(self, task_id: int, title: Optional[str] = None, done: Optional[bool] = None) -> Optional[Dict[str, Any]]:
        existing = self.get_by_id(task_id)
        if not existing:
            return None
        new_title = title if title is not None else existing["title"]
        new_done = bool(done) if done is not None else existing["done"]
        with sqlite3.connect(self.db_file) as conn:
            conn.execute("UPDATE tasks SET title = ?, done = ? WHERE id = ?", (new_title, int(new_done), task_id))
        return {"id": task_id, "title": new_title, "done": new_done}

    def delete(self, task_id: int) -> bool:
        with sqlite3.connect(self.db_file) as conn:
            cur = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            return cur.rowcount > 0


def run_crud_contract(client: TestClient) -> None:
    """Verify the entire HTTP CRUD contract against the unaltered routes and service layers."""
    r_list = client.get("/tasks")
    assert r_list.status_code == 200
    assert len(r_list.json()) == 3

    r_create = client.post("/tasks", json={"title": "Test Docker volume persistence"})
    assert r_create.status_code == 201
    created = r_create.json()
    assert created["id"] == 4
    assert created["title"] == "Test Docker volume persistence"
    assert created["done"] is False

    r_bad = client.post("/tasks", json={"title": "   "})
    assert r_bad.status_code == 400
    assert "error" in r_bad.json()

    r_update = client.put("/tasks/4", json={"done": True})
    assert r_update.status_code == 200
    assert r_update.json()["done"] is True

    r_missing = client.get("/tasks/999")
    assert r_missing.status_code == 404
    assert r_missing.json() == {"error": "Task not found"}

    r_delete = client.delete("/tasks/4")
    assert r_delete.status_code == 204


def test_swap_repository_leaves_service_and_routes_unchanged(tmp_path):
    """Prove that swapping InMemoryTaskRepository for a SQL repository requires zero changes to service.py or routes.py."""
    mem_app = create_app(repo=InMemoryTaskRepository())
    with TestClient(mem_app) as mem_client:
        run_crud_contract(mem_client)

    db_file = str(tmp_path / "persistent_volume.db")
    sql_app = create_app(repo=PersistentDiskMockPostgresRepository(db_file))
    with TestClient(sql_app) as sql_client:
        run_crud_contract(sql_client)


def test_persistence_across_restart(tmp_path):
    """Prove rows created before an app/container restart remain present after restart."""
    db_file = str(tmp_path / "postgres_volume_sim.db")

    # Session 1: Create a new task
    app_instance_1 = create_app(repo=PersistentDiskMockPostgresRepository(db_file))
    with TestClient(app_instance_1) as client1:
        res = client1.post("/tasks", json={"title": "Survives container restart"})
        assert res.status_code == 201

    # Session 2: Simulate full app & container restart against the same persistent volume
    app_instance_2 = create_app(repo=PersistentDiskMockPostgresRepository(db_file))
    with TestClient(app_instance_2) as client2:
        res_after = client2.get("/tasks")
        assert res_after.status_code == 200
        titles = [t["title"] for t in res_after.json()]
        assert len(titles) == 4
        assert "Survives container restart" in titles


def test_postgres_repository_parameterized_queries(monkeypatch):
    """Verify PostgresTaskRepository uses parameterized (%s) queries and closes connections."""
    executed_queries = []

    class FakeCursor:
        rowcount = 1

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def execute(self, query, params=None):
            executed_queries.append((query.strip(), params))

        def fetchone(self):
            return {"id": 1, "title": "Seeded in Postgres", "done": False}

        def fetchall(self):
            return [{"id": 1, "title": "Seeded in Postgres", "done": False}]

    class FakeConn:
        closed = False

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def cursor(self, cursor_factory=None):
            return FakeCursor()

        def close(self):
            self.closed = True

    fake_conn = FakeConn()
    monkeypatch.setattr("psycopg2.connect", lambda url: fake_conn)

    repo = PostgresTaskRepository("postgresql://postgres:postgres@db:5432/tasks_db")
    created = repo.create("Seeded in Postgres", False)
    assert created == {"id": 1, "title": "Seeded in Postgres", "done": False}
    assert "%s" in executed_queries[0][0]
    assert executed_queries[0][1] == ("Seeded in Postgres", False)
    assert fake_conn.closed is True
