"""
Meter Service: Idempotent usage recording and quota gating.
Guarantees exactly-once recording of billable usage events under client retries.
"""

import json
import hashlib
import uuid
from typing import Optional, Dict, Any, Tuple
from database import get_db
from pricing import calculate_token_cost_micros
from services.quota_service import check_and_enforce_quota, get_monthly_usage_rollup

class IdempotencyConflictException(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message

def compute_payload_hash(payload: Dict[str, Any]) -> str:
    serialized = json.dumps(payload, sort_keys=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

def record_billable_generation(
    tenant_id: str,
    prompt: str,
    prompt_tokens: Optional[int] = None,
    cached_prompt_tokens: Optional[int] = None,
    completion_tokens: Optional[int] = None,
    reasoning_tokens: Optional[int] = None,
    idempotency_key: Optional[str] = None
) -> Tuple[Dict[str, Any], bool]:
    """
    Executes billable AI generation workflow:
    1. Idempotency cache check
    2. Token and cost calculation
    3. Quota boundary enforcement
    4. Atomic database insertion
    5. Cache response for retries
    
    Returns (response_data_dict, is_cached_boolean)
    """
    request_payload = {
        "tenant_id": tenant_id,
        "prompt": prompt,
        "prompt_tokens": prompt_tokens,
        "cached_prompt_tokens": cached_prompt_tokens,
        "completion_tokens": completion_tokens,
        "reasoning_tokens": reasoning_tokens,
    }
    req_hash = compute_payload_hash(request_payload)

    # 1. Idempotency Check
    if idempotency_key:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT request_hash, response_status, response_body FROM idempotency_records WHERE key = ?;",
                (idempotency_key,)
            )
            cached_record = cursor.fetchone()
            if cached_record:
                if cached_record["request_hash"] != req_hash:
                    raise IdempotencyConflictException(
                        f"Idempotency-Key '{idempotency_key}' was previously used with a different request payload."
                    )
                # Idempotent match: return identical previous response with cached flag
                saved_response = json.loads(cached_record["response_body"])
                saved_response["cached_response"] = True
                return saved_response, True

    # 2. Token Estimation / Resolution
    # If caller didn't pass explicit simulated tokens, derive realistic numbers from prompt
    p_tokens = prompt_tokens if prompt_tokens is not None else max(10, len(prompt.split()) * 2)
    c_p_tokens = cached_prompt_tokens if cached_prompt_tokens is not None else (p_tokens // 4)
    out_tokens = completion_tokens if completion_tokens is not None else 180
    r_tokens = reasoning_tokens if reasoning_tokens is not None else 45

    cost_info = calculate_token_cost_micros(
        prompt_tokens=p_tokens,
        cached_prompt_tokens=c_p_tokens,
        completion_tokens=out_tokens,
        reasoning_tokens=r_tokens,
        include_api_base_fee=True
    )
    total_tokens = cost_info["total_tokens"]

    # 3. Quota Boundary Enforcement
    # Boundary check: raises QuotaExceededException (429 / 402) if boundary is crossed
    rollup_before = check_and_enforce_quota(
        tenant_id=tenant_id,
        requested_calls=1,
        requested_tokens=total_tokens
    )

    # 4. Atomic Persistence (Single Transaction)
    request_id = f"req_{uuid.uuid4().hex[:12]}"
    simulated_output = (
        f"Simulated LLM response for tenant '{tenant_id}': Successfully processed prompt "
        f"('{prompt[:40]}...') utilizing {total_tokens} total tokens."
    )

    quota_status = {
        "api_calls_used": rollup_before["used"]["api_calls"] + 1,
        "api_calls_limit": rollup_before["limits"]["api_calls"],
        "api_calls_remaining": max(0, rollup_before["remaining"]["api_calls"] - 1),
        "tokens_used": rollup_before["used"]["tokens"] + total_tokens,
        "tokens_limit": rollup_before["limits"]["tokens"],
        "tokens_remaining": max(0, rollup_before["remaining"]["tokens"] - total_tokens),
        "percentage_calls_used": round(((rollup_before["used"]["api_calls"] + 1) / rollup_before["limits"]["api_calls"]) * 100, 2),
        "percentage_tokens_used": round(((rollup_before["used"]["tokens"] + total_tokens) / rollup_before["limits"]["tokens"]) * 100, 2),
    }

    response_data = {
        "request_id": request_id,
        "tenant_id": tenant_id,
        "content": simulated_output,
        "usage": {
            "prompt_tokens": p_tokens,
            "cached_prompt_tokens": c_p_tokens,
            "completion_tokens": out_tokens,
            "reasoning_tokens": r_tokens,
            "total_tokens": total_tokens,
        },
        "cost": {
            "total_cost_micros": cost_info["total_cost_micros"],
            "total_cost_cents": cost_info["total_cost_cents"],
            "formatted_usd": cost_info["formatted_usd"],
            "token_cost_micros": cost_info["token_cost_micros"],
            "base_fee_micros": cost_info["base_fee_micros"],
            "prompt_cost_micros": cost_info["prompt_cost_micros"],
            "cached_cost_micros": cost_info["cached_cost_micros"],
            "completion_cost_micros": cost_info["completion_cost_micros"],
            "reasoning_cost_micros": cost_info["reasoning_cost_micros"],
        },
        "quota_status": quota_status,
        "cached_response": False
    }

    with get_db() as conn:
        cursor = conn.cursor()
        
        # Insert Usage Event
        cursor.execute("""
        INSERT INTO usage_events (
            tenant_id, event_type, api_calls_qty, prompt_tokens, cached_prompt_tokens,
            completion_tokens, reasoning_tokens, total_tokens, cost_micros, idempotency_key
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            tenant_id,
            "llm_completion",
            1,
            p_tokens,
            c_p_tokens,
            out_tokens,
            r_tokens,
            total_tokens,
            cost_info["total_cost_micros"],
            idempotency_key
        ))

        # Cache in Idempotency Store
        if idempotency_key:
            cursor.execute("""
            INSERT INTO idempotency_records (
                key, tenant_id, request_hash, response_status, response_body
            ) VALUES (?, ?, ?, ?, ?);
            """, (
                idempotency_key,
                tenant_id,
                req_hash,
                200,
                json.dumps(response_data)
            ))

    return response_data, False
