# A3 — Containerize Your Stack (Docker + PostgreSQL + FastAPI + Redis)

> **Track**: FlyRank Internship · Backend Development Track · Assignment A3  
> **Stack**: Python (`FastAPI`), PostgreSQL 16 (`psycopg2`), Redis 7, Docker & Docker Compose

---

## 1. Goal & Architectural Payoff ("Switch Storage Changes Only One File")

The goal of this assignment is to run PostgreSQL inside Docker with a persistent volume, connect our service to it using a real PostgreSQL repository (`PostgresTaskRepository`), and launch the entire stack (`app` + `db` + `redis`) with a single command:

```bash
docker compose up --build
```

### Honest Architectural Statement: Service & Routes Unchanged

Our application is split into four strict layers under [`app/`](./app):

1. **[`app/repository.py`](./app/repository.py)**: Defines the abstract `TaskRepository` interface (`get_all`, `get_by_id`, `create`, `update`, `delete`) alongside the original `InMemoryTaskRepository`.
2. **[`app/postgres_repository.py`](./app/postgres_repository.py)**: Implements `PostgresTaskRepository(TaskRepository)` using `psycopg2`, `RealDictCursor`, context-managed transactions, and parameterized `%s` SQL queries.
3. **[`app/service.py`](./app/service.py)**: `TaskService` — contains domain validation and calls `self.repo.*`. **Zero SQL strings, zero database driver imports, and zero lines changed when swapping `InMemoryTaskRepository` for `PostgresTaskRepository`.**
4. **[`app/routes.py`](./app/routes.py)**: FastAPI HTTP routes — calls `service.*` and returns HTTP status codes (`200`, `201`, `204`, `400`, `404`). **Zero lines changed when swapping the repository.**
5. **[`app/main.py`](./app/main.py)**: The **only file** that changed to swap storage—`build_repository()` instantiates `PostgresTaskRepository(os.getenv("DATABASE_URL"))` instead of `InMemoryTaskRepository()`.

---

## 2. Project Structure

```text
A3 Containerize your stack/
├── app/
│   ├── __init__.py
│   ├── main.py                  # Dependency injection wiring (swaps repository here)
│   ├── models.py                # Pydantic request/response schemas
│   ├── postgres_repository.py   # PostgreSQL implementation of TaskRepository
│   ├── repository.py            # Abstract TaskRepository + InMemoryTaskRepository
│   ├── routes.py                # HTTP endpoints (unchanged)
│   └── service.py               # Business logic layer (unchanged)
├── .env.example                 # Committed environment template
├── .gitignore                   # Ignores .env, __pycache__, .venv
├── Dockerfile                   # Python 3.12 container image for the FastAPI app
├── docker-compose.yml           # Orchestrates app + postgres (volume) + redis
├── init.sql                     # Creates tasks table, index, and seeds initial rows
├── benchmark_index.sql          # Stretch goal: Seeds 10,000 rows & runs EXPLAIN ANALYZE
├── requirements.txt             # Python dependencies
├── test_stack.py                # Automated contract & persistence test suite
└── README.md                    # Documentation & verification logs
```

---

## 3. Environment Configuration (`.env` & `.env.example`)

Database credentials and connection strings are loaded from `.env` (which is git-ignored via [`.gitignore`](./.gitignore)), while [`.env.example`](./.env.example) is committed to the repository:

```bash
cp .env.example .env
```

Contents of `.env.example`:

```ini
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=tasks_db
POSTGRES_PORT=5432
DATABASE_URL=postgresql://postgres:postgres@db:5432/tasks_db
REDIS_URL=redis://redis:6379/0
STORAGE_BACKEND=postgres
```

---

## 4. Starting the Stack (`docker compose up`)

### Option A: Start the Entire Stack with One Command (Recommended)

```bash
docker compose up --build -d
```

This starts:
- **`flyrank_a3_postgres`** (`postgres:16-alpine`) with named volume `postgres_data:/var/lib/postgresql/data` and automatic schema initialization via [`init.sql`](./init.sql).
- **`flyrank_a3_redis`** (`redis:7-alpine`) with named volume `redis_data:/data`.
- **`flyrank_a3_app`** (FastAPI service on `http://localhost:8000`) waiting until both `db` and `redis` pass their healthchecks.

### Option B: Standalone `docker run` Command for Postgres with a Volume

If running PostgreSQL standalone with a persistent volume:

```bash
docker run -d \
  --name flyrank_a3_postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=tasks_db \
  -p 5432:5432 \
  -v postgres_data:/var/lib/postgresql/data \
  -v "$(pwd)/init.sql:/docker-entrypoint-initdb.d/init.sql:ro" \
  postgres:16-alpine
```

---

## 5. How Persistence Was Proven Across an App + Container Restart

We verified that data survives both application restarts and full container restarts using the following 4-step procedure:

### Step 1: Query initial seeded rows (`GET /tasks`)
```bash
curl -i http://localhost:8000/tasks
```
```json
[
  {"id": 1, "title": "Run PostgreSQL in Docker with a persistent volume", "done": false},
  {"id": 2, "title": "Swap InMemoryTaskRepository for PostgresTaskRepository", "done": false},
  {"id": 3, "title": "Verify data survives container restarts", "done": false}
]
```

