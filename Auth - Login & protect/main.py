"""
Stage 4: Reusable Auth Dependency (`require_auth`), Protected Dashboard, and POST /auth/logout.
"""

from contextlib import asynccontextmanager
from typing import Any
from fastapi import Depends, FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from auth_middleware import (
    AuthError,
    get_supabase_from_request,
    require_auth,
    serialize_user,
)
import supabase_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    client = supabase_client.get_supabase_client()
    app.state.supabase = client
    print("Server running and connected to Supabase")
    yield


app = FastAPI(title="Auth Login & Protect API", lifespan=lifespan)


@app.exception_handler(AuthError)
async def auth_error_handler(request: Request, exc: AuthError):
    return JSONResponse(status_code=exc.status_code, content={"error": exc.message})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=400, content={"error": "Email and password are required"})


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

    sb = get_supabase_from_request(request)
    try:
        res = sb.auth.sign_up({"email": email.strip(), "password": password})
        user = getattr(res, "user", None)
        if user is None:
            return JSONResponse(status_code=400, content={"error": "Unable to register user"})
        return JSONResponse(
            status_code=201,
            content={"message": "User registered successfully", "user": serialize_user(user)},
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

    sb = get_supabase_from_request(request)
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
                "user": serialize_user(user) if user else None,
            },
        )
    except Exception:
        return JSONResponse(status_code=401, content={"error": "Invalid login credentials"})


@app.post("/auth/logout", status_code=204)
def logout(request: Request, auth_ctx: dict[str, Any] = Depends(require_auth)):
    sb = get_supabase_from_request(request)
    try:
        sb.auth.sign_out()
    except Exception:
        pass
    return Response(status_code=204)


@app.get("/public/info")
def public_info():
    return {"message": "Welcome stranger! This info is public."}


@app.get("/protected/profile")
def protected_profile(auth_ctx: dict[str, Any] = Depends(require_auth)):
    return {"user": auth_ctx["user"]}


@app.get("/protected/dashboard")
def protected_dashboard(auth_ctx: dict[str, Any] = Depends(require_auth)):
    return {
        "message": f"Welcome to the protected dashboard, {auth_ctx['user']['email']}!",
        "user": auth_ctx["user"],
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=supabase_client.PORT, reload=True)
