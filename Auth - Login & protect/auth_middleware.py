"""
Stage 5: Reusable Authentication Dependency with FastAPI `HTTPBearer` for Swagger UI (`/docs`).
Configures `HTTPBearer(auto_error=False)` so Swagger UI displays the 'Authorize' padlock button
and lock icons on protected routes while preserving exact HTTP 401 JSON error responses.
"""

from typing import Any
from fastapi import Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import supabase_client

bearer_scheme = HTTPBearer(
    scheme_name="BearerAuth",
    description="Paste the JWT `access_token` returned by `POST /auth/login`.",
    auto_error=False,
)


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


def extract_bearer_token(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = None,
) -> str:
    """
    Extract JWT from `HTTPBearer` credentials or raw `Authorization: Bearer <token>` header.
    Raises `AuthError("Access token required", 401)` if missing or malformed.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise AuthError("Access token required")

    parts = auth_header.split(" ", 1)
    if len(parts) != 2 or parts[0] != "Bearer" or not parts[1].strip():
        raise AuthError("Access token required")

    if credentials and credentials.credentials.strip():
        return credentials.credentials.strip()
    return parts[1].strip()


def require_auth(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
) -> dict[str, Any]:
    """
    Reusable FastAPI dependency that registers `HTTPBearer` in OpenAPI/Swagger UI
    and verifies the caller's Bearer JWT with Supabase (`supabase.auth.get_user(token)`).
    """
    token = extract_bearer_token(request, credentials)
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
