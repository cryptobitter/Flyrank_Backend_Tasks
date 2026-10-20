"""
FastAPI Server & Public API for Embeddable Widget & Lead-Capture Platform.

Implements all six core concerns:
1. Multi-tenant Widget Management API (CRUD + Auth)
2. Embed Snippet Generation (<script src="..."></script>)
3. Fast, Cached Widget Delivery (versioned bundle + HTTP Cache-Control headers)
4. Public Submission Endpoint (CORS, Preflight OPTIONS, Boundary Validation)
5. Abuse Protection, Fallback Geo Enrichment & Safe Side Effects
6. Owner Analytics Dashboard API (Aggregation queries)
"""

from datetime import datetime, timezone
import json
import os
import sys
import uuid
from typing import Any, Dict, List, Optional

# Ensure local module imports resolve cleanly
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.auth import (
    create_access_token,
    get_current_tenant,
    hash_password,
    verify_password,
)
from app.database import get_db, init_db, utc_now_iso
from app.geo import geo_service
from app.limiter import apply_submission_rate_limit, extract_client_ip, limiter
from app.notifications import notification_service
from app.schemas import (
    FormFieldConfig,
    PublicSubmissionRequest,
    PublicSubmissionResponse,
    PublicWidgetConfigResponse,
    TenantLoginRequest,
    TenantRegisterRequest,
    TokenResponse,
    WidgetCreateRequest,
    WidgetUpdateRequest,
)

# Initialize database schema on startup
init_db()

app = FastAPI(
    title="FlyRank Embeddable Widget & Lead-Capture Platform",
    description="Public internet widget ingestion engine with CORS, rate limiting, geo fallback, and safe side effects.",
    version="1.0.0",
)

# 1. Cross-Origin Resource Sharing (CORS) Middleware
# Required so client scripts running on any customer domain (http://localhost:5500, file://, etc.)
# can fetch widget configs and submit forms across origins.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Open public internet ingress
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["Retry-After", "X-RateLimit-Remaining", "Cache-Control", "Content-Type"],
)

STATIC_DIR = os.path.join(PARENT_DIR, "static")
WIDGET_JS_PATH = os.path.join(STATIC_DIR, "widget.v1.js")


# =====================================================================
# Public Widget Script & Cached Asset Delivery
# =====================================================================

@app.get("/widget.js", tags=["Widget Delivery"])
@app.get("/v1/widget.js", tags=["Widget Delivery"])
def serve_widget_script() -> FileResponse:
    """
    Serve the embeddable JavaScript bundle with long-lived caching.
    - Versioned URL / immutable asset delivery
    - Cache-Control: public, max-age=31536000, immutable
    """
    if not os.path.isfile(WIDGET_JS_PATH):
        raise HTTPException(status_code=404, detail="Widget bundle not found on server.")

    return FileResponse(
        path=WIDGET_JS_PATH,
        media_type="application/javascript",
        headers={
            "Cache-Control": "public, max-age=31536000, immutable",
            "Access-Control-Allow-Origin": "*",
        },
    )


# =====================================================================
# Public Widget Config Endpoint (Cached Delivery)
# =====================================================================

@app.get("/api/v1/widgets/{widget_id}/config", tags=["Widget Delivery"])
def get_public_widget_config(widget_id: str, request: Request, response: Response) -> Dict[str, Any]:
    """
    Public configuration endpoint read by the client widget script:
    - Sets short-lived cache headers: Cache-Control: public, max-age=60, stale-while-revalidate=120
    - Returns lightweight form structure and styling parameters
    """
    with get_db() as conn:
        row = conn.execute(
            """
            SELECT id, title, description, widget_type, button_text, form_fields, theme_color, is_active
            FROM widgets WHERE id = ?
            """,
            (widget_id,),
        ).fetchone()

        if not row or not row["is_active"]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Widget '{widget_id}' was not found or is currently inactive.",
            )

        # Set standard CDN / client cache headers
        response.headers["Cache-Control"] = "public, max-age=60, stale-while-revalidate=120"
        response.headers["Access-Control-Allow-Origin"] = "*"

        base_url = str(request.base_url).rstrip("/")
        form_fields_raw = json.loads(row["form_fields"]) if row["form_fields"] else []

        return {
            "id": row["id"],
            "title": row["title"],
            "description": row["description"],
            "widget_type": row["widget_type"],
            "button_text": row["button_text"],
            "theme_color": row["theme_color"],
            "form_fields": form_fields_raw,
            "submit_url": f"{base_url}/api/v1/widgets/{widget_id}/submit",
        }


