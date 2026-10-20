"""
Caching & Idempotency Store:
- In-memory TTL Cache for fast playbook retrieval
- Idempotency Key deduplication preventing duplicate incident ingestion
"""

import time
from typing import Any, Dict, Optional
from config import CACHE_TTL_SECONDS


class TTLCache:
    def __init__(self, default_ttl: int = CACHE_TTL_SECONDS):
        self.default_ttl = default_ttl
        self._cache: Dict[str, tuple[Any, float]] = {}

    def get(self, key: str) -> Optional[Any]:
        if key not in self._cache:
            return None
        value, expiry = self._cache[key]
        if time.time() > expiry:
            del self._cache[key]
            return None
        return value

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        expiry = time.time() + (ttl or self.default_ttl)
        self._cache[key] = (value, expiry)

    def delete(self, key: str) -> None:
        if key in self._cache:
            del self._cache[key]

    def clear(self) -> None:
        self._cache.clear()


class IdempotencyStore:
    def __init__(self, ttl_seconds: int = 3600):
        self.ttl_seconds = ttl_seconds
        self._store: Dict[str, tuple[str, float]] = {}  # key -> (incident_id, expiry)

    def set_id(self, key: str, incident_id: str):
        now = time.time()
        self._store[key] = (incident_id, now + self.ttl_seconds)

    def check_and_set(self, key: str, incident_id: str) -> tuple[bool, Optional[str]]:
        """
        Returns (is_duplicate, existing_incident_id).
        If new, registers the key and returns (False, None).
        """
        now = time.time()
        self._purge_expired(now)

        if key in self._store:
            existing_id, _ = self._store[key]
            return True, existing_id

        self._store[key] = (incident_id, now + self.ttl_seconds)
        return False, None

    def _purge_expired(self, now: float):
        expired = [k for k, (_, exp) in self._store.items() if now > exp]
        for k in expired:
            del self._store[k]

    def clear(self):
        self._store.clear()


# Global singletons
ttl_cache = TTLCache()
idempotency_store = IdempotencyStore()
