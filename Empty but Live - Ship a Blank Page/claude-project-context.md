# Claude Project / AI Workspace Master Context Bundle
**Loaded for Week 05 Build (`Ship the Ugly Version`)**

> **Purpose:** This file consolidates the **Visual Identity Kit** (Week 03), **Content & CTA Map** (Week 03), **Curated Image Manifest** (Week 03), and **Framed Case Studies + Voice Card** (Week 02 & Week 03/04 backend deliverables) into a single system context document loaded into the Claude Project so every generated page in Week 05 inherits the exact same fonts, hex codes, voice, structure, and proof.

---

## 1. Visual Identity Kit & Two-Line Style Note (`Decide Once`)

### Two-Line Style Note (System Prompt Lock)
> **Line 1 (Specs):** Set all headings in `Inter` (`700`/`600`) and body copy in `Inter` (`400`) on a `#F8FAFC` background with `#0F172A` text, pairing `JetBrains Mono` (`400`/`500`) inside `#1E293B` containers with `#0D9488` as the single interactive and metric accent.
> **Line 2 (Mood):** Maintain a quiet, high-contrast engineering specification mood that frames terminal benchmarks, SQL query plans, and clean Python diffs without competing for attention.

### Locked CSS Custom Properties
```css
:root {
  --bg-canvas: #F8FAFC;      /* Alabaster Slate — page background */
  --text-ink: #0F172A;       /* Deep Slate Ink — 17.4:1 contrast on #F8FAFC */
  --surface-slate: #1E293B;  /* Engineered Slate — code/terminal cards */
  --accent-teal: #0D9488;    /* Precision Teal — CTAs, status badges, metric callouts */
  --border-subtle: #CBD5E1;  /* Hairline dividers */
  --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
  --font-mono: 'JetBrains Mono', monospace;
}
```

### Brand Mark / Monogram (`favicon.svg` & `logo.svg`)
- Rounded slate square (`#1E293B`) with a `2.5px` `#0D9488` border containing the terminal prompt `>_` (`>` in `#F8FAFC`, `_` in `#0D9488`).

---

## 2. One-Line Claim & 3-Page Content + CTA Map (`The Through-Line`)

### Target Visitor & Single Action (from Week 01)
- **Target Visitor:** An Engineering Lead or Technical Founder at an early-stage B2B SaaS startup hiring a backend-focused intern or junior engineer.
- **The One Action (Primary CTA):** Book a 15-minute technical walkthrough call on my calendar.
- **The One-Line Claim:**
  > **"I build containerized Python backends where routes stay five lines long and data survives any restart."**

### 3-Page Ordered Section & CTA Map

#### Page 1: `Home / Proof Index` (`index.html`)
1. **Section 1.1 — Hero & One-Line Claim:** Monogram `>_`, headline claim, subhead naming stack (`Python`, `FastAPI`, `PostgreSQL`, `SQLite`, `Redis`, `Supabase JWT`, `Docker Compose`), primary CTA button (`#0D9488`).
2. **Section 1.2 — Lead Case Study Spotlight (Case 1: `A3 Containerize Your Stack`):** Side-by-side diff showing zero route/service changes during the `InMemoryTaskRepository` → `PostgresTaskRepository` swap + `EXPLAIN ANALYZE` (`2.410 ms` → `0.089 ms`).
3. **Section 1.3 — Supporting Case Study Grid (Cases 2 & 3):**
   - **Case 2 (`W3-A2`):** Persistent SQLite Repository & `11/11` `pytest` contract suite.
   - **Case 3 (`Auth - Login & Protect` + `The Prompt Ladder`):** Supabase JWT `HTTPBearer` route protection & 6-stage prompt engineering verification.
4. **Section 1.4 — Footer Conversion Banner:** Restates proof statement and presents the single primary CTA: **"Book a 15-Minute Technical Walkthrough →"**.

#### Page 2: `Case Studies / Deep-Dive Proof` (`cases.html`)
1. **Section 2.1 — Case Study Header & Quick-Jump Index:** Jump links in `JetBrains Mono` to Case 1 (`#a3-docker-postgres`), Case 2 (`#w3-a2-sqlite`), and Case 3 (`#auth-and-prompt-ladder`).
2. **Section 2.2 — Case 1 Full Breakdown (`A3 Containerize Your Stack`):** Three-Beat narrative + real `EXPLAIN ANALYZE` capture + Docker persistence transcript.
3. **Section 2.3 — Case 2 Full Breakdown (`W3-A2 Persistent SQLite CRUD API`):** Three-Beat narrative + real DB Browser (`tasks.db`) screenshot + atomic transaction rollback test.
4. **Section 2.4 — Case 3 Full Breakdown (`Auth - Login & Protect` & `Prompt Ladder`):** Three-Beat narrative + Swagger UI `HTTPBearer` lock flow (`401` vs `200`) + 6-stage regression table.
5. **Section 2.5 — Bottom Technical CTA:** **"Want to see these containers run live? Book a 15-Minute Technical Walkthrough →"**.

