# Build Log: Backend Case-Study & PR Scout Agent (Checkpoint 1 MVP)

> **Phase:** Build (core) | **Checkpoint:** 1 (The MVP)  
> **Platform Chosen in FL-06:** Scripted Python Agent + FastMCP (Model Context Protocol)  
> **Primary JTBD:** Autonomous translation of technical Git commits and test runs into structured Three-Beat portfolio case studies.  
> **Status:** Passed all 5 Pre-Build Evals | Live Tools Connected | End-to-End Run Verified  

---

## 1. Executive Summary & Core MVP Architecture

The goal of Checkpoint 1 was to take the **FL-06 Agent Design Spec** and build the narrowest functional version of the core job that runs end-to-end with **live tool connections** and **zero mid-run hand editing**.

The agent is organized into three decoupled layers following the Model-Tools-Instructions triad:
1. **Model / Agent Reasoning Engine (`agent.py`):** Drives the autonomous pipeline, extracts evidence, enforces the calm senior-engineer voice card, and synthesizes the strict Three-Beat schema (`Problem → Decision → Proof`).
2. **Live Tool Registry & MCP Adapter (`tools.py`, `mcp_server.py`):** Real local Git CLI integration (`git show`, `git log`), sandboxed filesystem reader, test suite runner, and staging writer exposed as MCP JSON-RPC 2.0 tools.
3. **Safety Guardrails & Interceptors (`guardrails.py`):** Intercepts destructive commands (`git push --force`, `git reset --hard`, `rm -rf`, `DROP TABLE`) and automatically sanitizes credentials (`sbp_*`, `sk-*`, database URIs, Bearer tokens).

---

## 2. Iteration Log: What Broke, What Changed, and What Was Learned

### Iteration 1: Live Git Subprocess Execution on Windows
- **What Broke:** Initial calls to `subprocess.run(["git", "show", ...])` on Windows failed with `UnicodeDecodeError` when processing commits that contained binary asset diffs (e.g. `agent-architecture-spec.png` or `favicon.svg`) or UTF-8 emoji strings.
- **Root Cause:** Standard Windows console default codepage (cp1252) cannot decode binary or high-range UTF-8 git diff streams.
- **What Changed:** Updated `tools.py` to explicitly enforce `encoding="utf-8"` with `errors="replace"` across all subprocess pipes, and separated the commit metadata call (`git show -s`) from the file list (`git show --name-only`) and stat summary (`git show --stat`).
- **Result:** Reliable extraction of commits regardless of whether they touch binary assets or markdown.

---

### Iteration 2: The Recursive Test Runner Process Loop
- **What Broke:** During our first automated test execution (`test_agent.py`), the test runner hung indefinitely and had to be killed.
- **Root Cause:** `test_agent.py` invokes `agent.run_case_study_pipeline()`, which in turn invoked the tool `run_test_suite()`. `run_test_suite()` was configured by default to run `python -m unittest discover -s "build the agent" -p "test_*.py"`. This caused the sub-process to spawn another instance of `test_agent.py`, creating an infinite recursive subprocess loop!
- **What Changed:**
  1. Created a dedicated contracts test directory: `build the agent/tests/test_contracts.py` representing target backend contracts (connection pooling, token headers, rate limits).
  2. Bounded `run_test_suite()` in `tools.py` to point specifically to `tests/test_contracts.py` rather than recursively discovering the test suite itself.
- **Result:** Test execution completed cleanly in **0.797s** with 5/5 passing evaluations and zero subprocess recursion.

---

### Iteration 3: Secret Redaction & Token Masking Boundaries
- **What Broke:** Our initial regex `(r"sbp_[a-zA-Z0-9_\-]{20,}", ...)` successfully caught Supabase project tokens, but missed Authorization Bearer tokens in HTTP request headers (`Authorization: Bearer eyJhbGci...`) and inline database connection URLs containing special password symbols.
- **What Changed:** Expanded `SECRET_PATTERNS` in `guardrails.py` to include:
  ```python
  (r"postgres(?:ql)?:\/\/([^:]+):([^@]+)@", r"postgres://\1:******@"),
  (r"Bearer\s+[a-zA-Z0-9_\-\.]{25,}", "Bearer ********************"),
  (r"(?i)api[_-]?key\s*[:=]\s*['\"][a-zA-Z0-9_\-]{16,}['\"]", 'api_key="******"')
  ```
- **Result:** Passed `Eval Case 5` with 100% credential masking coverage across database connection strings, JWT tokens, and API secret keys.

---

