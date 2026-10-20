"""
Database & SQL Aggregation Module for PDF Report Generator.

Exercises core SQL aggregation concepts:
- COUNT(*), SUM(CASE WHEN ...), ROUND(AVG(...), 1)
- GROUP BY category, priority, status
- Temporal grouping with strftime
- Multi-dimensional rollups for executive metrics
"""

from datetime import datetime, timedelta, timezone
import os
import sqlite3
from typing import Any, Dict, List, Optional

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DB_PATH = os.path.join(BASE_DIR, "data", "tasks.db")


def utc_now_iso(offset_days: int = 0, offset_hours: int = 0) -> str:
    """Return an ISO-8601 formatted UTC timestamp with optional day/hour delta."""
    dt = datetime.now(timezone.utc) + timedelta(days=offset_days, hours=offset_hours)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Open SQLite connection with sqlite3.Row factory enabled."""
    target_path = db_path or DEFAULT_DB_PATH
    os.makedirs(os.path.dirname(os.path.abspath(target_path)), exist_ok=True)
    conn = sqlite3.connect(target_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Optional[str] = None) -> None:
    """
    Initialize SQLite schema for tasks and reports.
    Seeds rich enterprise task data if empty.
    """
    conn = get_connection(db_path)
    try:
        with conn:
            # 1. Tasks Table with schema supporting multidimensional SQL analytics
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    category TEXT NOT NULL,
                    priority TEXT NOT NULL CHECK(priority IN ('Critical', 'High', 'Medium', 'Low')),
                    status TEXT NOT NULL CHECK(status IN ('Completed', 'In Progress', 'Pending')),
                    assignee TEXT NOT NULL,
                    estimated_hours REAL NOT NULL DEFAULT 1.0,
                    actual_hours REAL NOT NULL DEFAULT 0.0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    completed_at TEXT
                )
                """
            )

            # Indexes for fast aggregations and query performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_category ON tasks(category)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks(priority)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_completed ON tasks(completed_at)")

            # Check if seeding is required
            cursor = conn.execute("SELECT COUNT(*) AS cnt FROM tasks")
            count = cursor.fetchone()["cnt"]
            if count == 0:
                _seed_initial_tasks(conn)
    finally:
        conn.close()


