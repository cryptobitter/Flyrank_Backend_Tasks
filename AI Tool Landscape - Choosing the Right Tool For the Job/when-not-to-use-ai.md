# When NOT to Use AI: Pre-Prompt Prediction & High-Stakes Failure Modes

> **The Professional Reality:** In client work and production software, a wrong fact that ships costs ten to a hundred times more than doing the task by hand. The mark of an AI-fluent practitioner is not how many tasks they throw at AI, but knowing **before typing a single word** whether the model can give a reliable answer.

---

## 1. The Pre-Prompt Prediction Test (The 4-Question Filter)

Before opening ChatGPT, Claude, or Cursor for any task, run it through this four-question diagnostic:

```
                          [ START TASK ]
                                 │
           1. Does this task require strict factual recall
              of facts NOT present in my prompt?
              ├── YES ──► STOP: Search a database/docs first or use Perplexity.
              └── NO
                   │
           2. Can an undetected subtle error cause
              financial, legal, or security liability?
              ├── YES ──► STOP: High-risk zone. Manual verification required.
              └── NO
                   │
           3. Does verifying the output take LONGER
              than writing it from scratch?
              ├── YES ──► STOP: AI is a net negative productivity sink.
              └── NO
                   │
           4. Is the task pure deterministic math / counting?
              ├── YES ──► STOP: Use Python, SQL, or Excel instead.
              └── NO
                   │
                   ▼
       [ PROCEED WITH AI: High-Leverage Opportunity ]
```

---

## 2. Ethan Mollick's 15 vs. 5 Framework (Adapted for Technical Teams)

In *15 Times to use AI, and 5 Not to*, Ethan Mollick outlines the frontier where AI is a force multiplier versus where it quietly sabotages the user. Here is how that applies to real engineering and client deliverables:

### The 5 Times AI is the WRONG Tool

| Scenario | Why AI Fails | Real Backend / Business Disaster Example |
| :--- | :--- | :--- |
| **1. Obscure Fact Retrieval (Parametric Recall)** | The model fills memory voids with statistically probable nonsense. | Asking an LLM for the exact cryptographic signature algorithm of an obscure payment gateway; it invents a non-existent parameter that compiles but fails silently in production. |
| **2. Multi-Step Arithmetic & Deterministic Logic** | LLMs predict tokens; they do not possess an internal ALU (Arithmetic Logic Unit). | Asking an LLM to balance a financial ledger or compute cumulative compound interest over 360 monthly loan intervals. (A 10-line Python script or SQL query gives 100% mathematical certainty). |
| **3. High-Stakes Compliance, Legal & Medical Verification** | Hallucinations are indistinguishable in tone from verified facts. | Citing non-existent legal precedents in court filings (the famous *Mata v. Avianca* case) or generating medical dosage instructions without deterministic lookup tables. |
| **4. Tasks Where Verification Cost > Creation Cost** | When checking every single line for subtle edge-case bugs takes 45 minutes, but writing it yourself takes 20 minutes. | Asking AI to write a 300-line complex concurrent async state machine with edge-case race conditions; reviewing every line for re-entrancy bugs takes longer than writing it from scratch. |
| **5. Synthesizing Private / Real-Time Events (Without Context)** | The model has a static training cutoff and zero access to private internal company systems unless fed into context. | Asking: *"Why did the staging database drop connections at 3:14 AM yesterday?"* An LLM without logs will invent an plausible outage narrative that wastes hours of on-call investigation. |

---

## 3. High-Stakes Backend Case Studies: Silent AI Failures

### Case 1: The Hallucinated ORM Parameter
- **The Prompt:** *"Write a SQLAlchemy query to lock rows for update with a 5-second skip-locked timeout."*
- **The AI Output:**
  ```python
  session.query(Task).with_for_update(skip_locked=True, timeout_seconds=5).all()
  ```
- **The Silent Failure:** SQLAlchemy's `with_for_update()` does **not** accept `timeout_seconds` in that version (it accepts `nowait=True` or raw dialect-specific SQL). The Python interpreter ignored the unexpected keyword argument or threw an uncaught `TypeError` during peak production load.
- **The Fix:** Never ask an LLM to guess API signatures. Paste the official library documentation into context or consult the raw docstrings in the IDE.

### Case 2: The Hallucinated SQL Composite Constraint
- **The Prompt:** *"Generate SQLite schema for task tags ensuring case-insensitive uniqueness."*
- **The AI Output:**
  ```sql
  CREATE TABLE task_tags (
      id INTEGER PRIMARY KEY,
      tag_name TEXT COLLATE NOCASE UNIQUE
  );
  ```
  *(Looks correct, but when asked for composite foreign keys with cascaded deletes, the AI silently omitted `PRAGMA foreign_keys = ON;`, which SQLite requires per connection. The developer assumed cascade deletes worked on disk, leaving orphaned rows).*

---

## 4. The Verification Cost Formula

Before delegating work to an AI model, compute the **Net Time ROI**:

$$\text{Time Saved} = T_{\text{manual}} - (T_{\text{prompting}} + T_{\text{generation}} + T_{\text{verification}})$$

- **Positive ROI (Use AI):** Boilerplate scaffolding, test case generation, drafting initial copy, refactoring syntax, explaining complex legacy code. ($T_{\text{verification}}$ is low because the compiler, test runner, or human eye spots errors instantly).
- **Negative ROI (Do Not Use AI):** Subtle cryptographic logic, security audit guarantees, exact regulatory citations, multi-variable financial math. ($T_{\text{verification}}$ requires line-by-line manual audit and research).
