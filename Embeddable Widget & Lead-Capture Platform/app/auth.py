"""
Authentication & Multi-Tenant Isolation Module.

Enforces:
- PBKDF2-SHA256 password hashing with cryptographic salt
- Stateless JWT issuance and Bearer token verification
- Tenant isolation dependency (get_current_tenant)
"""

from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import os
import secrets
from typing import Any, Dict, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.database import get_db

SECRET_KEY = os.environ.get("JWT_SECRET", "super_secret_jwt_signing_key_at_least_32_characters_long_for_security")
ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

security = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    """Hash password using PBKDF2-HMAC-SHA256 with a unique random salt."""
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations=100_000,
    )
    return f"{salt}${key.hex()}"


def verify_password(plain_password: str, stored_hash: str) -> bool:
    """Verify password against stored salt$hash."""
    try:
        salt, key_hex = stored_hash.split("$")
        computed_key = hashlib.pbkdf2_hmac(
            "sha256",
            plain_password.encode("utf-8"),
            salt.encode("utf-8"),
            iterations=100_000,
        )
        return hmac.compare_digest(computed_key.hex(), key_hex)
    except Exception:
        return False


def create_access_token(tenant_id: str, email: str, expires_delta: Optional[timedelta] = None) -> str:
    """Generate signed JWT access token for a tenant."""
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode = {
        "sub": tenant_id,
        "email": email,
        "iat": now,
        "exp": expire,
    }
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Dict[str, Any]:
    """Decode and validate JWT access token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired credentials: {str(exc)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_tenant(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Dict[str, Any]:
    """
    FastAPI Dependency: Authenticate tenant from Authorization Bearer header.
    Guarantees tenant isolation: all child queries are strictly scoped to tenant['id'].
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please provide Authorization: Bearer <token>",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(credentials.credentials)
    tenant_id: str = payload.get("sub")
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload missing tenant identity (sub).",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Fetch tenant record from DB
    with get_db() as conn:
        row = conn.execute("SELECT id, name, email, created_at FROM tenants WHERE id = ?", (tenant_id,)).fetchone()
        if not row:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Tenant account no longer exists or has been deactivated.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return dict(row)
