# W3 · A2 — Connecting Your CRUD to the Database (SQLite)

> **Track**: FlyRank Internship · Backend Development Track · Week 3 · Assignment A2  
> **Lane**: Python (`FastAPI` + standard library `sqlite3`)  
> **Database**: SQLite (`tasks.db`)

---

## 1. Goal & The Big Idea

In Assignment 1, our CRUD API stored tasks inside an in-memory Python list (`Client -> API -> List in Memory`). Every time the server restarted, all tasks vanished.

In **W3 · A2**, we swapped the in-memory list for a persistent **SQLite database** (`Client -> API -> SQLite Database (tasks.db)`) while keeping the API endpoints, request bodies, status codes (`200`, `201`, `204`, `400`, `404`), and response shapes **100% identical**:

```text
Assignment 1:   Client  ->  API  ->  a list in memory
This one (A2):  Client  ->  API  ->  SQLite database (tasks.db)
```

---

## 2. Why SQLite Was Chosen

1. **Zero Configuration & Serverless**: SQLite requires no separate database server process, no background daemon, and no external credentials. Python's built-in `sqlite3` library connects directly to a file on disk.
2. **Single-File Persistence**: The entire relational schema, indexes, and rows live inside a single portable file (`tasks.db`) that survives server restarts.
3. **Production SQL Foundations**: Supports full ACID transactions, parameterized queries (`?` placeholders that prevent SQL injection), relational constraints, and B-tree indexes—making future transitions to PostgreSQL or MySQL purely a storage-layer change.

---

## 3. Where the Database File Is Stored

- **Location**: `W3-A2/tasks.db` (created automatically in the project root on startup; configurable via `TASKS_DB_PATH`).
- **Auto-Creation & One-Time Seeding**: On application startup (`lifespan` hook calling `database.init_db()`), the server:
  1. Opens (and creates if missing) `tasks.db`.
  2. Executes `CREATE TABLE IF NOT EXISTS tasks (...)` and creates search/filter indexes.
  3. Checks `SELECT COUNT(*) FROM tasks` and inserts the **three example tasks only when the count is `0`**, wrapped inside an atomic transaction so restarting the server never duplicates seed rows.
- **Git-Ignored**: `tasks.db` is listed in `.gitignore` so every clean clone automatically creates and seeds a fresh database on first run.

---

## 4. How to Start the Project

Clone the repository, navigate to `W3-A2`, and start the server with **one command**:

```bash
cd W3-A2
uvicorn main:app --reload --port 3000
```

### Verify with `curl`

```bash
# 1. Read all tasks (200 OK — returns 3 seeded tasks from tasks.db)
curl -i http://localhost:3000/tasks

# 2. Read a single task (200 OK) or unknown ID (404 Not Found)
curl -i http://localhost:3000/tasks/1
curl -i http://localhost:3000/tasks/999

# 3. Create a new task (201 Created — persists across server restarts)
curl -i -X POST http://localhost:3000/tasks \
  -H "Content-Type: application/json" \
  -d '{"title": "Buy almond milk"}'

# 4. Update a task (200 OK)
curl -i -X PUT http://localhost:3000/tasks/4 \
  -H "Content-Type: application/json" \
  -d '{"title": "Buy oat milk", "done": true}'

# 5. Delete a task (204 No Content)
curl -i -X DELETE http://localhost:3000/tasks/4
```

### Run Automated Verification Tests

```bash
pytest test_api.py -v
```

---

## 5. Database Viewer Screenshot (DB Browser for SQLite)

Below is `W3-A2/tasks.db` opened in **DB Browser for SQLite**, showing the live `tasks` table rows alongside the **Execute SQL** tab:

![DB Browser for SQLite Screenshot](./db_browser_screenshot.png)

---

## 6. Stage 4 — Manual SQL Queries Executed

In Stage 4, we executed raw SQL queries directly against `tasks.db` and verified that `GET /tasks` reflected every change immediately without restarting the server (because both the API and DB Browser read from the same `tasks.db` source of truth):

```sql
SELECT * FROM tasks;                   -- list every task
SELECT * FROM tasks WHERE done = 1;    -- only completed tasks
SELECT COUNT(*) FROM tasks;            -- how many tasks are there?
UPDATE tasks SET done = 1;             -- mark every task completed
DELETE FROM tasks WHERE done = 1;      -- delete all completed tasks
```

**Saved Query & One-Sentence Summary**:
- **Query**: `SELECT * FROM tasks WHERE done = 1;`
- **What it returned**: It filtered the `tasks` table inside SQLite and returned only the completed task row (`id = 1`, `title = 'Buy groceries'`, `done = 1`), excluding all pending tasks where `done = 0`.

---

## 7. Optional Extras & Stretch Goals Implemented

### Optional Extras
| Feature | Endpoint / Mechanism | SQL Clause Used |
| :--- | :--- | :--- |
| **Search with SQL** | `GET /tasks?search=milk` | `WHERE title LIKE ?` (`%milk%`) |
| **Filter by Status** | `GET /tasks?done=true` | `WHERE done = ?` (`1` or `0`) |
| **Sort Alphabetically** | `GET /tasks?sort=title` | `ORDER BY title COLLATE NOCASE ASC` |
| **Real SQL Statistics** | `GET /stats` | `SELECT COUNT(*) FROM tasks [WHERE done = 1/0]` |
| **Timestamps** | `created_at`, `updated_at` | Set on `INSERT` and refreshed on `UPDATE` (ISO-8601 UTC) |