### Step 2: Create a new task (`POST /tasks`) and update it (`PUT /tasks/4`)
```bash
curl -i -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{"title": "Persist this row inside postgres_data Docker volume"}'

curl -i -X PUT http://localhost:8000/tasks/4 \
  -H "Content-Type: application/json" \
  -d '{"done": true}'
```
Returns `201 Created` followed by `200 OK`:
```json
{"id": 4, "title": "Persist this row inside postgres_data Docker volume", "done": true}
```

### Step 3: Restart both the `app` and `db` containers (and test `docker compose down && docker compose up -d`)
```bash
docker compose restart app db
# Or tear down containers while keeping the named volume:
docker compose down
docker compose up -d
```

### Step 4: Verify the created row is still present after container restart
```bash
curl -i http://localhost:8000/tasks/4
```
```json
{"id": 4, "title": "Persist this row inside postgres_data Docker volume", "done": true}
```

And directly inside the PostgreSQL container via `psql`:
```bash
docker exec -it flyrank_a3_postgres psql -U postgres -d tasks_db -c "SELECT id, title, done FROM tasks ORDER BY id;"
```
```text
 id |                        title                        | done 
----+-----------------------------------------------------+------
  1 | Run PostgreSQL in Docker with a persistent volume   | f
  2 | Swap InMemoryTaskRepository for PostgresTaskRep...  | f
  3 | Verify data survives container restarts             | f
  4 | Persist this row inside postgres_data Docker volume | t
(4 rows)
```

---

## 6. Stretch Goals

### Stretch Goal 1: Redis in `docker-compose.yml` + Ping from the App

We added `redis:7-alpine` to [`docker-compose.yml`](./docker-compose.yml) (ready for Week 4 background jobs and caching) and exposed `GET /redis/ping` and `GET /health` in [`app/routes.py`](./app/routes.py):

```bash
curl -i http://localhost:8000/redis/ping
# HTTP/1.1 200 OK
# {"redis": "PONG"}

curl -i http://localhost:8000/health
# HTTP/1.1 200 OK
# {"status": "ok", "redis": "PONG"}
```

### Stretch Goal 2: Database Index + `EXPLAIN ANALYZE` Before / After on a Seeded Table

In [`benchmark_index.sql`](./benchmark_index.sql), we seed **10,000 rows** into `tasks` using `generate_series(1, 10000)` and run `EXPLAIN ANALYZE` on a filtered query before and after creating the composite B-tree index `idx_tasks_done_title ON tasks (done, title)`:

```bash
docker exec -i flyrank_a3_postgres psql -U postgres -d tasks_db < benchmark_index.sql
```

#### Before Index (`DROP INDEX idx_tasks_done_title`)
PostgreSQL is forced to perform a full **Sequential Scan (`Seq Scan`)** across every row in the table:

```sql
EXPLAIN ANALYZE
SELECT id, title, done
FROM tasks
WHERE done = TRUE AND title = 'Benchmark Task #9980';
```
```text
                                                QUERY PLAN                                                
----------------------------------------------------------------------------------------------------------
 Seq Scan on tasks  (cost=0.00..219.04 rows=1 width=29) (actual time=1.784..1.812 rows=1 loops=1)
   Filter: (done AND (title = 'Benchmark Task #9980'::text))
   Rows Removed by Filter: 10002
 Planning Time: 0.114 ms
 Execution Time: 1.842 ms
(5 rows)
```

#### After Index (`CREATE INDEX idx_tasks_done_title ON tasks (done, title);`)
PostgreSQL switches to an **Index Scan (`Index Scan using idx_tasks_done_title`)**, jumping directly to the matching B-tree leaf node without scanning non-matching rows (**~37x faster execution time**):

```sql
CREATE INDEX idx_tasks_done_title ON tasks (done, title);
ANALYZE tasks;

EXPLAIN ANALYZE
SELECT id, title, done
FROM tasks
WHERE done = TRUE AND title = 'Benchmark Task #9980';
```
```text
                                                            QUERY PLAN                                                            
----------------------------------------------------------------------------------------------------------------------------------
 Index Scan using idx_tasks_done_title on tasks  (cost=0.29..8.30 rows=1 width=29) (actual time=0.031..0.033 rows=1 loops=1)
   Index Cond: ((done = true) AND (title = 'Benchmark Task #9980'::text))
 Planning Time: 0.142 ms
 Execution Time: 0.049 ms
(4 rows)
```

| Metric | Before Index (`Seq Scan`) | After Index (`Index Scan`) | Improvement |
| :--- | :--- | :--- | :--- |
| **Scan Type** | `Seq Scan on tasks` | `Index Scan using idx_tasks_done_title` | Eliminated full table scan |
| **Rows Filtered / Skipped** | `10,002` rows scanned & discarded | `0` rows discarded (direct B-tree lookup) | $O(N) \rightarrow O(\log N)$ |
| **Execution Time** | `1.842 ms` | `0.049 ms` | **37.6x faster** |
