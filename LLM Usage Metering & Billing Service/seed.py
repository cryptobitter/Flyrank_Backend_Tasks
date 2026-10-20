"""
Seed script: Populates realistic test tenants, subscriptions, and usage events.
Enables instant evaluation of boundary quotas, idempotency, and Stripe upgrade flows.
"""

import uuid
from database import get_db, init_db

def seed_database():
    init_db()
    
    with get_db() as conn:
        cursor = conn.cursor()

        # Clear existing data for clean seed
        cursor.execute("DELETE FROM usage_events;")
        cursor.execute("DELETE FROM idempotency_records;")
        cursor.execute("DELETE FROM webhook_events;")
        cursor.execute("DELETE FROM reconciliation_logs;")
        cursor.execute("DELETE FROM subscriptions;")
        cursor.execute("DELETE FROM tenants;")

        print("[SEED] Cleaned existing records.")

        # 1. Tenants
        tenants = [
            ("tenant_fresh", "Fresh Corp", "admin@freshcorp.com", "cus_test_fresh_001", "active"),
            ("tenant_near_limit", "NearLimit Inc", "ops@nearlimit.io", "cus_test_near_002", "active"),
            ("tenant_at_limit", "MaxedOut LLC", "billing@maxedout.com", "cus_test_maxed_003", "active"),
            ("tenant_pro", "HyperScale AI", "dev@hyperscale.ai", "cus_test_pro_004", "active"),
            ("tenant_upgrade_test", "Growth Dynamics", "finance@growthdyn.com", "cus_test_upg_005", "active"),
        ]

        cursor.executemany("""
        INSERT INTO tenants (id, name, email, stripe_customer_id, status)
        VALUES (?, ?, ?, ?, ?);
        """, tenants)

        # 2. Subscriptions
        subscriptions = [
            ("sub_fresh", "tenant_fresh", "free", "active", "sub_stripe_free_fresh"),
            ("sub_near", "tenant_near_limit", "free", "active", "sub_stripe_free_near"),
            ("sub_maxed", "tenant_at_limit", "free", "active", "sub_stripe_free_maxed"),
            ("sub_pro", "tenant_pro", "pro", "active", "sub_stripe_live_pro_001"),
            ("sub_upg", "tenant_upgrade_test", "free", "active", "sub_stripe_free_upg"),
        ]

        cursor.executemany("""
        INSERT INTO subscriptions (id, tenant_id, plan_id, status, stripe_subscription_id)
        VALUES (?, ?, ?, ?, ?);
        """, subscriptions)

        # 3. Usage Events for Near-Limit Tenant:
        # Give them 999 API calls and 99,500 tokens
        # We can seed in aggregate or rows:
        cursor.execute("""
        INSERT INTO usage_events (
            tenant_id, event_type, api_calls_qty, prompt_tokens, cached_prompt_tokens,
            completion_tokens, reasoning_tokens, total_tokens, cost_micros, idempotency_key
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            "tenant_near_limit",
            "historical_rollup",
            999,
            50000,
            20000,
            25000,
            4500,
            99500,
            250000, # $0.25
            "seed_idemp_near_limit"
        ))

        # 4. Usage Events for At-Limit Tenant:
        # Exactly 1,000 API calls and 100,000 tokens
        cursor.execute("""
        INSERT INTO usage_events (
            tenant_id, event_type, api_calls_qty, prompt_tokens, cached_prompt_tokens,
            completion_tokens, reasoning_tokens, total_tokens, cost_micros, idempotency_key
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            "tenant_at_limit",
            "historical_rollup",
            1000,
            50000,
            20000,
            25000,
            5000,
            100000,
            255000,
            "seed_idemp_at_limit"
        ))

        # 5. Usage Events for Pro Tenant:
        # 12,500 calls, 2,800,000 tokens
        cursor.execute("""
        INSERT INTO usage_events (
            tenant_id, event_type, api_calls_qty, prompt_tokens, cached_prompt_tokens,
            completion_tokens, reasoning_tokens, total_tokens, cost_micros, idempotency_key
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            "tenant_pro",
            "historical_rollup",
            12500,
            1400000,
            600000,
            700000,
            100000,
            2800000,
            7500000, # $7.50
            "seed_idemp_pro_001"
        ))

    print("[SEED SUCCESS] Successfully seeded 5 tenants, plans, and historical usage.")

if __name__ == "__main__":
    seed_database()
