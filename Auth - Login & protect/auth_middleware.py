"""
Stage 4: Reusable Authentication Dependency / Middleware Guard (`require_auth`).
Extracts and verifies the Bearer token via Supabase Auth (`supabase.auth.get_user(token)`).
Raises `AuthError` (handled globally as HTTP 401 with `{"error": ...}`) when the token
is missing, malformed, expired, or invalid.
"""

from typing import Any
from fastapi import Request
import supabase_client


class AuthError(Exception):
    """Custom authentication exception carrying the exact 401 error message."""

    def __init__(self, message: str, status_code: int = 401) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def get_supabase_from_request(request: Request) -> Any:
    if not hasattr(request.app.state, "supabase") or request.app.state.supabase is None:
        request.app.state.supabase = supabase_client.get_supabase_client()
    return request.app.state.supabase


def serialize_user(user: Any) -> dict[str, Any]:
    if isinstance(user, dict):
        return user
    return {
        "id": getattr(user, "id", None),
        "email": getattr(user, "email", None),
        "created_at": str(getattr(user, "created_at", "")) if getattr(user, "created_at", None) else None,
        "role": getattr(user, "role", "authenticated"),
    }


def extract_bearer_token(request: Request) -> str:
    """Extract JWT from 'Authorization: Bearer <token>' header or raise AuthError(401)."""
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise AuthError("Access token required")

    parts = auth_header.split(" ", 1)
    if len(parts) != 2 or parts[0] != "Bearer" or not parts[1].strip():
        raise AuthError("Access token required")

    return parts[1].strip()


def require_auth(request: Request) -> dict[str, Any]:
    """
    Reusable FastAPI dependency that verifies the caller's Bearer JWT with Supabase.
    Returns a dictionary with `{"user": serialized_user, "token": raw_token}`.
    """
    token = extract_bearer_token(request)
    sb = get_supabase_from_request(request)
    try:
        user_res = sb.auth.get_user(token)
        user = getattr(user_res, "user", None)
        if user is None:
            raise AuthError("Invalid or expired token")
        return {"user": serialize_user(user), "token": token}
    except AuthError:
        raise
    except Exception as exc:
        raise AuthError("Invalid or expired token") from exc
