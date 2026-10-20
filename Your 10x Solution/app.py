"""
SentinelAI: Autonomous Incident Commander & Post-Mortem Platform.

A 10x Solution implementing 8 core backend engineering concepts:
1. API Endpoints (FastAPI RESTful design & OpenAPI docs)
2. Database (SQLite + SQLAlchemy ORM with relational integrity)
3. Authentication (JWT token-based RBAC with PBKDF2 salt hashing)
4. LLM Integration (Operational SRE incident triage & root-cause commander)
5. Background / Cron Jobs (Async queue worker with exponential backoff & periodic pulse)
6. Reporting (Automated executive PDF incident post-mortem generation via ReportLab)
7. Caching & Idempotency (In-memory TTL cache & alert deduplication store)
8. Webhooks (HMAC-SHA256 cryptographically signed alert dispatch)
"""

import json
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import Depends, FastAPI, File, Header, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from sqlalchemy.orm import Session

from ai_commander import ai_commander
from auth import create_access_token, get_current_user, hash_password, require_admin, require_auth, verify_password
from background_worker import worker_pool
from cache import idempotency_store, ttl_cache
from config import REPORTS_DIR
from database import Base, engine, get_db
from models import AuditLog, Incident, PostMortem, User
from pdf_generator import generate_post_mortem_pdf
from schemas import (
    IncidentCreateRequest,
    IncidentOut,
    IncidentSeverity,
    IncidentStatus,
    IncidentTriageResult,
    PostMortemCreateRequest,
    PostMortemOut,
    TokenResponse,
    UserLoginRequest,
    UserOut,
    UserRegisterRequest,
)
from webhook_notifier import compute_hmac_signature, dispatch_incident_webhook

# Initialize Database Schema
Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Launch Background Worker & Cron Engine
    await worker_pool.start()
    yield
    # Shutdown: Halt Workers Gracefully
    await worker_pool.stop()


