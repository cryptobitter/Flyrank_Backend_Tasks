"""
Exact Money Math Engine for LLM Usage Metering.
Guarantees zero floating-point drift by computing all token costs in scaled integer micro-units.
$1.00 USD = 1,000,000 micro-dollars.
"""

from typing import Dict, Any
from config import PRICING

def calculate_token_cost_micros(
    prompt_tokens: int,
    cached_prompt_tokens: int,
    completion_tokens: int,
    reasoning_tokens: int,
    include_api_base_fee: bool = True
) -> Dict[str, Any]:
    """
    Computes exact cost in integer micro-dollars ($1 = 1,000,000 micros).
    
    Rules:
    - Fresh input tokens: PRICING.INPUT_TOKEN_RATE_PER_MILLION_MICROS / 1,000,000
    - Cached input tokens: PRICING.CACHED_INPUT_TOKEN_RATE_PER_MILLION_MICROS / 1,000,000 (75% cheaper)
    - Output tokens: PRICING.OUTPUT_TOKEN_RATE_PER_MILLION_MICROS / 1,000,000
    - Reasoning tokens: Treated identically to output tokens
    - API base call fee: PRICING.API_CALL_BASE_FEE_MICROS
    """
    if prompt_tokens < 0 or cached_prompt_tokens < 0 or completion_tokens < 0 or reasoning_tokens < 0:
        raise ValueError("Token counts cannot be negative.")

    # High-precision scaled integer math: scale numerator by 1,000 to prevent premature truncation
    # 1M tokens cost in micros.
    prompt_micros_scaled = prompt_tokens * PRICING.INPUT_TOKEN_RATE_PER_MILLION_MICROS
    cached_micros_scaled = cached_prompt_tokens * PRICING.CACHED_INPUT_TOKEN_RATE_PER_MILLION_MICROS
    completion_micros_scaled = completion_tokens * PRICING.OUTPUT_TOKEN_RATE_PER_MILLION_MICROS
    reasoning_micros_scaled = reasoning_tokens * PRICING.REASONING_TOKEN_RATE_PER_MILLION_MICROS

    total_token_micros_scaled = (
        prompt_micros_scaled +
        cached_micros_scaled +
        completion_micros_scaled +
        reasoning_micros_scaled
    )

    # Round to nearest micro-dollar (add 500,000 before dividing by 1,000,000)
    token_cost_micros = (total_token_micros_scaled + 500_000) // 1_000_000
    
    # If there are active tokens but rounded to 0, preserve at least 1 micro-unit for non-zero activity
    if total_token_micros_scaled > 0 and token_cost_micros == 0:
        token_cost_micros = 1

    base_fee_micros = PRICING.API_CALL_BASE_FEE_MICROS if include_api_base_fee else 0
    total_cost_micros = token_cost_micros + base_fee_micros
    
    total_tokens = prompt_tokens + cached_prompt_tokens + completion_tokens + reasoning_tokens

    # Integer cents conversion ($1.00 = 100 cents = 1,000,000 micros -> 1 cent = 10,000 micros)
    total_cost_cents = (total_cost_micros + 9_999) // 10_000 if total_cost_micros > 0 else 0

    return {
        "prompt_tokens": prompt_tokens,
        "cached_prompt_tokens": cached_prompt_tokens,
        "completion_tokens": completion_tokens,
        "reasoning_tokens": reasoning_tokens,
        "total_tokens": total_tokens,
        "prompt_cost_micros": (prompt_micros_scaled + 500_000) // 1_000_000,
        "cached_cost_micros": (cached_micros_scaled + 500_000) // 1_000_000,
        "completion_cost_micros": (completion_micros_scaled + 500_000) // 1_000_000,
        "reasoning_cost_micros": (reasoning_micros_scaled + 500_000) // 1_000_000,
        "token_cost_micros": token_cost_micros,
        "base_fee_micros": base_fee_micros,
        "total_cost_micros": total_cost_micros,
        "total_cost_cents": total_cost_cents,
        "formatted_usd": f"${total_cost_micros / 1_000_000:.6f}",
    }
