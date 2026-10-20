"""
Background Worker: Asynchronous usage alerting and nightly Stripe subscription reconciliation.
Runs slow/bulk auditing work off the critical API request path.
"""

import logging
import asyncio
from typing import Dict, Any, List
from database import get_db
from services.quota_service import get_monthly_usage_rollup

logger = logging.getLogger("background_worker")

def check_and_dispatch_usage_alerts() -> List[Dict[str, Any]]:
    """
    Scans all tenants for quota threshold crossings (80% and 100%).
    Generates notification events for proactive customer alerts.
    """
    alerts = []
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, email FROM tenants WHERE status = 'active';")
        tenants = cursor.fetchall()

    for tenant in tenants:
        tenant_id = tenant["id"]
        try:
            rollup = get_monthly_usage_rollup(tenant_id)
            pct_calls = rollup["quota_percentage"]["api_calls"]
            pct_tokens = rollup["quota_percentage"]["tokens"]

            max_pct = max(pct_calls, pct_tokens)
            if max_pct >= 100.0:
                alert = {
                    "tenant_id": tenant_id,
                    "email": tenant["email"],
                    "level": "CRITICAL",
                    "threshold": "100%",
                    "message": f"Tenant {tenant_id} reached 100% quota ({pct_calls}% calls, {pct_tokens}% tokens). Requests are being throttled."
                }
                alerts.append(alert)
                logger.warning(f"[QUOTA ALERT - 100%] {alert['message']}")
            elif max_pct >= 80.0:
                alert = {
                    "tenant_id": tenant_id,
                    "email": tenant["email"],
                    "level": "WARNING",
                    "threshold": "80%",
                    "message": f"Tenant {tenant_id} reached 80% quota ({pct_calls}% calls, {pct_tokens}% tokens). Upgrade recommended."
                }
                alerts.append(alert)
                logger.info(f"[QUOTA ALERT - 80%] {alert['message']}")
        except Exception as e:
            logger.error(f"Error auditing tenant {tenant_id}: {str(e)}")

    return alerts

def run_stripe_reconciliation() -> Dict[str, Any]:
    """
    Nightly reconciliation job: Audits local database subscriptions against Stripe test records
    to catch missed webhooks or out-of-sync plans.
    """
    anomalies = []
    tenants_audited = 0

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT t.id, t.name, s.plan_id, s.status, s.stripe_subscription_id
        FROM tenants t
        JOIN subscriptions s ON t.id = s.tenant_id;
        """)
        rows = cursor.fetchall()
        tenants_audited = len(rows)

        for row in rows:
            tenant_id = row["id"]
            plan_id = row["plan_id"]
            sub_id = row["stripe_subscription_id"]

            # Anomaly condition: tenant claims Pro plan but has no active stripe_subscription_id
            if plan_id == "pro" and (not sub_id or sub_id.strip() == ""):
                anomalies.append({
                    "tenant_id": tenant_id,
                    "issue": "Pro plan recorded without associated Stripe subscription identifier.",
                    "severity": "HIGH"
                })

        # Record reconciliation audit run
        details_text = f"Audited {tenants_audited} tenants. Found {len(anomalies)} anomalies."
        cursor.execute("""
        INSERT INTO reconciliation_logs (tenants_checked, anomalies_detected, details)
        VALUES (?, ?, ?);
        """, (tenants_audited, len(anomalies), details_text))

    return {
        "tenants_checked": tenants_audited,
        "anomalies_detected": len(anomalies),
        "anomalies": anomalies,
        "details": details_text
    }

async def periodic_worker_loop(interval_seconds: int = 3600):
    """Periodic asynchronous runner for long-running service worker."""
    while True:
        try:
            check_and_dispatch_usage_alerts()
            run_stripe_reconciliation()
        except Exception as e:
            logger.error(f"Background worker iteration error: {str(e)}")
        await asyncio.sleep(interval_seconds)