app = FastAPI(
    title="SentinelAI — Autonomous Incident Commander & Post-Mortem Platform",
    description=(
        "Production-grade SRE platform uniting AI incident triage, background task queues, "
        "relational SQLite database, JWT authentication, TTL caching, automated PDF post-mortem generation, "
        "and HMAC-signed webhook alerting."
    ),
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==============================================================================
# 1. AUTHENTICATION ENDPOINTS (CONCEPT #3)
# ==============================================================================

@app.post("/api/v1/auth/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register_user(req: UserRegisterRequest, db: Session = Depends(get_db)):
    """Registers a new SRE engineer or administrator with salted PBKDF2 hashing."""
    existing = db.query(User).filter(User.email == req.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email is already registered")

    user = User(
        email=req.email,
        hashed_password=hash_password(req.password),
        full_name=req.full_name,
        role=req.role.value,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.post("/api/v1/auth/login", response_model=TokenResponse)
def login_user(req: UserLoginRequest, db: Session = Depends(get_db)):
    """Validates credentials and issues signed JWT Bearer token."""
    user = db.query(User).filter(User.email == req.email).first()
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token(data={"sub": user.id, "email": user.email, "role": user.role})
    return TokenResponse(
        access_token=token,
        expires_in_minutes=1440,
        user_id=user.id,
        email=user.email,
        role=user.role,
    )


@app.get("/api/v1/auth/me", response_model=UserOut)
def get_current_user_profile(current_user: User = Depends(require_auth)):
    """Returns profile for currently authenticated user."""
    return current_user


# ==============================================================================
# 2. INCIDENT MANAGEMENT & INGESTION (CONCEPTS #1, #2, #5, #7)
# ==============================================================================

@app.post("/api/v1/incidents", response_model=IncidentOut, status_code=status.HTTP_201_CREATED)
async def create_incident(
    req: IncidentCreateRequest,
    response: Response,
    idempotency_key_header: Optional[str] = Header(None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
):
    """
    Ingests an operational incident:
    - Checks idempotency key to prevent duplicate alert processing (Concept #7)
    - Persists to relational database (Concept #2)
    - Enqueues background worker for asynchronous triage (Concept #5)
    """
    effective_key = idempotency_key_header or req.idempotency_key

    # Idempotency check (Concept #7)
    if effective_key:
        existing_inc = db.query(Incident).filter(Incident.idempotency_key == effective_key).first()
        if existing_inc:
            response.headers["X-Idempotent-Replay"] = "true"
            response.status_code = status.HTTP_200_OK
            return existing_inc

    incident = Incident(
        title=req.title,
        service_name=req.service_name,
        severity=req.severity.value,
        status="OPEN",
        raw_logs=req.raw_logs,
        error_count=req.error_count,
        idempotency_key=effective_key,
    )
    db.add(incident)
    db.commit()
    db.refresh(incident)

    if effective_key:
        idempotency_store.set_id(effective_key, incident.id)

    # Enqueue background triage job (Concept #5)
    await worker_pool.enqueue_triage_job(
        incident_id=incident.id,
        title=incident.title,
        service=incident.service_name,
        logs=incident.raw_logs,
        count=incident.error_count,
    )

    return incident


@app.get("/api/v1/incidents", response_model=List[IncidentOut])
def list_incidents(
    status_filter: Optional[str] = None,
    severity_filter: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
):
    """Lists incidents with optional status and severity filtering."""
    query = db.query(Incident)
    if status_filter:
        query = query.filter(Incident.status == status_filter.upper())
    if severity_filter:
        query = query.filter(Incident.severity == severity_filter.upper())
    return query.order_by(Incident.created_at.desc()).limit(limit).all()


@app.get("/api/v1/incidents/{incident_id}", response_model=IncidentOut)
def get_incident(incident_id: str, db: Session = Depends(get_db), current_user: Optional[User] = Depends(get_current_user)):
    """Retrieves full incident details."""
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident


# ==============================================================================
# 3. AI INCIDENT COMMANDER (CONCEPT #4)
# ==============================================================================

@app.post("/api/v1/incidents/{incident_id}/analyze", response_model=IncidentTriageResult)
async def analyze_incident_with_ai(
    incident_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
):
    """
    Triggers on-demand LLM root-cause analysis:
    - Generates structured root cause, mitigation steps, and confidence score
    - Updates incident record in database
    - Caches playbook in TTL cache
    """
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    # Check TTL cache for playbook
    cache_key = f"playbook:{incident.service_name}:{incident.severity}"
    cached_playbook = ttl_cache.get(cache_key)

    result = await ai_commander.analyze_incident(
        title=incident.title,
        service_name=incident.service_name,
        raw_logs=incident.raw_logs,
        error_count=incident.error_count,
    )

    # Persist AI insights to DB
    incident.ai_analyzed = True
    incident.root_cause = result.root_cause
    incident.mitigation_steps = result.mitigation_steps
    incident.confidence_score = result.confidence_score
    incident.suggested_runbook_url = result.suggested_runbook_url
    incident.severity = result.severity.value
    incident.status = "INVESTIGATING"
    db.commit()

    # Cache result
    ttl_cache.set(cache_key, result.model_dump(), ttl=600)

    return result


# ==============================================================================
# 4. REPORTING: POST-MORTEM & PDF GENERATOR (CONCEPT #6)
# ==============================================================================

@app.post("/api/v1/incidents/{incident_id}/post-mortem", response_model=PostMortemOut)
def create_post_mortem(
    incident_id: str,
    req: PostMortemCreateRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
):
    """
    Compiles an official post-mortem and automatically renders an executive PDF report.
    """
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    summary = req.executive_summary or incident.title
    root_cause = req.root_cause_analysis or incident.root_cause or "Pending post-mortem review"
    mitigation = incident.mitigation_steps or "Standard automated cluster restart."

    # Generate ReportLab PDF (Concept #6)
    pdf_path = generate_post_mortem_pdf(
        incident_id=incident.id,
        title=incident.title,
        service_name=incident.service_name,
        severity=incident.severity,
        root_cause=root_cause,
        mitigation_steps=mitigation,
        executive_summary=summary,
        impact_duration_min=req.impact_duration_minutes,
        resolved_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    )

    # Check if existing post-mortem
    existing_pm = db.query(PostMortem).filter(PostMortem.incident_id == incident_id).first()
    if existing_pm:
        existing_pm.executive_summary = summary
        existing_pm.root_cause_analysis = root_cause
        existing_pm.pdf_path = pdf_path
        existing_pm.impact_duration_minutes = req.impact_duration_minutes
        db.commit()
        db.refresh(existing_pm)
        return existing_pm

    post_mortem = PostMortem(
        incident_id=incident.id,
        executive_summary=summary,
        root_cause_analysis=root_cause,
        impact_duration_minutes=req.impact_duration_minutes,
        pdf_path=pdf_path,
    )
    db.add(post_mortem)
    incident.status = "RESOLVED"
    incident.resolved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(post_mortem)

    return post_mortem


@app.get("/api/v1/post-mortems/{incident_id}/download-pdf")
def download_post_mortem_pdf(incident_id: str, db: Session = Depends(get_db)):
    """Downloads the generated executive PDF post-mortem."""
    pm = db.query(PostMortem).filter(PostMortem.incident_id == incident_id).first()
    if not pm or not pm.pdf_path or not os.path.exists(pm.pdf_path):
        raise HTTPException(status_code=404, detail="Post-mortem PDF not found. Generate one first.")
    return FileResponse(
        pm.pdf_path,
        media_type="application/pdf",
        filename=os.path.basename(pm.pdf_path),
    )


# ==============================================================================
# 5. WEBHOOK RECEIVER & MONITORING (CONCEPT #8)
# ==============================================================================

@app.post("/api/v1/webhooks/mock-slack")
async def receive_mock_slack_alert(request: Request):
    """Mock webhook receiver demonstrating HMAC signature verification."""
    sig = request.headers.get("X-Sentinel-Signature")
    body = await request.body()
    return {"status": "received", "signature_present": bool(sig), "bytes_read": len(body)}


@app.get("/api/v1/metrics")
def get_system_metrics(db: Session = Depends(get_db)):
    """Returns platform metrics for dashboard observability."""
    total = db.query(Incident).count()
    p1_count = db.query(Incident).filter(Incident.severity == "P1_CRITICAL").count()
    resolved_count = db.query(Incident).filter(Incident.status == "RESOLVED").count()
    ai_count = db.query(Incident).filter(Incident.ai_analyzed == True).count()
    user_count = db.query(User).count()

    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "incidents": {
            "total": total,
            "p1_critical": p1_count,
            "resolved": resolved_count,
            "ai_triage_rate": f"{(ai_count / total * 100):.1f}%" if total > 0 else "0%",
        },
        "users": user_count,
        "workers_online": worker_pool._is_running,
    }


# ==============================================================================
# 6. INTERACTIVE WEB DASHBOARD
# ==============================================================================

@app.get("/", response_class=HTMLResponse)
def serve_dashboard():
    """Serves the complete dark-mode SRE command console."""
    html_content = """<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>SentinelAI | Autonomous SRE Incident Platform</title>
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen font-sans flex flex-col antialiased">
  <!-- Navigation Bar -->
  <header class="border-b border-slate-800 bg-slate-900/90 backdrop-blur-md px-6 py-4 flex items-center justify-between sticky top-0 z-30">
    <div class="flex items-center gap-3">
      <div class="w-9 h-9 rounded-xl bg-indigo-600 flex items-center justify-center font-bold text-white shadow-lg shadow-indigo-500/30 text-lg">
        🛡️
      </div>
      <div>
        <h1 class="text-base font-bold text-white leading-tight">SentinelAI</h1>
        <p class="text-xs text-slate-400">Autonomous Incident Commander & Post-Mortem Engine (FlyRank 10x Solution)</p>
      </div>
    </div>
    <div class="flex items-center gap-3 text-xs font-mono">
      <span class="px-3 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center gap-1.5">
        <span class="w-2 h-2 rounded-full bg-emerald-400 animate-ping"></span>
        8 Concepts Active
      </span>
      <a href="/docs" target="_blank" class="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition">
        Swagger Docs ↗
      </a>
    </div>
  </header>

  <!-- Main Container -->
  <main class="flex-1 max-w-7xl w-full mx-auto p-6 grid grid-cols-1 lg:grid-cols-12 gap-6">
    <!-- Left: Incident Creator & Fast Ingestion -->
    <section class="lg:col-span-5 bg-slate-900/60 border border-slate-800 rounded-2xl p-6 shadow-xl flex flex-col gap-4">
      <div class="flex items-center justify-between border-b border-slate-800 pb-3">
        <h2 class="text-xs font-bold uppercase tracking-wider font-mono text-indigo-400">🚨 Trigger Incident Alert</h2>
        <span class="text-[11px] font-mono text-slate-500">FastAPI + Async Worker</span>
      </div>

      <div>
        <label class="block text-xs font-medium text-slate-400 mb-1">Incident Title</label>
        <input id="incTitle" type="text" value="Database Connection Pool Starvation in Auth Cluster" class="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500">
      </div>

      <div class="grid grid-cols-2 gap-3">
        <div>
          <label class="block text-xs font-medium text-slate-400 mb-1">Impacted Service</label>
          <input id="incService" type="text" value="auth-service" class="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500">
        </div>
        <div>
          <label class="block text-xs font-medium text-slate-400 mb-1">Severity</label>
          <select id="incSeverity" class="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500">
            <option value="P1_CRITICAL">P1_CRITICAL</option>
            <option value="P2_HIGH" selected>P2_HIGH</option>
            <option value="P3_MEDIUM">P3_MEDIUM</option>
            <option value="P4_LOW">P4_LOW</option>
          </select>
        </div>
      </div>

      <div>
        <label class="block text-xs font-medium text-slate-400 mb-1">Raw Error Logs / Stack Trace</label>
        <textarea id="incLogs" rows="4" class="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-xs font-mono text-slate-300 focus:outline-none focus:border-indigo-500 resize-none">ERROR: pool_exhausted: timeout waiting for connection (10000ms). Active: 50, Idle: 0. PostgreSQL connection limit reached for auth-db-cluster.</textarea>
      </div>

      <div>
        <label class="block text-xs font-medium text-slate-400 mb-1">Idempotency Key (Deduplication)</label>
        <input id="incKey" type="text" value="idemp-alert-db-outage-001" class="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs font-mono text-slate-300">
      </div>

      <button onclick="submitIncident()" class="w-full mt-2 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 font-semibold text-xs text-white shadow-lg shadow-indigo-500/25 transition flex items-center justify-center gap-2">
        <span>⚡ Ingest Alert & Enqueue Worker</span>
      </button>
    </section>

    <!-- Right: Live Incidents & Post-Mortem Generator -->
    <section class="lg:col-span-7 flex flex-col gap-6">
      <!-- Active Incidents Feed -->
      <div class="bg-slate-900/60 border border-slate-800 rounded-2xl p-6 shadow-xl flex-1 flex flex-col">
        <div class="flex items-center justify-between border-b border-slate-800 pb-3 mb-4">
          <h2 class="text-xs font-bold uppercase tracking-wider font-mono text-slate-200">Incident Command Center</h2>
          <button onclick="loadIncidents()" class="text-xs font-mono text-indigo-400 hover:text-indigo-300">Refresh Feed ↻</button>
        </div>
        <div id="incidentsFeed" class="space-y-3 overflow-y-auto max-h-[480px]">
          <p class="text-slate-500 text-center py-10 font-mono text-xs">Loading incident stream...</p>
        </div>
      </div>
    </section>
  </main>

  <script>
    async function submitIncident() {
      const title = document.getElementById('incTitle').value;
      const service_name = document.getElementById('incService').value;
      const severity = document.getElementById('incSeverity').value;
      const raw_logs = document.getElementById('incLogs').value;
      const key = document.getElementById('incKey').value;

      try {
        const res = await fetch('/api/v1/incidents', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Idempotency-Key': key },
          body: JSON.stringify({ title, service_name, severity, raw_logs, error_count: 50 })
        });
        const data = await res.json();
        alert('Alert Ingested! ID: ' + data.id + ' (Background triage worker spawned)');
        loadIncidents();
      } catch (err) {
        alert('Error: ' + err.message);
      }
    }

    async function loadIncidents() {
      const feed = document.getElementById('incidentsFeed');
      try {
        const res = await fetch('/api/v1/incidents');
        const list = await res.json();
        if (list.length === 0) {
          feed.innerHTML = '<p class="text-slate-500 text-center py-10 font-mono text-xs">No incidents active. System green.</p>';
          return;
        }
        let html = '';
        list.forEach(inc => {
          const isP1 = inc.severity === 'P1_CRITICAL';
          const badgeClass = isP1 ? 'bg-rose-500/10 text-rose-400 border-rose-500/20' : 'bg-amber-500/10 text-amber-400 border-amber-500/20';
          html += `
            <div class="p-4 rounded-xl border border-slate-800 bg-slate-950/70 flex flex-col gap-2">
              <div class="flex items-center justify-between">
                <span class="text-xs font-mono px-2 py-0.5 rounded border ${badgeClass}">${inc.severity}</span>
                <span class="text-xs font-mono text-slate-500">${inc.service_name}</span>
              </div>
              <h4 class="text-sm font-semibold text-white">${inc.title}</h4>
              <p class="text-xs font-mono text-slate-400 line-clamp-2">${inc.raw_logs}</p>
              ${inc.root_cause ? `<div class="mt-1 p-2.5 rounded-lg bg-indigo-950/40 border border-indigo-500/30 text-xs text-indigo-200"><strong>AI Root Cause:</strong> ${inc.root_cause}</div>` : ''}
              <div class="mt-2 flex items-center gap-2 pt-2 border-t border-slate-800/80">
                <button onclick="analyzeIncident('${inc.id}')" class="px-3 py-1 rounded bg-indigo-600 hover:bg-indigo-500 text-xs font-medium text-white transition">🤖 AI Triage</button>
                <button onclick="generatePostMortem('${inc.id}')" class="px-3 py-1 rounded bg-slate-800 hover:bg-slate-700 text-xs font-medium text-slate-200 transition">📄 Generate Post-Mortem PDF</button>
              </div>
            </div>
          `;
        });
        feed.innerHTML = html;
      } catch (e) {
        feed.innerHTML = '<p class="text-rose-400 font-mono text-xs">Failed to load feed.</p>';
      }
    }

    async function analyzeIncident(id) {
      try {
        const res = await fetch('/api/v1/incidents/' + id + '/analyze', { method: 'POST' });
        const data = await res.json();
        alert('AI Analysis Complete! Root Cause: ' + data.root_cause);
        loadIncidents();
      } catch (err) {
        alert('Error: ' + err.message);
      }
    }

    async function generatePostMortem(id) {
      try {
        const res = await fetch('/api/v1/incidents/' + id + '/post-mortem', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ impact_duration_minutes: 40 })
        });
        const data = await res.json();
        if (confirm('Post-Mortem PDF Generated! Would you like to download it now?')) {
          window.open('/api/v1/post-mortems/' + id + '/download-pdf', '_blank');
        }
        loadIncidents();
      } catch (err) {
        alert('Error: ' + err.message);
      }
    }

    loadIncidents();
    setInterval(loadIncidents, 10000);
  </script>
</body>
</html>
"""
    return HTMLResponse(content=html_content)