# =====================================================================
# Public Form Submission Endpoint (Hardened Ingestion Path)
# =====================================================================

@app.post(
    "/api/v1/widgets/{widget_id}/submit",
    status_code=status.HTTP_201_CREATED,
    response_model=PublicSubmissionResponse,
    tags=["Public Submission"],
)
async def submit_widget_lead(
    widget_id: str,
    payload: PublicSubmissionRequest,
    request: Request,
) -> PublicSubmissionResponse:
    """
    Public Submission Gateway:
    1. Boundary Validation: validates payload structure and rejects oversized input
    2. Abuse Protection: Rate limiting per IP and per Widget (HTTP 429)
    3. Spam Detection: Evaluates honeypot field (_hp_website)
    4. Geolocation Fallback Chain: Provider A -> Provider B -> Degraded success
    5. Tenant Lead Persistence: Stores valid submission in DB
    6. Safe Side Effects: Triggers notification with fail-safe error boundary
    """
    client_ip = extract_client_ip(request)
    user_agent = request.headers.get("User-Agent", "Unknown")

    # 1. Rate limiting check (Raises 429 if threshold exceeded)
    apply_submission_rate_limit(request=request, widget_id=widget_id)

    # 2. Verify Widget exists and fetch owner tenant ID
    with get_db() as conn:
        widget_row = conn.execute(
            """
            SELECT id, tenant_id, title, is_active
            FROM widgets WHERE id = ?
            """,
            (widget_id,),
        ).fetchone()

        if not widget_row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Widget '{widget_id}' does not exist.",
            )

        if not widget_row["is_active"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This widget is currently inactive and cannot accept submissions.",
            )

        tenant_id = widget_row["tenant_id"]

        # 3. Honeypot Spam Protection (Probe 6)
        # If the hidden honeypot field is filled, a bot filled it.
        # We record as spam or reject without leaking details.
        is_spam = False
        if payload.hp_website and len(payload.hp_website.strip()) > 0:
            is_spam = True
            submission_id = f"sub_spam_{uuid.uuid4().hex[:10]}"
            conn.execute(
                """
                INSERT INTO submissions (
                    id, widget_id, tenant_id, data, ip_address, user_agent,
                    country, city, region, geo_provider, is_spam, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
                """,
                (
                    submission_id,
                    widget_id,
                    tenant_id,
                    json.dumps(payload.data),
                    client_ip,
                    user_agent,
                    "Unknown",
                    "Unknown",
                    "Unknown",
                    "honeypot_caught",
                    utc_now_iso(),
                ),
            )
            conn.commit()
            return PublicSubmissionResponse(
                status="spam_blocked",
                submission_id=submission_id,
                message="Submission received.",
                geo=None,
            )

        # 4. Geolocation Enrichment Fallback Chain (Probe 4)
        geo_info = geo_service.enrich_ip(client_ip)

        # 5. Persist Clean Lead to Database
        submission_id = f"sub_{uuid.uuid4().hex[:12]}"
        now = utc_now_iso()

        conn.execute(
            """
            INSERT INTO submissions (
                id, widget_id, tenant_id, data, ip_address, user_agent,
                country, city, region, geo_provider, is_spam, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
            """,
            (
                submission_id,
                widget_id,
                tenant_id,
                json.dumps(payload.data),
                client_ip,
                user_agent,
                geo_info.get("country", "Unknown"),
                geo_info.get("city", "Unknown"),
                geo_info.get("region", "Unknown"),
                geo_info.get("geo_provider", "none"),
                now,
            ),
        )
        conn.commit()

        # Fetch tenant email for notification
        tenant_row = conn.execute("SELECT email FROM tenants WHERE id = ?", (tenant_id,)).fetchone()
        tenant_email = tenant_row["email"] if tenant_row else "owner@example.com"

    # 6. Safe Side Effects (Probe 5)
    # Failure in the notification subsystem MUST NEVER fail or abort the submission!
    notification_service.dispatch_lead_notification(
        submission_id=submission_id,
        widget_title=widget_row["title"],
        lead_data=payload.data,
        tenant_email=tenant_email,
    )

    return PublicSubmissionResponse(
        status="success",
        submission_id=submission_id,
        message="Thank you! Your submission has been securely recorded.",
        geo=geo_info,
    )


