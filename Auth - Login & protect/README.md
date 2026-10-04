# Auth — Login & Protect (Supabase Auth + FastAPI + JWT Middleware)

> **Track**: FlyRank Internship · Backend Development Track · Auth — Login & Protect  
> **Lane**: Python (`FastAPI` + `supabase` SDK + built-in OpenAPI/Swagger UI at `/docs`)

---

## 1. What This Project Is

In previous assignments, our API endpoints were open to any caller. This project secures a FastAPI backend using **Supabase Auth** as the **Identity Provider (IdP)** and **JSON Web Tokens (JWTs)** for stateless route protection.

### The Trust Triangle Architecture

```text
1. Sign Up / Log In:   Client  ──(email + password)──►  FastAPI  ──►  Supabase Auth (IdP)
2. Issue JWT Pass:     Supabase Auth  ──(signed JWT access_token)──►  Client
3. Protected Request:  Client  ──(Authorization: Bearer <token>)──►  FastAPI Middleware (require_auth)
4. Token Verification: FastAPI Middleware  ──(supabase.auth.get_user(token))──►  200 OK or 401 Unauthorized
```

---

## 2. How to Set Up Local Environment Variables

1. Create a free project at [supabase.com](https://supabase.com/) and navigate to **Project Settings $\rightarrow$ API**.
2. Copy `.env.example` to `.env` inside `Auth - Login & protect/`:
   ```bash
   cp .env.example .env
   ```
3. Fill in your `SUPABASE_URL` and `SUPABASE_KEY` (`anon` public key):
   ```ini
   SUPABASE_URL=https://your-project-id.supabase.co
   SUPABASE_KEY=your-public-anon-key
   PORT=3000
   ```
   *(CRITICAL: `.env` is listed in [`.gitignore`](./.gitignore) so private Supabase keys are never committed to GitHub.)*

---

## 3. How to Run the Server (Single Command)

Install dependencies and start the server on port `3000`:

```bash
pip install -r requirements.txt
uvicorn main:app --reload --port 3000
```

Or run directly with Python:
```bash
python main.py
```

### Run the Automated Verification Suite (`pytest`)
```bash
pytest test_auth.py -v
```

---

## 4. API Reference Table

| Method | Endpoint | Auth Required? | Request Body / Header | Success Status | Error Statuses | Purpose |
| :---: | :--- | :---: | :--- | :---: | :---: | :--- |
| `POST` | `/auth/signup` | ❌ No | `{"email": "...", "password": "..."}` | `201 Created` | `400 Bad Request` | Register a new user account in Supabase Auth (`supabase.auth.sign_up`). |
| `POST` | `/auth/login` | ❌ No | `{"email": "...", "password": "..."}` | `200 OK` *(returns `access_token` & `refresh_token`)* | `400 Bad Request`<br>`401 Unauthorized` | Authenticate user credentials (`supabase.auth.sign_in_with_password`) and return JWT. |
| `POST` | `/auth/logout` | ✅ **Yes (`Bearer <token>`)** | `Authorization: Bearer <token>` | `204 No Content` | `401 Unauthorized` | Verify active session token via `require_auth` and terminate session (`supabase.auth.sign_out`). |
| `GET` | `/public/info` | ❌ No | None | `200 OK` | — | Return public information accessible without any token. |
| `GET` | `/protected/profile` | ✅ **Yes (`Bearer <token>`)** | `Authorization: Bearer <token>` | `200 OK` *(returns verified user metadata)* | `401 Unauthorized` | Protected route guarded by `require_auth` dependency (`supabase.auth.get_user(token)`). |
| `GET` | `/protected/dashboard` | ✅ **Yes (`Bearer <token>`)** | `Authorization: Bearer <token>` | `200 OK` | `401 Unauthorized` | Second protected route proving reusable middleware/dependency protection. |

---

## 5. Swagger UI (`/docs`) with Bearer Token Authorization

FastAPI's `HTTPBearer` security scheme (`BearerAuth`) is configured in [`auth_middleware.py`](./auth_middleware.py). Opening `http://localhost:3000/docs` displays the **Authorize** padlock button at the top right and lock icons next to `/auth/logout`, `/protected/profile`, and `/protected/dashboard`:

![Swagger UI Screenshot with BearerAuth](./swagger_ui_screenshot.png)

---

## 6. Stage 7 (Bonus) — AI vs. Me Security & Code Review

After building Stages 0–6 by hand, we wrote a specification prompt from memory and quarantined the AI's generated code in [`ai-version/ai_auth_app.py`](./ai-version/ai_auth_app.py).

### Our Prompt Written from Memory

```text
Build a Python FastAPI authentication API integrated with the Supabase Python SDK (`supabase`).
Read SUPABASE_URL, SUPABASE_KEY, and PORT=3000 from `.env`.
Implement these routes:
1. POST /auth/signup -> 201 Created with user object; 400 if email or password is missing.
2. POST /auth/login -> 200 OK with access_token and refresh_token; 400 if fields are missing; 401 {"error": "Invalid login credentials"} on wrong credentials.
3. GET /public/info -> 200 OK with {"message": "Welcome stranger! This info is public."}.
4. GET /protected/profile -> Protected by a reusable FastAPI dependency that extracts the JWT from `Authorization: Bearer <token>`, verifies it with `supabase.auth.get_user(token)`, returns 401 if missing or invalid, and 200 OK with the user profile if valid.
5. POST /auth/logout -> Protected route that calls `supabase.auth.sign_out()` and returns 204 No Content.
Configure FastAPI's HTTPBearer so Swagger UI at /docs shows the Authorize padlock button.
```

### "AI vs. Me" Analysis (Testing Stage 3 & Stage 4 Checkpoints Against the AI Code)

1. **How it handled token extraction (`403` vs `401` trap & `"Bearer "` prefix parsing)**:
   - **What the AI did**: The AI instantiated `security = HTTPBearer()` with default settings (`auto_error=True`). When we fired our Stage 2 checkpoint (`curl -i http://localhost:3000/protected/profile` with no header) at the AI's code, FastAPI's built-in `HTTPBearer` intercepted the request and returned **`403 Forbidden` with `{"detail": "Not authenticated"}`** instead of the required **`401 Unauthorized` with `{"error": "Access token required"}`**.
   - **How our hand-built version solved it**: In [`auth_middleware.py`](./auth_middleware.py), we passed `HTTPBearer(auto_error=False)` so Swagger UI still renders the **Authorize** padlock button, while our `extract_bearer_token()` function explicitly splits the `Authorization` header (`parts = auth_header.split(" ", 1)`), verifies `parts[0] == "Bearer"` and `parts[1].strip() != ""`, and raises `AuthError("Access token required", status_code=401)`.
2. **Security & Reliability Flaws Introduced by the AI**:
   - **Uncaught `sign_up` exceptions (`500 Internal Server Error`)**: In [`ai-version/ai_auth_app.py`](./ai-version/ai_auth_app.py), `POST /auth/signup` called `supabase.auth.sign_up(...)` without a `try...except` block. Passing an invalid email format or duplicate user caused an unhandled exception (`500 Internal Server Error`) instead of a clean `400 Bad Request`.
   - **Pydantic `422` vs `400` on missing fields**: Sending `{}` to `POST /auth/signup` in the AI version triggered FastAPI's default `422 Unprocessable Entity` before the route handler's `if not data.email:` check could even run. Our hand-built version overrides `@app.exception_handler(RequestValidationError)` to guarantee HTTP `400`.
3. **What our prompt missed and what the AI silently assumed**:
   - Our prompt specified `401 {"error": "Invalid login credentials"}` on login, but didn't explicitly state that **every** error response must use the JSON key `"error"` instead of FastAPI's default `"detail"`, nor did it warn about `HTTPBearer(auto_error=False)`. The AI silently defaulted to `HTTPException(detail=...)` and `HTTPBearer(auto_error=True)`.

---

## 7. Requirements Checklist

- [x] Server starts on localhost with a single documented terminal command (`uvicorn main:app --reload --port 3000`).
- [x] `.env` file is properly used and `.gitignore` prevents it from being pushed to GitHub.
- [x] `POST /auth/signup` and `POST /auth/login` communicate with Supabase Auth (`sign_up` & `sign_in_with_password`).
- [x] `GET /protected/profile` extracts and verifies the Bearer token from the HTTP `Authorization` header (`get_user(token)`).
- [x] Proper status codes used: `201` on signup, `200` on successful login/read, `204` on logout, `400` on missing inputs, and `401` on missing, incorrect, or expired tokens.
- [x] Auth check extracted into reusable middleware/dependency ([`auth_middleware.py`](./auth_middleware.py)).
- [x] Swagger UI configured at `/docs` with Bearer Token Authorization (`HTTPBearer`) fully functional.
- [x] Public GitHub repo with ≥6 clean stage commits and a comprehensive README.