#### Page 3: `Architecture & Contact` (`about.html`)
1. **Section 3.1 — Engineering Philosophy ("Why My Routes Stay 5 Lines Long"):** Direct explanation of Routes → Service → Repository separation and AI-assisted code verification (`Stage 6/7 AI vs. Me`).
2. **Section 3.2 — Verified Technical Stack Matrix:** Clean table mapping every claim to a live folder in `cryptobitter/Flyrank_Backend_Tasks`.
3. **Section 3.3 — Direct Calendar & Contact Block:** Primary CTA button + direct email/GitHub fallback links.

---

## 3. Framed Case Studies (The Three Beats) & Voice Card (`Work That Speaks for Itself`)

### Voice Card Rules
- **Tone:** Direct, technical, evidence-first. Sounds like a calm pull-request description written for a busy senior engineer.
- **Rule 1:** Start with the constraint or failure mode, never "In this assignment I learned..."
- **Rule 2:** Name exact files, status codes (`201`, `401`, `404`), and latency numbers (`0.089 ms`).
- **Rule 3:** Banned words: *passionate, synergy, cutting-edge, revolutionary, seamless, thrilled, journey, delve*.

### Case Study 1 (Lead): Zero-Rewrite Storage Swap & Containerized Stack (`A3 Containerize your stack`)
- **Beat 1 (The Problem):** Prototype APIs break on container restart when state lives in memory, and tightly coupled SQL inside route handlers forces a full rewrite when migrating to PostgreSQL.
- **Beat 2 (The Decision):** Isolated all persistence behind a strict repository contract (`PostgresTaskRepository`), orchestrated `FastAPI` + `PostgreSQL 16` + `Redis 7` in `docker-compose.yml` with a named volume (`pgdata`) and `init.sql`, and added a composite B-tree index `idx_tasks_status_created_at`.
- **Beat 3 (The Proof):** Swapped the in-memory store for PostgreSQL while modifying **0 lines** in `routes.py` or `service.py`. Verified row survival across `docker compose restart` and reduced filtered query latency on a 10,000-row table from **`2.410 ms` (Seq Scan) to `0.089 ms` (Bitmap Index Scan — 27x speedup)**.

### Case Study 2: Persistent SQLite Repository & Atomic Transactions (`W3-A2`)
- **Beat 1 (The Problem):** Ad-hoc SQLite scripts leak connections on validation errors, allow invalid status strings into disk storage, and leave partial writes behind when a batch operation fails mid-way.
- **Beat 2 (The Decision):** Built `SQLiteTaskRepository` using context-managed transactions (`with self._get_connection() as conn:`), parameterized SQL (`?` placeholders) with SQLite `CHECK` constraints, and database-level `COUNT(*)` aggregation.
- **Beat 3 (The Proof):** Passed **`11/11` automated `pytest` contract and persistence tests** (`test_api.py`), including a simulated mid-transaction crash that proved zero partial writes hit `tasks.db`.

### Case Study 3: Stateless JWT Route Protection & Systematic Prompt Engineering (`Auth - Login & protect` & `The Prompt Ladder`)
- **Beat 1 (The Problem):** Open CRUD endpoints expose user data to anyone with the URL, while naive AI-generated auth middleware often leaks raw Upstream IdP exceptions as `500 Internal Server Error` or fails to render the `Authorize` modal in Swagger UI.
- **Beat 2 (The Decision):** Implemented a reusable `HTTPBearer` FastAPI dependency (`get_current_user` in `auth_middleware.py`) validating Bearer JWTs against Supabase Auth, paired with a 6-stage constrained prompt engineering rubric that enforces explicit HTTP error contracts.
- **Beat 3 (The Proof):** Protected `/protected/profile` and `/protected/dashboard` with verified `401 Unauthorized` responses for missing/tampered tokens, `200 OK` identity extraction for valid JWTs, and **`8/8` passing security tests** (`test_auth.py`).

---

## 4. Curated Image Manifest (`Kill Your Darlings`)

- **Real Work Captures (`keepers/real-work/`):**
  1. `case1-postgres-explain-analyze.png` — PostgreSQL 16 `EXPLAIN ANALYZE` terminal output (`2.410 ms` → `0.089 ms`).
  2. `case1-zero-diff-architecture.png` — Side-by-side `main.py` dependency swap (`routes.py: 0 lines changed`).
  3. `case2-sqlite-db-browser.png` — DB Browser for SQLite capture of `tasks.db` with `idx_tasks_status`.
- **Connective Tissue Icons (`keepers/connective-tissue/`):**
  - `icon-layers-architecture.svg`, `icon-container-persistence.svg`, `icon-prompt-verification.svg` (`2px` stroke in `#F8FAFC` + `#0D9488` on `#1E293B`).