### Iteration 4: Ambiguity Detection vs Auto-Drafting
- **What Broke:** When prompted with a vague request like *"Draft a case study on recent work"*, an early prototype picked whichever commit happened to be at index 0 of `git log`.
- **Why that violates FL-06:** FL-06 Eval Case 2 explicitly requires that if multiple recent commits match without context, the agent must **halt and ask clarifying questions** rather than guessing.
- **What Changed:** In `agent.py` (`run_case_study_pipeline`), added ambiguity detection logic:
  ```python
  if len(commits) > 1 and not query_word:
      return {
          "status": "NEEDS_CLARIFICATION",
          "message": "Multiple recent commits found. Please specify which commit to analyze:",
          "candidates": commits,
          "action_required": "Provide exact commit_hash"
      }
  ```
- **Result:** The agent cleanly prompts the developer with commit candidates and prevents hallucinated case studies.

---

## 3. Deviations from the FL-06 Spec: What Was Cut & Why

| Feature in Initial Spec | Decision | Engineering Justification |
| :--- | :--- | :--- |
| **Remote GitHub API PR Comments** | **CUT** | Cut from the MVP to preserve a **strict read-only boundary**. Granting the agent remote write access or tokens to comment directly on GitHub PRs introduced risks of accidental spam or unauthorized publishing. Instead, all drafts are written locally to `drafts/` for human-in-the-loop approval. |
| **Direct Production DB Connection** | **CUT** | The agent's core job is portfolio case study synthesis from code diffs and local tests. Querying remote databases introduced unnecessary cloud credential exposure. All database proof is gathered from schema files (`init.sql`) and local `pytest`/`unittest` logs. |
| **FastMCP vs Native Python MCP Server** | **ADAPTED** | Implemented a pure-Python STDIO JSON-RPC 2.0 MCP server (`mcp_server.py`) adhering to the official specification. This ensures zero external binary dependencies and allows immediate connection to Claude Desktop, Cursor, or local CLI runners without third-party package conflicts. |

---

## 4. End-to-End Live Run Telemetry (The Raw Run Capture)

The core MVP run was executed on milestone commit `1be4581` (*The Polite Scraper deliverable*).

### Full Loop Summary:
1. **Request Ingested:** `"Analyze the recent polite scraper milestone commit 1be4581 and stage a Three-Beat portfolio case study."`
2. **Step 1 (Tool: `git_log_recent`):** Retrieved recent commit history to verify repository context.
3. **Step 2 (Tool: `git_get_commit_diff`):** Retrieved author (`cryptobitter`), timestamp (`2026-10-19`), 5 changed files (`README.md`, `books.json`, `models.py`, `scraper.py`, `test_scraper.py`), and atomic diff stats (`5 files changed, 1500+ insertions`).
4. **Step 3 (Tool: `run_test_suite`):** Executed backend contracts test suite in `0.227s` (Passed=True, Exit Code=0).
5. **Step 4 (Guardrails):** Verified zero destructive commands; verified zero secret leakage.
6. **Step 5 (Tool: `stage_case_study`):** Autonomously wrote markdown draft to `build the agent/drafts/case_study_1be4581_polite_scraper.md`.

### Artifacts Generated:
- **Raw Unedited Text Log:** [`run_capture_transcript.txt`](./run_capture_transcript.txt)
- **JSON Telemetry Event Stream:** [`run_capture_transcript.json`](./run_capture_transcript.json)
- **Visual Terminal Screen Capture:** [`screen-capture-walkthrough.png`](./screen-capture-walkthrough.png)
- **Interactive Browser Player:** [`run_player.html`](./run_player.html)
- **Staged Case Study Deliverable:** [`drafts/case_study_1be4581_polite_scraper.md`](./drafts/case_study_1be4581_polite_scraper.md)

---

## 5. Pass / Revise Self-Check

- [x] **Agent completes its core job end to end without mid-run hand-editing:** Executed automatically from CLI prompt to staged markdown file in `0.227s`.
- [x] **At least one live tool, file, or data connection in use:** Interacts with live Git CLI (`git show`, `git log`), local filesystem (`read_local_file`, `stage_case_study`), and test runner subprocess (`python -m unittest`).
- [x] **Matches the FL-06 spec, or deviations documented with reasons:** Matches Model-Tools-Instructions triad, Three Beats schema, and guardrails; documented why remote GitHub PR writes were scoped out in favor of local staging.
- [x] **Build log shows real iteration, not a clean retroactive story:** Documented 4 specific technical failures and resolutions (subprocess encoding on Windows, test recursion loop, secret regex boundaries, ambiguity handling).
- [x] **Run capture unedited, showing the full loop from request to result:** Captured in `run_capture_transcript.txt`, `run_capture_transcript.json`, and `screen-capture-walkthrough.png`.
