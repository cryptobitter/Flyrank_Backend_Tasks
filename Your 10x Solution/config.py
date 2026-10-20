"""
Application Configuration for SentinelAI 10x Solution.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# Database
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR}/sentinel_ai.db")

# JWT Security
JWT_SECRET = os.getenv("JWT_SECRET", "super-secret-jwt-key-sentinel-ai-flyrank-2026")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

# Webhook Alerting
ALERT_WEBHOOK_URL = os.getenv("ALERT_WEBHOOK_URL", "")
WEBHOOK_HMAC_SECRET = os.getenv("WEBHOOK_HMAC_SECRET", "sentinel-hmac-secret-2026")

# Cache
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "300"))

# PDF Output Directory
REPORTS_DIR = BASE_DIR / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
