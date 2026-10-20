# Build-in-Public Showcase Post

**Assignment 8.2 Deliverable**  
**Author:** Aditya Rajput  
**Channels:** LinkedIn • X / Twitter • FlyRank Community Showcase  
**Live Demo:** [https://www.loom.com/share/aditya-rajput-flyrank-capstone-demo](https://www.loom.com/share/aditya-rajput-flyrank-capstone-demo)  
**Live Site:** [https://adityarajput.netlify.app](https://adityarajput.netlify.app)  
**Codebase:** [https://github.com/cryptobitter/Flyrank_Backend_Tasks](https://github.com/cryptobitter/Flyrank_Backend_Tasks)  

---

## 📢 The LinkedIn / Showcase Post

**"Calling an LLM is 30 lines. Making it trustworthy under real traffic is 500 lines of engineering."**

Today I officially shipped my capstone for the **FlyRank AI Engineering Internship**: an **Autonomous AI Decision & Background Triage Engine**.

Here is what I built, one real technical decision I made, and one real limitation I'm keeping honest about on camera. 👇

---

### The Problem We Hit in Week 6
In Week 6, we built an AI support triage endpoint to classify customer issues into domain, urgency, and recommended actions. It worked great on a single test prompt. 

Then we put it under concurrent traffic. The reality of LLMs hit: **blocking HTTP connections for 2.5 seconds per request kills your server.** If 50 customers hit your checkout during an outage, web worker threads exhaust, mobile clients disconnect, and you get cascading 504 timeouts.

---

### The Architecture: Accept Fast $\rightarrow$ Work in Background $\rightarrow$ Report Status
To fix this, I rebuilt the system around an asynchronous queue/worker pattern:
1. **Accept Fast**: `POST /api/v1/jobs` ingests customer inquiries, validates schemas, and returns **`HTTP 202 Accepted` in just 2.82 milliseconds** with a `Location: /api/v1/jobs/:id` header.
2. **Work in Background**: Autonomous workers pull jobs from the queue and run the inference independently.
3. **Report Status**: Clients poll `/api/v1/jobs/:id` as it transitions from `queued` $\rightarrow$ `processing` $\rightarrow$ `completed`.
4. **Visual Decision Flow Canvas**: In the frontend, support leads can visually design decision trees with **React Flow** and **Inngest**, where each node evaluates strictly to **YES** or **NO** with animated green/red flow indicators.

---

### 💡 One Key Design Decision
**Why dual engines (FastAPI Background Worker + Inngest/React Flow)?**  
We wanted sub-3ms HTTP 202 ingestion for thousands of raw incoming webhook bursts (handled effortlessly by our lightweight FastAPI queue), while simultaneously giving support leads visual step replays, individual node inspection, and durable state machines for complex multi-hop decisions (handled by Inngest and React Flow). Decoupling high-velocity ingestion from visual orchestration gave us the best of both worlds.

---

### ⚠️ One Real Limitation (Transparency Matters)
In our default development configuration, our queue lives in Python memory. If someone pulls the server power cord, pending jobs that haven't been picked up by workers will be lost. In a full production rollout, that queue must be backed by a persistent **Redis Stream** or a **PostgreSQL transactional outbox pattern** to guarantee zero job loss across hard crashes.

---

### 🏆 The 3 Non-Negotiables I'll Never Forget:
1. **Jobs will run twice (Idempotency)**: Our system uses `Idempotency-Key` headers and sha256 payload caching. If a network retry hits us, it returns the existing job in <1ms—zero duplicate LLM spend.
2. **Jobs will fail (Retries)**: Exponential backoff with full randomized jitter gives upstream model providers breathing room instead of thundering-herd retries.
3. **Someone must find out (Alerts)**: If a job exhausts all 3 retries, it moves to `DEAD_LETTER` and fires a `CRITICAL` alert to Slack and our `/api/v1/alerts` monitoring stream.

---

Huge thank you to the FlyRank engineering team and my peer reviewers for the honest critiques along the way.

Check out the 3-minute live walkthrough (no slides, pure terminal and canvas execution):  
📹 **Demo Video**: https://www.loom.com/share/aditya-rajput-flyrank-capstone-demo  
💻 **GitHub**: https://github.com/cryptobitter/Flyrank_Backend_Tasks  
🌐 **Portfolio**: https://adityarajput.netlify.app  

#SoftwareEngineering #AIEngineering #FastAPI #ReactFlow #Inngest #Python #SystemDesign #BuildInPublic #FlyRank
