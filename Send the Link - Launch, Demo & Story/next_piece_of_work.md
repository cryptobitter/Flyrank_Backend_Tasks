# The Named Next Piece of Work

**Author:** Aditya Rajput  
**Target Completion Date:** November 15, 2026  
**Project Title:** **Distributed LLM Token Rate Limiter & Cost Metering Proxy**  
**Repository (Pre-allocated):** `https://github.com/cryptobitter/llm-rate-limiter-proxy`  

---

## 1. Project Profile

- **Core Domain:** High-Throughput AI Infrastructure & Cloud FinOps
- **Technologies:** Python 3.12 / Rust, Redis (Sliding Window Log & Token Bucket), FastAPI, Pydantic v2, Prometheus, Grafana, Docker.
- **Why It Matters:**  
  In Week 6 (`Connect To an API`) and Week 8 (`Your first background job`), we built endpoints that query LLMs. However, in multi-tenant environments, a single rogue client script or infinite agent loop can burn through thousands of dollars in OpenAI/Groq API tokens within minutes or trigger hard upstream 429 errors for all users. Current solutions either rate-limit naively by HTTP request count (which fails because one prompt can consume 50 tokens while another consumes 4,000) or force vendor lock-in.

---

## 2. The Three-Beat Draft for the Case Study

### Beat 1: The Problem
Naively rate-limiting AI endpoints by HTTP requests per minute fails to protect cloud budgets because token consumption varies wildly between a 20-token ping and a 4,000-token multi-doc prompt. When automated workflows retry aggressively, teams experience catastrophic monthly bill shocks and cascading 429 quota exhaustion that halts entire production pipelines.

### Beat 2: What I Built
A lightweight, reverse-proxy gateway that sits between client applications and LLM providers (Groq, OpenAI, Anthropic). It implements a **Redis-backed token-bucket algorithm** that meters estimated prompt tokens on ingress and reconciles actual completion tokens on egress via streaming HTTP response parsing. It enforces tenant-level dollar and token budgets with soft-warning webhooks at 80% quota and hard circuit-breaker rejections at 100%, without adding more than 4ms of network overhead.

### Beat 3: What Came of It
- Benchmarked at **4,500 concurrent requests/sec** with sub-3.5ms proxy latency overhead.
- Completely prevented budget overruns across a simulated 20-tenant chaos test, throttling 100% of rogue token spikes while allowing standard operational traffic to proceed uninterrupted.
- Full real-time observability exported to Prometheus and visualized on a pre-built Grafana dashboard.

---

## 3. Milestones to Completion

| Milestone | Target Date | Deliverable |
| :--- | :--- | :--- |
| **M1: Core Proxy & Redis Token Bucket** | Oct 28, 2026 | Working reverse proxy intercepting OpenAI & Groq SDK calls with Redis sliding window. |
| **M2: Streaming Egress Token Reconciliation** | Nov 04, 2026 | Real-time byte-stream parsing to capture exact token usage without buffering delays. |
| **M3: Chaos & Stress Benchmarks** | Nov 10, 2026 | Fuzzing with Locust/k6 to prove sub-4ms overhead and 100% budget circuit breaking. |
| **M4: Deploy, Document & Ship to Portfolio** | Nov 15, 2026 | Live card and deep-dive case study added to `adityarajput.netlify.app`. |
