"""
Stage 3: The Guard — Token Verification on GET /protected/profile via supabase.auth.get_user(token).
"""

from contextlib import asynccontextmanager
from typing import Any
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
import supabase_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    client = supabase_client.get_supabase_client()
    app.state.supabase = client
    print("Server running and connected to Supabase")
    yield


app = FastAPI(title="Auth Login & Protect API", lifespan=lifespan)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=400, content={"error": "Email and password are required"})


def _get_supabase(request: Request) -> Any:
    if not hasattr(request.app.state, "supabase") or request.app.state.supabase is None:
        request.app.state.supabase = supabase_client.get_supabase_client()
    return request.app.state.supabase


def _serialize_user(user: Any) -> dict[str, Any]:
    if isinstance(user, dict):
        return user
    return {
        "id": getattr(user, "id", None),
        "email": getattr(user, "email", None),
        "created_at": str(getattr(user, "created_at", "")) if getattr(user, "created_at", None) else None,
        "role": getattr(user, "role", "authenticated"),
    }


def _extract_bearer_token(request: Request) -> str | None:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    token = auth_header[len("Bearer "):].strip()
    return token if token else None


@app.post("/auth/signup", status_code=201)
async def signup(request: Request):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON body"})

    if not isinstance(body, dict):
        return JSONResponse(status_code=400, content={"error": "Request body must be a JSON object"})

    email = body.get("email")
    password = body.get("password")
    if not isinstance(email, str) or not email.strip() or not isinstance(password, str) or not password.strip():
        return JSONResponse(status_code=400, content={"error": "Email and password are required"})

    sb = _get_supabase(request)
    try:
        res = sb.auth.sign_up({"email": email.strip(), "password": password})
        user = getattr(res, "user", None)
        if user is None:
            return JSONResponse(status_code=400, content={"error": "Unable to register user"})
        return JSONResponse(
            status_code=201,
            content={"message": "User registered successfully", "user": _serialize_user(user)},
        )
    except Exception as exc:
        return JSONResponse(status_code=400, content={"error": str(exc)})


@app.post("/auth/login")
async def login(request: Request):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON body"})

    if not isinstance(body, dict):
        return JSONResponse(status_code=400, content={"error": "Request body must be a JSON object"})

    email = body.get("email")
    password = body.get("password")
    if not isinstance(email, str) or not email.strip() or not isinstance(password, str) or not password.strip():
        return JSONResponse(status_code=400, content={"error": "Email and password are required"})

    sb = _get_supabase(request)
    try:
        res = sb.auth.sign_in_with_password({"email": email.strip(), "password": password})
        session = getattr(res, "session", None)
        user = getattr(res, "user", None)
        if session is None or not getattr(session, "access_token", None):
            return JSONResponse(status_code=401, content={"error": "Invalid login credentials"})
        return JSONResponse(
            status_code=200,
            content={
                "access_token": getattr(session, "access_token", None),
                "refresh_token": getattr(session, "refresh_token", None),
                "token_type": "bearer",
                "user": _serialize_user(user) if user else None,
            },
        )
    except Exception:
        return JSONResponse(status_code=401, content={"error": "Invalid login credentials"})


@app.get("/public/info")
def public_info():
    return {"message": "Welcome stranger! This info is public."}


@app.get("/protected/profile")
def protected_profile(request: Request):
    token = _extract_bearer_token(request)
    if not token:
        return JSONResponse(status_code=401, content={"error": "Access token required"})

    sb = _get_supabase(request)
    try:
        user_res = sb.auth.get_user(token)
        user = getattr(user_res, "user", None)
        if user is None:
            return JSONResponse(status_code=401, content={"error": "Invalid or expired token"})
        return JSONResponse(
            status_code=200,
            content={"user": _serialize_user(user)},
        )
    except Exception:
        return JSONResponse(status_code=401, content={"error": "Invalid or expired token"})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=supabase_client.PORT, reload=True)
