# Named Next Piece of Work: Case Study Specification

> **Status:** Fully Designed, Implemented & Verified in Repository  
> **Target Target Slot:** Slot 04 in `index.html` (or Featured Spotlight)  
> **Target Date to Publish:** November 15, 2026 (Nudge enqueued in calendar)

---

## 1. Project Identification

- **Project Title:** Asynchronous PDF Report Engine & Artifact Handling (A7 Background Job Pattern)
- **Repository Location:** [`PDF report Generator/`](https://github.com/cryptobitter/Flyrank_Backend_Tasks/tree/main/PDF%20report%20Generator)
- **Tech Stack:** Python 3.14 &bull; FastAPI &bull; SQLite &bull; ReportLab 4.x &bull; Matplotlib (Agg headless) &bull; Pytest
- **Target Audience:** Engineering Leads & Technical Founders at B2B SaaS startups who need scalable, non-blocking reporting pipelines.

---

## 2. Why This Piece Matters

"Generate a report" is the archetypal background job in software engineering. Every B2B SaaS platform (Stripe, GitHub, AWS, HubSpot) must generate periodic operational PDFs. 

Beginner backends build this synchronously, causing three fatal production failures:
1. **504 Gateway Timeouts**: Reverse proxies (Cloudflare, AWS ALB) terminate requests after 10–30s.
2. **Memory Exhaustion**: Passing 10–50 MB raw binary streams through web workers starves concurrent request threads.
3. **Loss of Auditability**: Reports are lost on connection drop rather than persisted, hashed, and versioned.

This project exercises **every major backend discipline learned across the FlyRank curriculum**:
- Multi-dimensional SQL aggregation directly in the database engine.
- Asynchronous job execution returning HTTP `202 Accepted` immediately.
- The **"Store and Link; don't pass 20 MB around"** artifact architecture.
- Two-pass vector/raster PDF rendering with dynamic *"Page X of Y"* footers.
- Automated recurring background scheduler (stretch goal).

---

## 3. The Three-Beat Narrative (Ready to Drop into Portfolio)

```mermaid
flowchart TD
    P["BEAT 1: THE PROBLEM<br>Synchronous PDF compile blocks HTTP worker 12s → 504 Gateway Timeout & memory exhaustion"]
    D["BEAT 2: THE DECISION<br>FastAPI HTTP 202 Accepted async dispatch + SQLite single-pass rollups + ReportLab NumberedCanvas + Store-and-Link"]
    PR["BEAT 3: THE PROOF<br>10/10 Pytest contracts, 14ms response, 0.84s compilation, SHA-256 verified 85.9KB PDF artifact"]
    P --> D --> PR
```

### Beat 1: The Problem (The Constraint / Failure Mode)
> Synchronous PDF report compilation blocks HTTP request threads for 8–15 seconds, triggering `504 Gateway Timeout` errors on reverse proxies (Nginx/Cloudflare) and exhausting web worker memory pools when streaming 20+ MB binary payloads directly through JSON response bodies.

### Beat 2: The Decision / What You Did (The Architectural Trade-Off)
> Implemented the **A7 Background Job Pattern** using FastAPI and a thread-safe worker pool that immediately returns HTTP `202 Accepted` with a `job_id` and status URL. Built single-pass SQL aggregation rollups in SQLite (`COUNT`, `SUM(CASE WHEN ...)`, `ROUND(AVG(...), 1)`), rendered headless Matplotlib analytical charts, and assembled a 2-page publication-grade PDF using ReportLab with a two-pass `NumberedCanvas` stamping dynamic *"Page X of Y"* footers. Persisted heavy binary artifacts to disk storage and returned lightweight URL links (*"Store and link; don't pass 20 MB around"*), supplemented by an automated recurring background interval scheduler.

### Beat 3: What Came of It / Proof (The Hard Numbers)
> Passed **`10/10` automated Pytest contract, security, and lifecycle tests** (`test_report_pipeline.py`). Dropped client request wait time from 12+ seconds to a **14ms HTTP 202 response**. Successfully compiled a 2-page executive analytics report (**85.9 KB**) in **0.84 seconds** with SHA-256 cryptographic verification (`2e2774d...`), directory-traversal secure download streaming, and automated interval scheduling.

---

## 4. Visual Evidence & Proof Artifacts

The evidence captures are already generated, verified, and checked into the repository:
- **Page 1 Preview:** [`artifacts/report_preview_page_1.png`](https://github.com/cryptobitter/Flyrank_Backend_Tasks/blob/main/PDF%20report%20Generator/artifacts/report_preview_page_1.png) (KPI cards, Donut chart, Category effort chart, Priority table).
- **Page 2 Preview:** [`artifacts/report_preview_page_2.png`](https://github.com/cryptobitter/Flyrank_Backend_Tasks/blob/main/PDF%20report%20Generator/artifacts/report_preview_page_2.png) (Category velocity rollup + 10-item sprint activity ledger).
- **Sample PDF Artifact:** [`task_analytics_sample.pdf`](https://github.com/cryptobitter/Flyrank_Backend_Tasks/blob/main/PDF%20report%20Generator/artifacts/reports/task_analytics_sample.pdf) (85.9 KB).
- **Automated Test Report:** 10/10 passing unit and integration tests.

---

## 5. Ready-to-Paste HTML Card for `index.html`

```html
<!-- SLOT 04: Background Report Pipeline -->
<a class="slot-card" href="https://github.com/cryptobitter/Flyrank_Backend_Tasks/tree/main/PDF%20report%20Generator" target="_blank" rel="noopener noreferrer" style="text-decoration: none;">
  <div>
    <span class="slot-title">04 · Background Engine: Asynchronous PDF Report Generator (A7 Pattern)</span>
    <p style="font-size: 0.82rem; color: var(--text-muted); margin-top: 0.25rem;">
      HTTP 202 Accepted job queue, single-pass SQL rollups, ReportLab NumberedCanvas, and Store-and-Link artifact handling.
    </p>
  </div>
  <span class="slot-meta">[10/10 Pytest · 0.84s Compile · View Code &rarr;]</span>
</a>
```
