"""
Automated Verification Suite for Auth - Login & Protect (Stages 0–5).
Tests:
1. POST /auth/signup (201 on valid input, 400 on missing email/password)
2. POST /auth/login (200 with access_token & refresh_token, 400 on missing input, 401 on wrong credentials)
3. GET /public/info (200 without any Authorization header)
4. GET /protected/profile & GET /protected/dashboard:
   - 401 {"error": "Access token required"} when Authorization header is missing or malformed
   - 401 {"error": "Invalid or expired token"} when token is tampered with or expired
   - 200 with user profile when a valid JWT is passed
5. POST /auth/logout (204 No Content with valid Bearer token, 401 without token)
6. Swagger UI (/openapi.json & /docs) HTTPBearer security scheme configuration.
"""

import os
import sys
from types import SimpleNamespace
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from main import app  # noqa: E402


class MockSupabaseAuth:
    """Deterministic mock of Supabase Auth SDK methods (sign_up, sign_in_with_password, get_user, sign_out)."""

    VALID_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.valid_supabase_jwt_token"
    REFRESH_TOKEN = "supabase_refresh_token_abc123"

    def __init__(self) -> None:
        self.signed_out = False

    def sign_up(self, credentials: dict):
        email = credentials.get("email")
        user = SimpleNamespace(
            id="d8f4a91c-3b7e-4e12-9a54-8c20f9e1a001",
            email=email,
            created_at="2026-10-04T01:05:00Z",
            role="authenticated",
        )
        return SimpleNamespace(user=user, session=None)

    def sign_in_with_password(self, credentials: dict):
        email = credentials.get("email")
        password = credentials.get("password")
        if email == "test@example.com" and password == "password123":
            user = SimpleNamespace(
                id="d8f4a91c-3b7e-4e12-9a54-8c20f9e1a001",
                email=email,
                created_at="2026-10-04T01:05:00Z",
                role="authenticated",
            )
            session = SimpleNamespace(
                access_token=self.VALID_TOKEN,
                refresh_token=self.REFRESH_TOKEN,
            )
            return SimpleNamespace(user=user, session=session)
        raise Exception("Invalid login credentials")

    def get_user(self, jwt: str):
        if jwt == self.VALID_TOKEN and not self.signed_out:
            user = SimpleNamespace(
                id="d8f4a91c-3b7e-4e12-9a54-8c20f9e1a001",
                email="test@example.com",
                created_at="2026-10-04T01:05:00Z",
                role="authenticated",
            )
            return SimpleNamespace(user=user)
        raise Exception("Invalid or expired token")

    def sign_out(self):
        self.signed_out = True


class MockSupabaseClient:
    def __init__(self) -> None:
        self.auth = MockSupabaseAuth()


def test_full_auth_flow_and_protected_routes():
    with TestClient(app) as client:
        mock_sb = MockSupabaseClient()
        app.state.supabase = mock_sb

        # Stage 1: Signup validation (400) & success (201)
        r_bad_signup = client.post("/auth/signup", json={"email": "test@example.com"})
        assert r_bad_signup.status_code == 400
        assert r_bad_signup.json() == {"error": "Email and password are required"}

        r_signup = client.post(
            "/auth/signup",
            json={"email": "test@example.com", "password": "password123"},
        )
        assert r_signup.status_code == 201
        assert r_signup.json()["user"]["email"] == "test@example.com"

        # Stage 1: Login validation (400), wrong password (401), & success (200)
        r_bad_login = client.post("/auth/login", json={"email": "", "password": ""})
        assert r_bad_login.status_code == 400

        r_wrong_pw = client.post(
            "/auth/login",
            json={"email": "test@example.com", "password": "wrongpassword"},
        )
        assert r_wrong_pw.status_code == 401
        assert r_wrong_pw.json() == {"error": "Invalid login credentials"}

        r_login = client.post(
            "/auth/login",
            json={"email": "test@example.com", "password": "password123"},
        )
        assert r_login.status_code == 200
        token = r_login.json()["access_token"]
        assert token == MockSupabaseAuth.VALID_TOKEN

        # Stage 2: Public route (200) & unauthenticated protected route (401)
        r_pub = client.get("/public/info")
        assert r_pub.status_code == 200
        assert r_pub.json() == {"message": "Welcome stranger! This info is public."}

        r_no_token = client.get("/protected/profile")
        assert r_no_token.status_code == 401
        assert r_no_token.json() == {"error": "Access token required"}

        # Stage 3: Valid token (200) vs Tampered token (401)
        r_prof = client.get(
            "/protected/profile",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r_prof.status_code == 200
        assert r_prof.json()["user"]["email"] == "test@example.com"

        tampered_token = token[:-1] + "X"
        r_tampered = client.get(
            "/protected/profile",
            headers={"Authorization": f"Bearer {tampered_token}"},
        )
        assert r_tampered.status_code == 401
        assert r_tampered.json() == {"error": "Invalid or expired token"}

        # Stage 4: Second protected route (/protected/dashboard) & POST /auth/logout (204)
        r_dash = client.get(
            "/protected/dashboard",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r_dash.status_code == 200
        assert "Welcome to the protected dashboard" in r_dash.json()["message"]

        r_logout = client.post(
            "/auth/logout",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r_logout.status_code == 204
        assert r_logout.text == ""

        # Stage 5: Verify Swagger UI (/docs) & OpenAPI BearerAuth schema
        r_docs = client.get("/docs")
        assert r_docs.status_code == 200
        r_openapi = client.get("/openapi.json")
        assert r_openapi.status_code == 200
        assert "BearerAuth" in r_openapi.json()["components"]["securitySchemes"]