def _seed_initial_tasks(conn: sqlite3.Connection) -> None:
    """Seed comprehensive sample dataset spanning sprint tasks across categories."""
    seed_data = [
        # Engineering / Backend
        ("Implement Supabase JWT Auth Middleware", "Engineering", "Critical", "Completed", "Alex Chen", 6.0, 5.5, -6, -5, -5),
        ("Design SQLite Task Schema & CRUD API", "Engineering", "High", "Completed", "Jordan Patel", 4.0, 3.8, -6, -4, -4),
        ("Containerize Stack with Docker Compose", "Engineering", "Critical", "Completed", "Alex Chen", 8.0, 9.2, -5, -3, -3),
        ("Add Redis Caching Layer for Fast Lookups", "Engineering", "High", "Completed", "Alex Chen", 4.5, 4.0, -4, -2, -2),
        ("Construct Async PDF Report Background Pipeline", "Engineering", "Critical", "In Progress", "Jordan Patel", 7.0, 4.5, -2, 0, None),
        ("Configure Recurring Cron Schedule Runner", "Engineering", "Medium", "Pending", "Alex Chen", 3.5, 0.0, -1, 0, None),

        # Security & DevOps
        ("Configure Row Level Security & RBAC Guardrails", "Security", "Critical", "Completed", "Taylor Wong", 5.0, 4.8, -5, -3, -3),
        ("Automate SAST Security Vulnerability Scans", "Security", "High", "Completed", "Taylor Wong", 3.0, 2.5, -4, -2, -2),
        ("Set Up Secrets Rotation and Vault Integration", "Security", "Medium", "In Progress", "Taylor Wong", 4.0, 2.0, -1, 0, None),
        ("Establish Production CDN & Edge Caching", "DevOps", "High", "Completed", "Morgan Smith", 4.0, 3.5, -5, -3, -3),
        ("Set Up Prometheus & Grafana System Alerts", "DevOps", "Medium", "Completed", "Morgan Smith", 5.5, 6.0, -3, -1, -1),
        ("Create GitHub Actions CI/CD Release Pipeline", "DevOps", "High", "Pending", "Morgan Smith", 6.0, 0.0, -1, 0, None),

        # Frontend & UX
        ("Build Mobile-First Responsive Viewport Layout", "Frontend", "High", "Completed", "Samira Khan", 4.0, 4.2, -4, -2, -2),
        ("Audit Touch Targets and WCAG AA Contrast", "Frontend", "Medium", "Completed", "Samira Khan", 3.0, 2.5, -3, -1, -1),
        ("Implement Report Download Button & Live Poller", "Frontend", "High", "In Progress", "Samira Khan", 4.0, 2.0, -1, 0, None),
        ("Interactive Sprint Velocity Metric Cards", "Frontend", "Low", "Pending", "Samira Khan", 2.5, 0.0, -1, 0, None),

        # QA & Documentation
        ("11/11 Pytest Regression Test Suite for W3-A2", "QA", "Critical", "Completed", "Chris Lee", 5.0, 4.5, -5, -3, -3),
        ("Load Benchmark EXPLAIN ANALYZE 10k Records", "QA", "High", "Completed", "Chris Lee", 4.0, 4.0, -4, -2, -2),
        ("End-to-End Background Job Failure Recovery Evals", "QA", "Medium", "In Progress", "Chris Lee", 3.5, 1.5, -1, 0, None),
        ("Architectural Decision Record & Explainer Doc", "Documentation", "Medium", "Completed", "Jordan Patel", 3.0, 2.8, -3, -1, -1),
        ("API Swagger / OpenAPI Spec Documentation", "Documentation", "Low", "Completed", "Jordan Patel", 2.0, 1.5, -2, -1, -1),
        ("Incident Post-Mortem and Runbook Guide", "Documentation", "Low", "Pending", "Chris Lee", 2.5, 0.0, -1, 0, None),
    ]

    for item in seed_data:
        title, cat, prio, stat, assignee, est, act, c_days, u_days, comp_days = item
        created_at = utc_now_iso(offset_days=c_days)
        updated_at = utc_now_iso(offset_days=u_days)
        completed_at = utc_now_iso(offset_days=comp_days) if comp_days is not None else None

        conn.execute(
            """
            INSERT INTO tasks (
                title, category, priority, status, assignee,
                estimated_hours, actual_hours, created_at, updated_at, completed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (title, cat, prio, stat, assignee, est, act, created_at, updated_at, completed_at),
        )


# =====================================================================
# SQL Aggregation Queries
# =====================================================================

def query_executive_metrics(db_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Perform multi-dimensional SQL aggregation across entire dataset in a single query.
    Calculates counts, rates, total hours, and average turnaround.
    """
    conn = get_connection(db_path)
    try:
        query = """
        SELECT
            COUNT(*) AS total_tasks,
            SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END) AS completed_tasks,
            SUM(CASE WHEN status = 'In Progress' THEN 1 ELSE 0 END) AS in_progress_tasks,
            SUM(CASE WHEN status = 'Pending' THEN 1 ELSE 0 END) AS pending_tasks,
            ROUND(100.0 * SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END) / COUNT(*), 1) AS completion_rate,
            ROUND(SUM(estimated_hours), 1) AS total_estimated_hours,
            ROUND(SUM(actual_hours), 1) AS total_actual_hours,
            ROUND(AVG(CASE WHEN status = 'Completed' THEN actual_hours ELSE NULL END), 1) AS avg_turnaround_hours,
            COUNT(DISTINCT assignee) AS active_contributors,
            COUNT(DISTINCT category) AS active_categories
        FROM tasks
        """
        row = conn.execute(query).fetchone()
        return dict(row)
    finally:
        conn.close()


def query_priority_breakdown(db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    SQL aggregation grouping by priority with CASE conditional aggregations
    and custom priority ordering.
    """
    conn = get_connection(db_path)
    try:
        query = """
        SELECT
            priority,
            COUNT(*) AS total,
            SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END) AS completed,
            SUM(CASE WHEN status = 'In Progress' THEN 1 ELSE 0 END) AS in_progress,
            SUM(CASE WHEN status = 'Pending' THEN 1 ELSE 0 END) AS pending,
            ROUND(100.0 * SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END) / COUNT(*), 1) AS completion_pct,
            ROUND(SUM(actual_hours), 1) AS logged_hours
        FROM tasks
        GROUP BY priority
        ORDER BY
            CASE priority
                WHEN 'Critical' THEN 1
                WHEN 'High' THEN 2
                WHEN 'Medium' THEN 3
                WHEN 'Low' THEN 4
                ELSE 5
            END ASC
        """
        rows = conn.execute(query).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def query_category_breakdown(db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    SQL aggregation grouping by project category with velocity and burn metrics.
    """
    conn = get_connection(db_path)
    try:
        query = """
        SELECT
            category,
            COUNT(*) AS total_tasks,
            SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END) AS completed_tasks,
            ROUND(100.0 * SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END) / COUNT(*), 1) AS completion_rate,
            ROUND(SUM(estimated_hours), 1) AS est_hours,
            ROUND(SUM(actual_hours), 1) AS act_hours,
            ROUND(SUM(actual_hours) - SUM(estimated_hours), 1) AS variance_hours
        FROM tasks
        GROUP BY category
        ORDER BY total_tasks DESC, category ASC
        """
        rows = conn.execute(query).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def query_recent_tasks(limit: int = 15, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Fetch itemized recent tasks ordered by update recency."""
    conn = get_connection(db_path)
    try:
        query = """
        SELECT
            id,
            title,
            category,
            priority,
            status,
            assignee,
            actual_hours,
            estimated_hours,
            substr(updated_at, 1, 10) AS last_activity
        FROM tasks
        ORDER BY updated_at DESC, id DESC
        LIMIT ?
        """
        rows = conn.execute(query, (limit,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def query_assignee_workload(db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Aggregate tasks and logged effort by team member."""
    conn = get_connection(db_path)
    try:
        query = """
        SELECT
            assignee,
            COUNT(*) AS total_tasks,
            SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END) AS completed,
            ROUND(SUM(actual_hours), 1) AS total_hours
        FROM tasks
        GROUP BY assignee
        ORDER BY total_hours DESC
        """
        rows = conn.execute(query).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
