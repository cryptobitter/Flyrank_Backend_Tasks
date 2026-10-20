"""
Configuration and Pinned Pricing Constants for LLM Usage Metering & Billing Engine.
All money values are stored as exact integers (cents or micro-dollars) to eliminate floating-point drift.
"""

import os
from pydantic import BaseModel

class PricingConfig(BaseModel):
    # Prices pinned in integer micro-dollars ($1.00 USD = 1,000,000 micro-dollars)
    # 1,000,000 tokens pricing standard:
    # Fresh input: $0.150 per 1M tokens -> 0.15 micros / token (150,000 micros per 1M tokens)
    # Cached input: $0.0375 per 1M tokens (75% discount) -> 0.0375 micros / token (37,500 micros per 1M tokens)
    # Output / Completion: $0.600 per 1M tokens -> 0.60 micros / token (600,000 micros per 1M tokens)
    # Reasoning tokens: Billed as output tokens -> $0.600 per 1M tokens (600,000 micros per 1M tokens)
    # Base API Call overhead fee: 100 micro-dollars ($0.000100 per call)
    
    INPUT_TOKEN_RATE_PER_MILLION_MICROS: int = 150_000
    CACHED_INPUT_TOKEN_RATE_PER_MILLION_MICROS: int = 37_500
    OUTPUT_TOKEN_RATE_PER_MILLION_MICROS: int = 600_000
    REASONING_TOKEN_RATE_PER_MILLION_MICROS: int = 600_000
    API_CALL_BASE_FEE_MICROS: int = 100

class PlanSpec(BaseModel):
    plan_id: str
    name: str
    monthly_api_calls_quota: int
    monthly_tokens_quota: int
    base_price_cents: int  # Stored in integer cents ($29.00 = 2900 cents)

PLANS = {
    "free": PlanSpec(
        plan_id="free",
        name="Free Tier",
        monthly_api_calls_quota=1_000,
        monthly_tokens_quota=100_000,
        base_price_cents=0,
    ),
    "pro": PlanSpec(
        plan_id="pro",
        name="Pro Tier",
        monthly_api_calls_quota=50_000,
        monthly_tokens_quota=10_000_000,
        base_price_cents=2900,  # $29.00 / month
    ),
}

# Environment Settings
DATABASE_PATH = os.getenv("DATABASE_PATH", os.path.join(os.path.dirname(__file__), "billing.db"))
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "sk_test_placeholder_key_for_local_eval")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "whsec_test_secret_for_local_eval_signature_verification_123456")
PORT = int(os.getenv("PORT", "8000"))
HOST = os.getenv("HOST", "0.0.0.0")

PRICING = PricingConfig()