# =====================================================================
# Tenant Authentication & Account Management
# =====================================================================

@app.post("/api/v1/auth/register", status_code=status.HTTP_201_CREATED, response_model=TokenResponse, tags=["Auth"])
def register_tenant(payload: TenantRegisterRequest) -> TokenResponse:
    """Register a new customer tenant account."""
    with get_db() as conn:
        existing = conn.execute("SELECT id FROM tenants WHERE email = ?", (payload.email,)).fetchone()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"An account with email '{payload.email}' already exists.",
            )

        tenant_id = f"tnt_{uuid.uuid4().hex[:12]}"
        pwd_hash = hash_password(payload.password)
        now = utc_now_iso()

        conn.execute(
            "INSERT INTO tenants (id, name, email, password_hash, created_at) VALUES (?, ?, ?, ?, ?)",
            (tenant_id, payload.name, payload.email, pwd_hash, now),
        )
        conn.commit()

    token = create_access_token(tenant_id=tenant_id, email=payload.email)
    return TokenResponse(
        access_token=token,
        tenant_id=tenant_id,
        name=payload.name,
        email=payload.email,
    )


@app.post("/api/v1/auth/login", response_model=TokenResponse, tags=["Auth"])
def login_tenant(payload: TenantLoginRequest) -> TokenResponse:
    """Authenticate tenant credentials and issue signed JWT."""
    with get_db() as conn:
        row = conn.execute("SELECT id, name, email, password_hash FROM tenants WHERE email = ?", (payload.email,)).fetchone()
        if not row or not verify_password(payload.password, row["password_hash"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        token = create_access_token(tenant_id=row["id"], email=row["email"])
        return TokenResponse(
            access_token=token,
            tenant_id=row["id"],
            name=row["name"],
            email=row["email"],
        )


@app.get("/api/v1/auth/me", tags=["Auth"])
def get_current_tenant_profile(tenant: Dict[str, Any] = Depends(get_current_tenant)) -> Dict[str, Any]:
    """Retrieve logged-in tenant profile."""
    return {"tenant": tenant}


# =====================================================================
# Authenticated Widget Management (Multi-Tenant Isolation)
# =====================================================================

@app.post("/api/v1/widgets", status_code=status.HTTP_201_CREATED, tags=["Widget Management"])
def create_widget(
    payload: WidgetCreateRequest,
    request: Request,
    tenant: Dict[str, Any] = Depends(get_current_tenant),
) -> Dict[str, Any]:
    """Create a new embeddable widget belonging strictly to the current tenant."""
    widget_id = f"wgt_{uuid.uuid4().hex[:10]}"
    now = utc_now_iso()
    fields_json = json.dumps([f.model_dump() for f in payload.form_fields])

    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO widgets (
                id, tenant_id, title, description, widget_type, button_text,
                form_fields, theme_color, is_active, allowed_domains, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?)
            """,
            (
                widget_id,
                tenant["id"],
                payload.title,
                payload.description,
                payload.widget_type,
                payload.button_text,
                fields_json,
                payload.theme_color,
                payload.allowed_domains,
                now,
                now,
            ),
        )
        conn.commit()

    base_url = str(request.base_url).rstrip("/")
    snippet = f'<script src="{base_url}/v1/widget.js?id={widget_id}" defer></script>'

    return {
        "message": "Widget created successfully.",
        "widget_id": widget_id,
        "embed_snippet": snippet,
    }


@app.get("/api/v1/widgets", tags=["Widget Management"])
def list_tenant_widgets(
    request: Request,
    tenant: Dict[str, Any] = Depends(get_current_tenant),
) -> Dict[str, Any]:
    """
    List all widgets for the authenticated tenant.
    TENANT ISOLATION: Tenant A can never view Tenant B's widgets.
    """
    base_url = str(request.base_url).rstrip("/")
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT id, title, description, widget_type, button_text, theme_color, is_active, created_at
            FROM widgets
            WHERE tenant_id = ?
            ORDER BY created_at DESC
            """,
            (tenant["id"],),
        ).fetchall()

        widgets = []
        for r in rows:
            w_dict = dict(r)
            w_dict["embed_snippet"] = f'<script src="{base_url}/v1/widget.js?id={r["id"]}" defer></script>'
            widgets.append(w_dict)

        return {"total": len(widgets), "widgets": widgets}


@app.get("/api/v1/widgets/{widget_id}", tags=["Widget Management"])
def get_widget_details(
    widget_id: str,
    request: Request,
    tenant: Dict[str, Any] = Depends(get_current_tenant),
) -> Dict[str, Any]:
    """
    Fetch single widget details.
    TENANT ISOLATION: Returns 404 if widget belongs to another tenant.
    """
    base_url = str(request.base_url).rstrip("/")
    with get_db() as conn:
        row = conn.execute(
            """
            SELECT * FROM widgets WHERE id = ? AND tenant_id = ?
            """,
            (widget_id, tenant["id"]),
        ).fetchone()

        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Widget '{widget_id}' not found in your tenant account.",
            )

        data = dict(row)
        data["form_fields"] = json.loads(data["form_fields"]) if data["form_fields"] else []
        data["embed_snippet"] = f'<script src="{base_url}/v1/widget.js?id={row["id"]}" defer></script>'
        return {"widget": data}


