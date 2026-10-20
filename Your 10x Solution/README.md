# SentinelAI: Autonomous Incident Commander & Post-Mortem Platform

**Capstone:** Your 10x Solution  
**Author:** Aditya Rajput  
**Framework Track:** FlyRank AI Engineering Internship (Fall 2026)  
**Repository:** [https://github.com/cryptobitter/Flyrank_Backend_Tasks](https://github.com/cryptobitter/Flyrank_Backend_Tasks)  
**Submission Document:** [`My 10x Solution - Aditya Rajput.md`](./My%2010x%20Solution%20-%20Aditya%20Rajput.md)  

---

## 🚀 Overview

SentinelAI is a production-grade Site Reliability Engineering (SRE) incident commander that autonomously triages infrastructure alerts, executes asynchronous diagnostic tasks, and generates executive-ready post-mortem PDF documents.

It implements **8 core backend concepts** from the FlyRank curriculum:
1. **API Endpoints** (FastAPI with OpenAPI / Swagger)
2. **Relational Database** (SQLAlchemy ORM + SQLite)
3. **Authentication & RBAC** (JWT Bearer tokens + salted PBKDF2 password hashing)
4. **LLM Integration** (AI Incident Commander root-cause analysis with strict Pydantic schemas)
5. **Background & Cron Jobs** (Async worker queue with exponential backoff & periodic monitoring)
6. **Reporting** (Automated ReportLab PDF post-mortem compilation)
7. **Caching & Idempotency** (In-memory TTL cache & atomic alert deduplication store)
8. **Webhooks** (Cryptographically signed HMAC-SHA256 alert dispatch)

---

## ⚡ Quickstart

### 1. Install Dependencies
```bash
cd "Your 10x Solution"
pip install -r requirements.txt
```

### 2. Run the Verification Test Suite
```bash
python -m pytest test_10x_solution.py -v
```

### 3. Run the Interactive 7-Scenario Demonstration
```bash
python demo_10x_solution.py
```

### 4. Start the Application & Web Dashboard
```bash
python -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```
- **Interactive Web Dashboard**: [http://localhost:8000](http://localhost:8000)
- **Interactive Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 📁 Project Structure

```
Your 10x Solution/
├── My 10x Solution - Aditya Rajput.md # Official submission document for the portal
├── README.md                          # Technical overview & quickstart guide
├── requirements.txt                   # Dependency definitions
├── .env.example                       # Environment configuration template
├── .gitignore                         # Git exclusion rules
├── config.py                          # Global application settings & paths
├── database.py                        # SQLAlchemy engine & session factory
├── models.py                          # Relational DB models (User, Incident, PostMortem, AuditLog)
├── schemas.py                         # Pydantic v2 data contracts
├── auth.py                            # PBKDF2 hashing, JWT generation, route guards
├── ai_commander.py                    # LLM Incident Commander with heuristic fallback
├── background_worker.py               # Async worker queue, backoff retries, cron pulse
├── cache.py                           # TTL Cache & Idempotency Key store
├── pdf_generator.py                   # ReportLab executive PDF post-mortem compiler
├── webhook_notifier.py                # Cryptographic HMAC-SHA256 webhook dispatcher
├── app.py                             # FastAPI main app with endpoints & dashboard UI
├── demo_10x_solution.py               # Interactive CLI demonstration
└── test_10x_solution.py               # 6 comprehensive pytest tests
```
