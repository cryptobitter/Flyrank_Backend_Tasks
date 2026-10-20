"""
SQLite Database Layer for Image Understanding & Matching Engine.

Tables:
- images: structured vision metadata and review flags
- embeddings: vector embeddings stored as serialized float arrays
- posts: blog articles needing relevant images
- suggestions: recorded candidate recommendations and guard decisions
- reviews: human-in-the-loop approvals / rejections
- cost_logs: granular per-call AI cost tracking ledger
"""

from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
import sqlite3
from typing import Any, Dict, Generator, List, Optional

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DB_PATH = os.path.join(os.path.dirname(CURRENT_DIR), "data", "image_engine.db")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def get_db_path() -> str:
    db_path = os.environ.get("DATABASE_URL", DEFAULT_DB_PATH)
    if db_path.startswith("sqlite:///"):
        db_path = db_path.replace("sqlite:///", "")
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
    return db_path


def get_raw_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    target_path = db_path or get_db_path()
    conn = sqlite3.connect(target_path, check_same_thread=False, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA busy_timeout = 30000;")
    return conn


@contextmanager
def get_db(db_path: Optional[str] = None) -> Generator[sqlite3.Connection, None, None]:
    conn = get_raw_connection(db_path)
    try:
        yield conn
    finally:
        conn.close()


def init_db(db_path: Optional[str] = None) -> None:
    """Initialize database tables and indexes."""
    with get_db(db_path) as conn:
        with conn:
            # 1. Images table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS images (
                    id TEXT PRIMARY KEY,
                    filename TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    category TEXT NOT NULL,
                    attributes TEXT NOT NULL, -- JSON array
                    caption TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    flagged INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL
                )
                """
            )

            # 2. Embeddings table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS embeddings (
                    entity_id TEXT PRIMARY KEY,
                    entity_type TEXT NOT NULL, -- 'image' or 'post'
                    vector TEXT NOT NULL, -- JSON serialized float list
                    updated_at TEXT NOT NULL
                )
                """
            )

            # 3. Blog posts table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS posts (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )

            # 4. Suggestions / Match Decisions table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS suggestions (
                    id TEXT PRIMARY KEY,
                    post_id TEXT NOT NULL,
                    image_id TEXT NOT NULL,
                    similarity_score REAL NOT NULL,
                    decision TEXT NOT NULL, -- 'ACCEPTED' or 'REJECTED'
                    reason TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )

            # 5. Reviews table (Human-in-the-loop review workflow)
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS reviews (
                    id TEXT PRIMARY KEY,
                    post_id TEXT NOT NULL,
                    image_id TEXT NOT NULL,
                    decision TEXT NOT NULL, -- 'approved' or 'rejected'
                    feedback TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )

            # 6. Cost logs table (Section 6 & Probe 6 requirement)
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS cost_logs (
                    id TEXT PRIMARY KEY,
                    operation TEXT NOT NULL, -- 'vision_tagging' or 'embedding_generation'
                    model TEXT NOT NULL,
                    input_units INTEGER NOT NULL,
                    output_units INTEGER NOT NULL,
                    cost_usd REAL NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )

            # Indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_images_subject ON images(subject);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_images_category ON images(category);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_images_flagged ON images(flagged);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_suggestions_post ON suggestions(post_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_cost_op ON cost_logs(operation);")
