"""
Stage 7 (Bonus — The AI Rematch): Quarantined AI-Generated Auth Implementation (`ai_auth_app.py`).
Generated from our first-pass prompt written from memory.

Key differences discovered when testing our Stage 3 and Stage 4 checkpoints against this AI version:
1. Token Extraction Flaw (`403` vs `401`):
   - The AI used `security = HTTPBearer()` (with default `auto_error=True`).
   - In FastAPI/Starlette, when a request is sent to `GET /protected/profile` WITHOUT an `Authorization` header,
     default `HTTPBearer()` returns `403 Forbidden {"detail": "Not authenticated"}` instead of the required
     `401 Unauthorized {"error": "Access token required"}`!
2. Naive `.replace("Bearer ", "")` Fallback:
   - In its manual header fallback, using `auth_header.replace("Bearer ", "")` accepts a header that doesn't even
     start with `"Bearer "` (e.g., `"Basic abc"` passes `"Basic abc"` straight to `get_user`).
3. Error Payload Shape (`{"detail": ...}` vs `{"error": ...}`):
   - Raising standard `HTTPException(status_code=401, detail=...)` returns `{"detail": "..."}` instead of `{"error": "..."}`.
"""

import os
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from supabase import create_client

load_dotenv()

app = FastAPI(title="AI-Generated Supabase Auth API (Quarantined)")
supabase = create_client(os.getenv("SUPABASE_URL", ""), os.getenv("SUPABASE_KEY", ""))

# FLAW 1: Default auto_error=True causes FastAPI to return 403 Forbidden (instead of 401) when header is missing!
security = HTTPBearer()


class AuthInput(BaseModel):
    email: str
    password: str


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials.replace("Bearer ", "")
    try:
        res = supabase.auth.get_user(token)
        if not res.user:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        return res.user
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


@app.post("/auth/signup", status_code=201)
def signup(data: AuthInput):
    if not data.email or not data.password:
        raise HTTPException(status_code=400, detail="Email and password required")
    res = supabase.auth.sign_up({"email": data.email, "password": data.password})
    return {"user": res.user}


@app.post("/auth/login")
def login(data: AuthInput):
    if not data.email or not data.password:
        raise HTTPException(status_code=400, detail="Email and password required")
    try:
        res = supabase.auth.sign_in_with_password({"email": data.email, "password": data.password})
        return {
            "access_token": res.session.access_token,
            "refresh_token": res.session.refresh_token,
        }
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid login credentials")


@app.post("/auth/logout", status_code=204)
def logout(user=Depends(verify_token)):
    supabase.auth.sign_out()
    return Response(status_code=204)


@app.get("/public/info")
def public_info():
    return {"message": "Welcome stranger! This info is public."}


@app.get("/protected/profile")
def profile(user=Depends(verify_token)):
    return {"user": user}
