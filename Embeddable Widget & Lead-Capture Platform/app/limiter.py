"""
Abuse Protection & Rate Limiting Engine.

Implements sliding-window counter rate limiting:
- Per-IP rate limiting (protects against single-source floods)
- Per-Widget rate limiting (protects tenant endpoints from distributed abuse)
- Returns HTTP 429 Too Many Requests with standard Retry-After headers
- Thread-safe tracking with automatic stale-entry cleanup
"""

from collections import defaultdict
import os
import threading
import time
from typing import Dict, List, Optional, Tuple

from fastapi import HTTPException, Request, status

DEFAULT_IP_MAX_REQUESTS = int(os.environ.get("RATE_LIMIT_IP_MAX_REQUESTS", "15"))
DEFAULT_IP_WINDOW = int(os.environ.get("RATE_LIMIT_IP_WINDOW_SECONDS", "60"))
DEFAULT_WIDGET_MAX_REQUESTS = int(os.environ.get("RATE_LIMIT_WIDGET_MAX_REQUESTS", "60"))
DEFAULT_WIDGET_WINDOW = int(os.environ.get("RATE_LIMIT_WIDGET_WINDOW_SECONDS", "60"))


class SlidingWindowRateLimiter:
    """Thread-safe sliding-window rate limiter."""

    def __init__(self) -> None:
        self._ip_history: Dict[str, List[float]] = defaultdict(list)
        self._widget_history: Dict[str, List[float]] = defaultdict(list)
        self._lock = threading.Lock()
        self.enabled = True

    def check_rate_limits(
        self,
        ip: str,
        widget_id: str,
        ip_limit: int = DEFAULT_IP_MAX_REQUESTS,
        ip_window: int = DEFAULT_IP_WINDOW,
        widget_limit: int = DEFAULT_WIDGET_MAX_REQUESTS,
        widget_window: int = DEFAULT_WIDGET_WINDOW,
    ) -> Tuple[bool, Optional[str], int]:
        """
        Check whether request exceeds IP or Widget limits.
        Returns (is_allowed, violation_reason, retry_after_seconds).
        """
        if not self.enabled:
            return True, None, 0

        now = time.time()
        with self._lock:
            # 1. Clean and evaluate IP history
            ip_cutoff = now - ip_window
            self._ip_history[ip] = [t for t in self._ip_history[ip] if t > ip_cutoff]

            if len(self._ip_history[ip]) >= ip_limit:
                oldest = self._ip_history[ip][0]
                retry_after = max(1, int(ip_window - (now - oldest)))
                return False, f"IP rate limit exceeded ({ip_limit} req / {ip_window}s)", retry_after

            # 2. Clean and evaluate Widget history
            widget_cutoff = now - widget_window
            self._widget_history[widget_id] = [t for t in self._widget_history[widget_id] if t > widget_cutoff]

            if len(self._widget_history[widget_id]) >= widget_limit:
                oldest = self._widget_history[widget_id][0]
                retry_after = max(1, int(widget_window - (now - oldest)))
                return False, f"Widget submission threshold exceeded ({widget_limit} req / {widget_window}s)", retry_after

            # Record request
            self._ip_history[ip].append(now)
            self._widget_history[widget_id].append(now)
            return True, None, 0

    def reset(self) -> None:
        """Reset all rate limiter tracking history."""
        with self._lock:
            self._ip_history.clear()
            self._widget_history.clear()


limiter = SlidingWindowRateLimiter()


def extract_client_ip(request: Request) -> str:
    """Extract client IP respecting X-Forwarded-For reverse proxy headers."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # Take leftmost public client IP
        return forwarded.split(",")[0].strip()
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    return request.client.host if request.client else "127.0.0.1"


def apply_submission_rate_limit(
    request: Request,
    widget_id: str,
    ip_limit: int = DEFAULT_IP_MAX_REQUESTS,
    widget_limit: int = DEFAULT_WIDGET_MAX_REQUESTS,
) -> None:
    """
    Enforce rate limits on incoming public submission requests.
    Raises HTTP 429 when threshold exceeded.
    """
    client_ip = extract_client_ip(request)
    allowed, reason, retry_after = limiter.check_rate_limits(
        ip=client_ip,
        widget_id=widget_id,
        ip_limit=ip_limit,
        widget_limit=widget_limit,
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too Many Requests: {reason}. Please retry after {retry_after} seconds.",
            headers={"Retry-After": str(retry_after)},
        )
