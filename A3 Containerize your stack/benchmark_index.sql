-- Stretch Goal: Demonstrate EXPLAIN ANALYZE before and after adding an index on a seeded table

-- 1. Ensure clean benchmark setup with 10,000 synthetic rows
DROP INDEX IF EXISTS idx_tasks_done_title;

INSERT INTO tasks (title, done)
SELECT
    'Benchmark Task #' || g,
    (g % 20 = 0)
FROM generate_series(1, 10000) AS g;

ANALYZE tasks;

-- 2. BEFORE INDEX: Forces a Sequential Scan across all 10,000+ rows
EXPLAIN ANALYZE
SELECT id, title, done
FROM tasks
WHERE done = TRUE AND title = 'Benchmark Task #9980';

-- 3. ADD INDEX: Create composite B-tree index on (done, title)
CREATE INDEX idx_tasks_done_title ON tasks (done, title);
ANALYZE tasks;

-- 4. AFTER INDEX: Uses Index Scan on idx_tasks_done_title
EXPLAIN ANALYZE
SELECT id, title, done
FROM tasks
WHERE done = TRUE AND title = 'Benchmark Task #9980';