**Reflections on Adding Timestamps (Schema Evolution & Migrations)**:
Adding `created_at` and `updated_at` to an already-existing `tasks.db` file revealed that `CREATE TABLE IF NOT EXISTS` does not automatically update a table whose shape has already been written to disk. Handling existing rows required either deleting the database file or running `ALTER TABLE tasks ADD COLUMN ...` and backfilling `NULL` values—which is the exact pain point that formal **database migrations** solve in production systems.

### Stretch Goals
1. **Proof That the API Didn't Change (`test_api.py`)**:
   In [`test_api.py`](./test_api.py), `run_identical_a1_crud_contract()` executes the exact same endpoint assertions against both `in_memory_a1.app` (Assignment 1) and `main.app` (Assignment 2 SQLite). Because automated tests interact strictly with HTTP requests, status codes, and JSON payloads, identical tests passing without modification proves that storage is purely an internal implementation detail hidden behind the API contract.
2. **Database Indexes (`idx_tasks_done`, `idx_tasks_title`)**:
   - *One-line explanation*: An index is a B-tree lookup structure that lets the database jump directly to matching rows during `WHERE` and `ORDER BY` queries instead of scanning every row in the table sequentially.
3. **Atomic Transaction (`with conn:` in `init_db()`)**:
   - *One-line explanation*: Wrapping multi-step database operations (such as creating the table and seeding the three starter tasks) in a transaction guarantees all-or-nothing execution so a crash mid-seed rolls back cleanly instead of leaving a half-seeded database.

---

## 8. Stage 6 (Bonus) — The AI Rematch ("AI vs Me")

After building Stages 0–5 by hand, we wrote a specification prompt from memory and quarantined the AI's generated code inside [`ai-version/`](./ai-version/).

### Our First-Pass Prompt (Written from Memory)

```text
Migrate an in-memory Python FastAPI task CRUD API to SQLite using Python's built-in sqlite3 library.
Requirements:
- Open a SQLite database file named tasks.db (created automatically on startup).
- Create a table named tasks if it doesn't already exist with columns: id (INTEGER PRIMARY KEY AUTOINCREMENT), title (TEXT NOT NULL), and done (BOOLEAN NOT NULL DEFAULT 0).
- Seed three example tasks on startup ONLY when the tasks table is empty (count == 0) so restarts never duplicate them.
- Keep the exact same 5 CRUD endpoints:
  1. GET /tasks -> 200 OK with list of tasks
  2. GET /tasks/{task_id} -> 200 OK with task, or 404 {"error": "Task not found"}
  3. POST /tasks -> 201 Created with new task; missing/empty title returns 400
  4. PUT /tasks/{task_id} -> 200 OK with updated task; invalid body returns 400; unknown id returns 404 {"error": "Task not found"}
  5. DELETE /tasks/{task_id} -> 204 No Content on success; unknown id returns 404 {"error": "Task not found"}
- Use parameterized SQL queries (?) everywhere to prevent SQL injection.
```

### Code Review & Diff (`git diff --no-index main.py ai-version/ai_app_v1.py`)

Comparing our hand-built code ([`database.py`](./database.py) + [`main.py`](./main.py)) against [`ai-version/ai_app_v1.py`](./ai-version/ai_app_v1.py) surfaced four concrete differences:

1. **What the AI did better (and why)**:
   - The AI used SQLite 3.35+'s `INSERT INTO tasks (title, done) VALUES (?, ?) RETURNING *` and `UPDATE ... RETURNING *` clauses inside a `@contextmanager def get_db()` helper, which returns the inserted/updated row in a single round-trip instead of running a separate `SELECT * FROM tasks WHERE id = ?` after `cursor.lastrowid`.
2. **What the AI got wrong or quietly ignored**:
   - **Wrong Validation Status Code (`422` vs `400`)**: Because the AI used a standard Pydantic `BaseModel` (`TaskPayload`) without overriding FastAPI's `RequestValidationError` handler, sending `{}` or `{"title": ""}` to `POST /tasks` returned `422 Unprocessable Entity` with `{"detail": [...]}` instead of Assignment 1's required `400 Bad Request` with `{"error": "..."}`.
   - **Wrong Error JSON Key (`detail` vs `error`)**: Using `raise HTTPException(status_code=404, detail="Task not found")` produced `{"detail": "Task not found"}` instead of `{"error": "Task not found"}`, breaking strict A1 contract compatibility.
   - **Whitespace Titles Accepted**: `Field(..., min_length=1)` allowed `"   "` (three spaces) as a valid task title.
3. **What our prompt forgot to specify (and what the AI silently decided)**:
   - Our first prompt said `done (BOOLEAN NOT NULL DEFAULT 0)` and asked for JSON task responses, but forgot to mention that Python's `sqlite3` driver returns `0` and `1` integers for `BOOLEAN` columns. The AI silently returned `{"id": 1, "title": "Buy groceries", "done": 0}` instead of converting `done` back to `false`/`true` booleans, and also used FastAPI's deprecated `@app.on_event("startup")` hook.

### The Rematch (`ai-version/ai_app_rematch.py`)

We improved our prompt by explicitly specifying: *(a)* override `RequestValidationError` to return HTTP `400` with `{"error": "..."}`, *(b)* strip whitespace-only titles, *(c)* return `JSONResponse(status_code=404, content={"error": "Task not found"})`, *(d)* cast `row["done"]` to `bool`, and *(e)* use FastAPI's `@asynccontextmanager def lifespan(app)`.

**One-sentence summary of what changed**: Adding explicit framework-boundary constraints (overriding FastAPI's default `422`/`detail` error behavior and casting SQLite's `0`/`1` integers to booleans) turned the AI's rematch output ([`ai-version/ai_app_rematch.py`](./ai-version/ai_app_rematch.py)) into a drop-in replacement that passes 100% of our Assignment 1 contract tests on the first try.
