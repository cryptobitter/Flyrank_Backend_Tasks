"""
Database Layer for Embeddable Widget & Lead-Capture Platform.

Features:
- SQLite connection management with WAL mode and foreign keys enabled
- Schema setup with migrations & indexes for high-throughput reads/writes
- Multi-tenant data model: tenants, widgets, submissions, audit logs
"""

from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
import sqlite3
from typing import Any, Dict, Generator, List, Optional

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DB_PATH = os.path.join(os.path.dirname(CURRENT_DIR), "data", "widget_platform.db")


def utc_now_iso() -> str:
    """Return current UTC time in ISO-8601 format."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def get_db_path() -> str:
    """Return active database path from environment or default."""
    db_path = os.environ.get("DATABASE_URL", DEFAULT_DB_PATH)
    if db_path.startswith("sqlite:///"):
        db_path = db_path.replace("sqlite:///", "")
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
    return db_path


def get_raw_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Open and configure SQLite connection."""
    target_path = db_path or get_db_path()
    conn = sqlite3.connect(target_path, check_same_thread=False, timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    return conn


@contextmanager
def get_db(db_path: Optional[str] = None) -> Generator[sqlite3.Connection, None, None]:
    """Context manager yielding a transactional SQLite connection."""
    conn = get_raw_connection(db_path)
    try:
        yield conn
    finally:
        conn.close()


def init_db(db_path: Optional[str] = None) -> None:
    """Initialize database tables and indexes."""
    with get_db(db_path) as conn:
        with conn:
            # 1. Tenants Table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS tenants (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )

            # 2. Widgets Table (Multi-tenant isolated)
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS widgets (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    widget_type TEXT NOT NULL CHECK(widget_type IN ('signup_form', 'contact_modal', 'cta_popover')),
                    button_text TEXT NOT NULL DEFAULT 'Submit',
                    form_fields TEXT NOT NULL, -- JSON array of field configurations
                    theme_color TEXT NOT NULL DEFAULT '#0D9488',
                    is_active INTEGER NOT NULL DEFAULT 1,
                    allowed_domains TEXT NOT NULL DEFAULT '*', -- comma-separated or *
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
                )
                """
            )

            # 3. Submissions (Leads) Table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS submissions (
                    id TEXT PRIMARY KEY,
                    widget_id TEXT NOT NULL,
                    tenant_id TEXT NOT NULL,
                    data TEXT NOT NULL, -- JSON object of captured inputs
                    ip_address TEXT NOT NULL,
                    user_agent TEXT NOT NULL DEFAULT '',
                    country TEXT NOT NULL DEFAULT 'Unknown',
                    city TEXT NOT NULL DEFAULT 'Unknown',
                    region TEXT NOT NULL DEFAULT 'Unknown',
                    geo_provider TEXT NOT NULL DEFAULT 'none',
                    is_spam INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(widget_id) REFERENCES widgets(id) ON DELETE CASCADE,
                    FOREIGN KEY(tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
                )
                """
            )

            # 4. Audit Logs Table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    details TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )

            # Performance Indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_widgets_tenant ON widgets(tenant_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_submissions_widget ON submissions(widget_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_submissions_tenant ON submissions(tenant_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_submissions_created ON submissions(created_at);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_submissions_spam ON submissions(is_spam);")
