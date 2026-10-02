-- A3: Initialize tasks table and seed initial rows (idempotent)
CREATE TABLE IF NOT EXISTS tasks (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    done BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Stretch Goal: Create index on (done, title) for fast filtered lookups
CREATE INDEX IF NOT EXISTS idx_tasks_done_title ON tasks (done, title);

-- Seed 3 initial rows only when the table is empty
INSERT INTO tasks (title, done)
SELECT seed.title, seed.done
FROM (
    VALUES
        ('Run PostgreSQL in Docker with a persistent volume', FALSE),
        ('Swap InMemoryTaskRepository for PostgresTaskRepository', FALSE),
        ('Verify data survives container restarts', FALSE)
) AS seed(title, done)
WHERE NOT EXISTS (SELECT 1 FROM tasks);
