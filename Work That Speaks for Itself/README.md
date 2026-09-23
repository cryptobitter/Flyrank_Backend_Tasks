# Work That Speaks for Itself · Week 2 Deliverable

> **Track**: FlyRank AI Internship — Week 02  
> **Topic**: Frame Your Work as Cases  
> **Reference**: [FlyRank Curriculum — Week 2](https://aifluency.flyrank.ai/week-02.html#frame-it-as-cases)

---

## 1. Voice Card

> **Voice Card**: `Direct, warm, plain, specific, no buzzwords.`

### Standing Instructions for AI Workspace:
```text
Here is my voice card. Use it for everything you draft for me: direct, warm, plain, specific, no buzzwords. Short sentences. No "passionate," "results-driven," "leveraged," or "dynamic." A few words that are mine: clear, modular, grounded. If a line sounds like a generic corporate AI bio, rewrite it the way an engineer would explain their build to a teammate over coffee.
```

---

## 2. Framed Case Studies (The Three Beats)

### Case Study 1: Note-Taking Microservice with PostgreSQL & Repository Pattern
*Project Source: `assignment_2`*

* **The Problem**:  
  When backend APIs scale or shift databases, mixing raw SQL queries into route handlers makes code fragile, breaks testability, and slows down feature development. I needed to build a clean CRUD service where data access is completely isolated from HTTP delivery.

* **What I Did & Decided**:  
  I built a containerized Python backend backed by PostgreSQL. Instead of coupling routes directly to database cursors, I implemented a strict Repository Pattern (`PostgresRepository`). The database connection, query execution, and object serialization are confined to data layer methods (`create_note`, `get_notes`, `delete_note`), while `routes.py` and `service.py` remain completely agnostic of database implementation details. I also containerized the setup using Docker Compose to ensure deterministic local environments.

* **What Came of It**:  
  Route handlers became five-line functions that do not care whether data lives in Postgres, SQLite, or an in-memory mock during tests. What I would do differently next time is add schema migration tooling (like Alembic) rather than relying on a static `init.sql`, so database schema evolutions can be safely tracked and rolled back.

---

### Case Study 2: Core Service Health & Routing Container
*Project Source: `Assignment_1`*

* **The Problem**:  
  In distributed environments, services can silently fail or get stuck in deadlock loops while still appearing to run. Without explicit, lightweight health probes, orchestrators cannot detect when an instance needs to be restarted or taken out of rotation.

* **What I Did & Decided**:  
  I wrote a minimal, dependency-conscious Flask service with dedicated status endpoints (`/` and `/health`). I deliberately kept third-party dependencies down to fewer than ten essential packages to keep container spin-up times fast and reduce the attack surface.

* **What Came of It**:  
  A predictable baseline service that boots in milliseconds and provides verifiable heartbeat responses for uptime monitors. What I would do differently next time is make the `/health` endpoint execute a shallow ping to downstream resources (like database sockets) so it reports real dependency health rather than just process liveliness.

---

## 3. Bio & Contact / CTA Copy

### Bio
> I build modular, containerized Python backends and database architectures that stay maintainable as products scale. I help early-stage technical teams move fast without building up unmanageable technical debt.

### Contact / CTA Copy
> Ready to review clean code instead of reading bullet points? **Book a 15-minute technical walkthrough call on my calendar**, and we will inspect the architecture together.

---

## 4. Before & After: Generic AI vs. Edited Human Voice

| Generic AI Output (The Trap) | Edited Version (Voice Card Applied) | Why the Edit Matters |
| :--- | :--- | :--- |
| *I am a passionate, results-driven software engineer dedicated to architecting scalable, cutting-edge backend solutions. Leveraging modern full-stack paradigms and synergistic database technologies, I empower enterprise stakeholders to unlock operational velocity and seamless user journeys.* | *I build modular, containerized Python backends with clean repository patterns. I focus on writing maintainable database queries and decoupled routes so small teams can ship quickly without breaking production.* | The generic line is bloated corporate buzzwords with zero verifiable facts. The edited version names the exact layer (Python backends, repository pattern, SQL queries) and states what problem it actually solves. |
| *Successfully spearheaded the implementation of an innovative containerized note storage microservice utilizing PostgreSQL paradigms to optimize data retention workflows.* | *I built a containerized note-taking service using PostgreSQL and Docker, separating all database operations into a standalone repository class so endpoints stay simple.* | Cuts empty buzzwords (spearheaded, innovative, paradigms) in favor of concrete architectural decisions. |

---

## 5. Pass / Revise Verification Checklist

- [x] **Framed case exists for each piece**: Both Assignment 1 and Assignment 2 are documented as real, working case studies.
- [x] **Three beats in every case**: Each project clearly details (1) The Problem, (2) What I Did & Decided, and (3) What Came of It (including what I would do differently).
- [x] **Distinct personal voice**: Strictly avoids results-driven, passionate, and spearheaded filler.
- [x] **Before & After included**: Side-by-side comparison illustrating generic AI sludge vs. tight, authentic engineering copy.
- [x] **Points to the one audience and one action**: Speaks directly to Engineering Leads / Founders and links straight to the 15-minute technical walkthrough call.