@app.put("/api/v1/widgets/{widget_id}", tags=["Widget Management"])
def update_widget(
    widget_id: str,
    payload: WidgetUpdateRequest,
    tenant: Dict[str, Any] = Depends(get_current_tenant),
) -> Dict[str, Any]:
    """Update widget configuration (enforcing tenant isolation)."""
    with get_db() as conn:
        existing = conn.execute(
            "SELECT id FROM widgets WHERE id = ? AND tenant_id = ?",
            (widget_id, tenant["id"]),
        ).fetchone()

        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Widget '{widget_id}' not found in your tenant account.",
            )

        updates: List[str] = []
        params: List[Any] = []

        if payload.title is not None:
            updates.append("title = ?")
            params.append(payload.title)
        if payload.description is not None:
            updates.append("description = ?")
            params.append(payload.description)
        if payload.button_text is not None:
            updates.append("button_text = ?")
            params.append(payload.button_text)
        if payload.theme_color is not None:
            updates.append("theme_color = ?")
            params.append(payload.theme_color)
        if payload.is_active is not None:
            updates.append("is_active = ?")
            params.append(1 if payload.is_active else 0)
        if payload.allowed_domains is not None:
            updates.append("allowed_domains = ?")
            params.append(payload.allowed_domains)

        if updates:
            updates.append("updated_at = ?")
            params.append(utc_now_iso())
            params.append(widget_id)
            params.append(tenant["id"])

            sql = f"UPDATE widgets SET {', '.join(updates)} WHERE id = ? AND tenant_id = ?"
            conn.execute(sql, tuple(params))
            conn.commit()

        return {"message": "Widget updated successfully.", "widget_id": widget_id}


