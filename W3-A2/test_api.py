"""
Automated Verification & Stretch Goal Test Suite for W3-A2.
1. Runs the exact same Assignment 1 CRUD contract tests against BOTH the
   A1 in-memory app and the A2 SQLite app — proving storage is an implementation detail.
2. Verifies persistence across server restarts and one-time seeding (Stage 0-3 checkpoints).
3. Verifies Optional Extras: SQL LIKE search, WHERE done filter, ORDER BY title sort,
   GET /stats using SQL COUNT(*), and created_at / updated_at timestamps.
"""

import os
import tempfile
import pytest
from fastapi.testclient import TestClient

import database
import in_memory_a1
import main


def run_identical_a1_crud_contract(client: TestClient) -> None:
    """
    The unmodified Assignment 1 CRUD API contract test suite.
    Checks GET /tasks, GET /tasks/:id, POST /tasks, PUT /tasks/:id, DELETE /tasks/:id,
    and status codes 200, 201, 204, 400, 404.
    """
    # 1. GET /tasks returns the 3 initial seeded tasks
    res = client.get("/tasks")
    assert res.status_code == 200
    tasks = res.json()
    assert len(tasks) == 3
    assert tasks[0]["id"] == 1
    assert tasks[0]["title"] == "Buy groceries"
    assert tasks[0]["done"] is False

    # 2. GET /tasks/{id} returns a single task or 404 for unknown id
    res_one = client.get("/tasks/1")
    assert res_one.status_code == 200
    assert res_one.json()["title"] == "Buy groceries"

    res_missing = client.get("/tasks/999")
    assert res_missing.status_code == 404
    assert res_missing.json() == {"error": "Task not found"}

    # 3. POST /tasks validates missing/empty title (400) and creates valid task (201)
    res_bad_post = client.post("/tasks", json={})
    assert res_bad_post.status_code == 400
    assert "error" in res_bad_post.json()

    res_empty_title = client.post("/tasks", json={"title": "   "})
    assert res_empty_title.status_code == 400
    assert "error" in res_empty_title.json()

    res_created = client.post("/tasks", json={"title": "Buy almond milk"})
    assert res_created.status_code == 201
    created_task = res_created.json()
    assert created_task["id"] == 4
    assert created_task["title"] == "Buy almond milk"
    assert created_task["done"] is False

    # 4. PUT /tasks/{id} updates task (200), rejects invalid body (400), 404 on unknown id
    res_updated = client.put("/tasks/4", json={"title": "Buy oat milk", "done": True})
    assert res_updated.status_code == 200
    assert res_updated.json()["title"] == "Buy oat milk"
    assert res_updated.json()["done"] is True

    res_put_missing = client.put("/tasks/999", json={"title": "Ghost", "done": True})
    assert res_put_missing.status_code == 404
    assert res_put_missing.json() == {"error": "Task not found"}

    res_put_bad = client.put("/tasks/4", json={"title": ""})
    assert res_put_bad.status_code == 400
    assert "error" in res_put_bad.json()

    # 5. DELETE /tasks/{id} returns 204 and removes task; second DELETE returns 404
    res_del = client.delete("/tasks/4")
    assert res_del.status_code == 204
    assert res_del.text == ""

    res_del_again = client.delete("/tasks/4")
    assert res_del_again.status_code == 404
    assert res_del_again.json() == {"error": "Task not found"}


def test_a1_contract_passes_on_both_memory_and_sqlite(monkeypatch):
    """Stretch Goal: Prove the exact same A1 endpoint tests pass on both implementations."""
    # Reset A1 in-memory state
    in_memory_a1.tasks[:] = [
        {"id": 1, "title": "Buy groceries", "done": False},
        {"id": 2, "title": "Learn SQLite fundamentals", "done": False},
        {"id": 3, "title": "Connect CRUD API to database", "done": False},
    ]
    in_memory_a1.next_id = 4

    with TestClient(in_memory_a1.app) as memory_client:
        run_identical_a1_crud_contract(memory_client)

    with tempfile.TemporaryDirectory() as tmpdir:
        test_db = os.path.join(tmpdir, "tasks.db")
        monkeypatch.setattr(database, "DB_PATH", test_db)
        with TestClient(main.app) as sqlite_client:
            run_identical_a1_crud_contract(sqlite_client)


def test_seed_runs_only_once_and_data_survives_restart(monkeypatch):
    """Stage 0 & Stage 2 Checkpoint: Restart server multiple times; seed never duplicates and new tasks persist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_db = os.path.join(tmpdir, "tasks.db")
        monkeypatch.setattr(database, "DB_PATH", test_db)

        # Restart 1, 2, 3 -> still exactly 3 seeded tasks
        for _ in range(3):
            with TestClient(main.app) as client:
                res = client.get("/tasks")
                assert res.status_code == 200
                assert len(res.json()) == 3

        # Create a new task in session 1
        with TestClient(main.app) as client1:
            post_res = client1.post("/tasks", json={"title": "Persist across restart"})
            assert post_res.status_code == 201

        # Simulate server stop & restart in session 2 -> task is still there!
        with TestClient(main.app) as client2:
            get_res = client2.get("/tasks")
            assert get_res.status_code == 200
            titles = [t["title"] for t in get_res.json()]
            assert len(titles) == 4
            assert "Persist across restart" in titles


def test_optional_extras_search_filter_sort_stats_timestamps(monkeypatch):
    """Verify Optional Extras: LIKE search, WHERE done filter, ORDER BY sort, GET /stats, and timestamps."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_db = os.path.join(tmpdir, "tasks.db")
        monkeypatch.setattr(database, "DB_PATH", test_db)

        with TestClient(main.app) as client:
            # Create and update tasks
            r_milk = client.post("/tasks", json={"title": "Buy organic milk", "done": True})
            assert r_milk.status_code == 201
            milk_task = r_milk.json()
            assert "created_at" in milk_task and "updated_at" in milk_task

            # Search using SQL LIKE: GET /tasks?search=milk
            r_search = client.get("/tasks?search=milk")
            assert r_search.status_code == 200
            assert len(r_search.json()) == 1
            assert r_search.json()[0]["title"] == "Buy organic milk"

            # Filter completed tasks: GET /tasks?done=true
            r_done = client.get("/tasks?done=true")
            assert r_done.status_code == 200
            assert len(r_done.json()) == 1
            assert r_done.json()[0]["done"] is True

            # Sort alphabetically: GET /tasks?sort=title
            r_sort = client.get("/tasks?sort=title")
            assert r_sort.status_code == 200
            sorted_titles = [t["title"] for t in r_sort.json()]
            assert sorted_titles == sorted(sorted_titles, key=str.lower)

            # Real statistics via SQL COUNT(*): GET /stats
            r_stats = client.get("/stats")
            assert r_stats.status_code == 200
            assert r_stats.json() == {"total": 4, "completed": 1, "pending": 3}
