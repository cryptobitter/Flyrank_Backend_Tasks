"""
Quota Service: Enforces honest API boundaries and aggregates usage rollups.
Rule:
At 999 of 1,000 calls: Allowed.
At exactly 1,000 of 1,000 calls: Allowed.
At 1,001 calls: Rejected with 429 Too Many Requests (or 402 Payment Required).
"""

from typing import Dict, Any, Optional
from database import get_db
from config import PLANS

class QuotaExceededException(Exception):
    def __init__(self, message: str, status_code: int = 429, retry_after: int = 3600):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.retry_after = retry_after

def get_tenant_plan_and_subscription(tenant_id: str) -> Dict[str, Any]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT t.id as tenant_id, t.name as tenant_name, t.status as tenant_status,
               s.plan_id, s.status as subscription_status,
               p.name as plan_name, p.monthly_api_calls_quota, p.monthly_tokens_quota, p.base_price_cents
        FROM tenants t
        LEFT JOIN subscriptions s ON t.id = s.tenant_id
        LEFT JOIN plans p ON s.plan_id = p.id
        WHERE t.id = ?;
        """, (tenant_id,))
        row = cursor.fetchone()
        
        if not row:
            raise ValueError(f"Tenant '{tenant_id}' not found in database.")

        return dict(row)

def get_monthly_usage_rollup(tenant_id: str) -> Dict[str, Any]:
    """Aggregates all usage events for the current calendar month for a tenant."""
    plan_info = get_tenant_plan_and_subscription(tenant_id)

    with get_db() as conn:
        cursor = conn.cursor()
        
        # Aggregate current month usage
        cursor.execute("""
        SELECT 
            COALESCE(SUM(api_calls_qty), 0) as total_api_calls,
            COALESCE(SUM(prompt_tokens), 0) as total_prompt_tokens,
            COALESCE(SUM(cached_prompt_tokens), 0) as total_cached_prompt_tokens,
            COALESCE(SUM(completion_tokens), 0) as total_completion_tokens,
            COALESCE(SUM(reasoning_tokens), 0) as total_reasoning_tokens,
            COALESCE(SUM(total_tokens), 0) as total_tokens,
            COALESCE(SUM(cost_micros), 0) as total_cost_micros
        FROM usage_events
        WHERE tenant_id = ?
          AND strftime('%Y-%m', timestamp) = strftime('%Y-%m', 'now');
        """, (tenant_id,))
        
        usage_row = cursor.fetchone()
        usage = dict(usage_row) if usage_row else {}

    api_calls_used = usage.get("total_api_calls", 0)
    tokens_used = usage.get("total_tokens", 0)
    cost_micros = usage.get("total_cost_micros", 0)

    api_limit = plan_info["monthly_api_calls_quota"]
    token_limit = plan_info["monthly_tokens_quota"]

    api_remaining = max(0, api_limit - api_calls_used)
    tokens_remaining = max(0, token_limit - tokens_used)

    pct_calls = round((api_calls_used / api_limit) * 100, 2) if api_limit > 0 else 100.0
    pct_tokens = round((tokens_used / token_limit) * 100, 2) if token_limit > 0 else 100.0

    cost_cents = (cost_micros + 9_999) // 10_000 if cost_micros > 0 else 0

    return {
        "tenant_id": tenant_id,
        "tenant_name": plan_info["tenant_name"],
        "plan_id": plan_info["plan_id"],
        "plan_name": plan_info["plan_name"],
        "status": plan_info["subscription_status"] or plan_info["tenant_status"],
        "used": {
            "api_calls": api_calls_used,
            "tokens": tokens_used,
            "prompt_tokens": usage.get("total_prompt_tokens", 0),
            "cached_prompt_tokens": usage.get("total_cached_prompt_tokens", 0),
            "completion_tokens": usage.get("total_completion_tokens", 0),
            "reasoning_tokens": usage.get("total_reasoning_tokens", 0),
        },
        "limits": {
            "api_calls": api_limit,
            "tokens": token_limit,
        },
        "remaining": {
            "api_calls": api_remaining,
            "tokens": tokens_remaining,
        },
        "quota_percentage": {
            "api_calls": pct_calls,
            "tokens": pct_tokens,
        },
        "cost": {
            "total_cost_micros": cost_micros,
            "total_cost_cents": cost_cents,
            "formatted_usd": f"${cost_micros / 1_000_000:.6f}",
        }
    }

def check_and_enforce_quota(tenant_id: str, requested_calls: int = 1, requested_tokens: int = 0) -> Dict[str, Any]:
    """
    Checks if tenant has remaining quota for the requested action.
    Raises QuotaExceededException with 429 or 402 if boundary is violated.
    """
    rollup = get_monthly_usage_rollup(tenant_id)
    plan_id = rollup["plan_id"]
    status = rollup["status"]

    if status in ("past_due", "canceled", "suspended"):
        raise QuotaExceededException(
            message=f"Subscription for tenant '{tenant_id}' is {status}. Please update payment method to restore access.",
            status_code=402,
            retry_after=0
        )

    used_calls = rollup["used"]["api_calls"]
    limit_calls = rollup["limits"]["api_calls"]
    
    used_tokens = rollup["used"]["tokens"]
    limit_tokens = rollup["limits"]["tokens"]

    # Boundary rule: at exactly 1,000 of 1,000, call is allowed.
    # At 1,001 (used_calls + requested_calls > limit_calls), it is rejected!
    if used_calls + requested_calls > limit_calls:
        if plan_id == "free":
            raise QuotaExceededException(
                message=f"API call quota exceeded: {used_calls}/{limit_calls} calls used this month. Upgrade to Pro for 50,000 calls/month.",
                status_code=429,
                retry_after=3600
            )
        else:
            raise QuotaExceededException(
                message=f"Pro API call quota reached: {used_calls}/{limit_calls} calls used this month. Contact support for volume tiering.",
                status_code=429,
                retry_after=1800
            )

    if used_tokens + requested_tokens > limit_tokens:
        if plan_id == "free":
            raise QuotaExceededException(
                message=f"Token allowance exceeded: {used_tokens}/{limit_tokens} tokens used this month. Upgrade to Pro for 10M tokens/month.",
                status_code=429,
                retry_after=3600
            )
        else:
            raise QuotaExceededException(
                message=f"Pro token limit reached: {used_tokens}/{limit_tokens} tokens used this month. Upgrade or enable overage billing.",
                status_code=429,
                retry_after=1800
            )

    return rollup