@app.delete("/api/v1/widgets/{widget_id}", tags=["Widget Management"])
def delete_widget(
    widget_id: str,
    tenant: Dict[str, Any] = Depends(get_current_tenant),
) -> Dict[str, Any]:
    """Delete a widget and its child submissions (enforcing tenant isolation)."""
    with get_db() as conn:
        res = conn.execute(
            "DELETE FROM widgets WHERE id = ? AND tenant_id = ?",
            (widget_id, tenant["id"]),
        )
        conn.commit()
        if res.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Widget '{widget_id}' not found in your tenant account.",
            )
        return {"message": f"Widget '{widget_id}' deleted successfully."}


@app.get("/api/v1/widgets/{widget_id}/snippet", tags=["Widget Management"])
def get_widget_snippet(
    widget_id: str,
    request: Request,
    tenant: Dict[str, Any] = Depends(get_current_tenant),
) -> Dict[str, Any]:
    """Retrieve the one-line embed snippet for a customer's website."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, title FROM widgets WHERE id = ? AND tenant_id = ?",
            (widget_id, tenant["id"]),
        ).fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Widget not found.")

        base_url = str(request.base_url).rstrip("/")
        snippet = f'<script src="{base_url}/v1/widget.js?id={widget_id}" defer></script>'
        return {
            "widget_id": widget_id,
            "title": row["title"],
            "embed_snippet": snippet,
            "instructions": "Paste this one-line tag anywhere inside the <body> of your website.",
        }


# =====================================================================
# Owner Analytics Dashboard API (Aggregation Queries)
# =====================================================================

@app.get("/api/v1/dashboard/stats", tags=["Dashboard"])
def get_dashboard_stats(tenant: Dict[str, Any] = Depends(get_current_tenant)) -> Dict[str, Any]:
    """
    Aggregation analytics for the authenticated tenant:
    - Counts over time
    - Per-widget submission counts
    - Geolocation breakdown
    - Provider fallback statistics
    """
    with get_db() as conn:
        tenant_id = tenant["id"]

        # 1. Total widgets and active count
        widget_stats = conn.execute(
            """
            SELECT
                COUNT(*) AS total_widgets,
                SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) AS active_widgets
            FROM widgets WHERE tenant_id = ?
            """,
            (tenant_id,),
        ).fetchone()

        # 2. Total submissions & spam counts
        sub_stats = conn.execute(
            """
            SELECT
                COUNT(*) AS total_submissions,
                SUM(CASE WHEN is_spam = 0 THEN 1 ELSE 0 END) AS clean_leads,
                SUM(CASE WHEN is_spam = 1 THEN 1 ELSE 0 END) AS spam_blocked
            FROM submissions WHERE tenant_id = ?
            """,
            (tenant_id,),
        ).fetchone()

        # 3. Per-widget stats
        per_widget = conn.execute(
            """
            SELECT
                w.id AS widget_id,
                w.title,
                w.widget_type,
                COUNT(s.id) AS submission_count
            FROM widgets w
            LEFT JOIN submissions s ON w.id = s.widget_id AND s.is_spam = 0
            WHERE w.tenant_id = ?
            GROUP BY w.id
            ORDER BY submission_count DESC
            """,
            (tenant_id,),
        ).fetchall()

        # 4. Geolocation breakdown
        geo_breakdown = conn.execute(
            """
            SELECT country, COUNT(*) AS count
            FROM submissions
            WHERE tenant_id = ? AND is_spam = 0
            GROUP BY country
            ORDER BY count DESC
            LIMIT 10
            """,
            (tenant_id,),
        ).fetchall()

        # 5. Geo Provider distribution (Fallback analytics)
        provider_stats = conn.execute(
            """
            SELECT geo_provider, COUNT(*) AS count
            FROM submissions
            WHERE tenant_id = ? AND is_spam = 0
            GROUP BY geo_provider
            """,
            (tenant_id,),
        ).fetchall()

        return {
            "tenant": {"id": tenant["id"], "name": tenant["name"], "email": tenant["email"]},
            "summary": {
                "total_widgets": widget_stats["total_widgets"],
                "active_widgets": widget_stats["active_widgets"],
                "total_submissions": sub_stats["total_submissions"],
                "clean_leads": sub_stats["clean_leads"],
                "spam_blocked": sub_stats["spam_blocked"],
            },
            "per_widget": [dict(r) for r in per_widget],
            "geo_breakdown": [dict(r) for r in geo_breakdown],
            "geo_providers": [dict(r) for r in provider_stats],
        }


@app.get("/api/v1/dashboard/submissions", tags=["Dashboard"])
def get_dashboard_submissions(
    widget_id: Optional[str] = None,
    limit: int = 50,
    tenant: Dict[str, Any] = Depends(get_current_tenant),
) -> Dict[str, Any]:
    """Retrieve detailed submission records for tenant."""
    with get_db() as conn:
        query = """
            SELECT id, widget_id, data, ip_address, country, city, region, geo_provider, is_spam, created_at
            FROM submissions
            WHERE tenant_id = ?
        """
        params: List[Any] = [tenant["id"]]

        if widget_id:
            query += " AND widget_id = ?"
            params.append(widget_id)

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        rows = conn.execute(query, tuple(params)).fetchall()

        results = []
        for r in rows:
            d = dict(r)
            d["data"] = json.loads(d["data"]) if d["data"] else {}
            results.append(d)

        return {"total": len(results), "submissions": results}


# =====================================================================
# Deterministic Probe & Test Automation Endpoints (Section 13)
# =====================================================================

@app.post("/api/v1/admin/probes/toggle-geo", tags=["Probes"])
def toggle_geo_providers(provider_a: Optional[bool] = None, provider_b: Optional[bool] = None) -> Dict[str, Any]:
    """Toggle geolocation providers for Probe 4 fallback testing."""
    if provider_a is not None:
        geo_service.set_provider_a(provider_a)
    if provider_b is not None:
        geo_service.set_provider_b(provider_b)
    return {
        "provider_a_enabled": geo_service.provider_a_enabled,
        "provider_b_enabled": geo_service.provider_b_enabled,
    }


@app.post("/api/v1/admin/probes/toggle-side-effect", tags=["Probes"])
def toggle_side_effect_failure(force_failure: bool) -> Dict[str, Any]:
    """Toggle simulated side effect failure for Probe 5 testing."""
    notification_service.set_force_failure(force_failure)
    return {"force_failure_mode": notification_service.force_failure}


@app.post("/api/v1/admin/probes/reset-rate-limit", tags=["Probes"])
def reset_rate_limiter() -> Dict[str, Any]:
    """Reset rate limiter state for deterministic probe testing."""
    limiter.reset()
    return {"message": "Rate limiter history reset successfully."}


@app.get("/", tags=["System"])
def root_status(request: Request) -> Dict[str, Any]:
    """Platform health check and index."""
    base_url = str(request.base_url).rstrip("/")
    return {
        "service": "FlyRank Embeddable Widget & Lead-Capture Platform",
        "status": "operational",
        "version": "1.0.0",
        "endpoints": {
            "widget_bundle": f"{base_url}/v1/widget.js",
            "widget_config": f"{base_url}/api/v1/widgets/{{widget_id}}/config",
            "public_submit": f"{base_url}/api/v1/widgets/{{widget_id}}/submit",
            "dashboard_stats": f"{base_url}/api/v1/dashboard/stats",
            "api_docs": f"{base_url}/docs",
        },
    }
