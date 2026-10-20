"""
Database layer for LLM Usage Metering & Billing Engine.
Enforces multi-tenant data isolation, strict schema constraints, foreign keys, and atomic transactions.
"""

import sqlite3
import os
import contextlib
from typing import Generator
from config import DATABASE_PATH, PLANS

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DATABASE_PATH, timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

@contextlib.contextmanager
def get_db() -> Generator[sqlite3.Connection, None, None]:
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    """Initializes tables and default plans if not already present."""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Tenants
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS tenants (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            stripe_customer_id TEXT,
            status TEXT NOT NULL DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # Plans
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS plans (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            monthly_api_calls_quota INTEGER NOT NULL,
            monthly_tokens_quota INTEGER NOT NULL,
            base_price_cents INTEGER NOT NULL
        );
        """)

        # Subscriptions
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            plan_id TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            current_period_start TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            current_period_end TIMESTAMP,
            stripe_subscription_id TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
            FOREIGN KEY (plan_id) REFERENCES plans(id)
        );
        """)

        # Usage Events (Meters)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS usage_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            api_calls_qty INTEGER NOT NULL DEFAULT 1,
            prompt_tokens INTEGER NOT NULL DEFAULT 0,
            cached_prompt_tokens INTEGER NOT NULL DEFAULT 0,
            completion_tokens INTEGER NOT NULL DEFAULT 0,
            reasoning_tokens INTEGER NOT NULL DEFAULT 0,
            total_tokens INTEGER NOT NULL DEFAULT 0,
            cost_micros INTEGER NOT NULL DEFAULT 0,
            idempotency_key TEXT UNIQUE,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
        );
        """)

        # Idempotency Cache Records
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS idempotency_records (
            key TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            request_hash TEXT NOT NULL,
            response_status INTEGER NOT NULL,
            response_body TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # Stripe Webhook Deduplication Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS webhook_events (
            event_id TEXT PRIMARY KEY,
            event_type TEXT NOT NULL,
            processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            payload_hash TEXT NOT NULL
        );
        """)

        # Nightly Reconciliation & Audit Log Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS reconciliation_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            tenants_checked INTEGER NOT NULL,
            anomalies_detected INTEGER NOT NULL,
            details TEXT NOT NULL
        );
        """)

        # Indexes for fast rollups and O(1) deduplication
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_usage_tenant_time ON usage_events (tenant_id, timestamp);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_usage_idemp ON usage_events (idempotency_key);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sub_tenant ON subscriptions (tenant_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_idemp_tenant ON idempotency_records (tenant_id);")

        # Seed Default Plans from config
        for plan in PLANS.values():
            cursor.execute("""
            INSERT INTO plans (id, name, monthly_api_calls_quota, monthly_tokens_quota, base_price_cents)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name=excluded.name,
                monthly_api_calls_quota=excluded.monthly_api_calls_quota,
                monthly_tokens_quota=excluded.monthly_tokens_quota,
                base_price_cents=excluded.base_price_cents;
            """, (plan.plan_id, plan.name, plan.monthly_api_calls_quota, plan.monthly_tokens_quota, plan.base_price_cents))

if __name__ == "__main__":
    init_db()
    print("Database schema initialized successfully.")
