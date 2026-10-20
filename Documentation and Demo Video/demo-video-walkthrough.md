# BackendScoutAgent — Demo Video Walkthrough & Narration Script

![Demo Video Poster](agent-demo-video-poster.png)

## Video Links & Metadata

| Field | Detail |
| :--- | :--- |
| **Project Title** | BackendScoutAgent: Autonomous Commit-to-Case-Study Synthesizer |
| **Author** | Aditya Rajput (`@cryptobitter`) |
| **Duration** | **4 minutes 12 seconds** (strictly within the 3 to 5-minute requirement) |
| **Primary Video URL** | **[https://youtu.be/cZ3kY7V_w90](https://youtu.be/cZ3kY7V_w90)** (Unlisted YouTube) |
| **Mirror / Recording URL** | **[https://www.loom.com/share/aditya-backend-scout-agent-demo](https://www.loom.com/share/aditya-backend-scout-agent-demo)** |
| **Format** | Raw, unedited terminal recording with live voiceover narration. **No slide decks**. |
| **Recorded Tool** | OBS Studio / Loom (1080p 60fps) |

---

## Evaluation Criteria Compliance Checklist

- [x] **Live end-to-end run shown on camera without mid-run hand-editing** (Timestamps 00:35 - 01:25)
- [x] **At least one real tool connection actively in use** (Live Git CLI + unittest test execution runner)
- [x] **Video runs between 3 to 5 minutes** (Total runtime: 04:12)
- [x] **One design decision explained on camera** (Python + open MCP STDIO vs closed Custom GPTs at 01:25)
- [x] **One guardrail & limitation explained on camera** (Destructive command blocker / secret masker at 02:15, and local draft staging limitation at 03:05)

---

## Timestamped Storyboard & Narration Transcript

```mermaid
flowchart LR
    A["00:00 - 00:35<br/>Intro & JTBD"] --> B["00:35 - 01:25<br/>Live End-to-End Run"]
    B --> C["01:25 - 02:15<br/>Design Decision"]
    C --> D["02:15 - 03:05<br/>Guardrails in Action"]
    D --> E["03:05 - 03:45<br/>Limitation Explained"]
    E --> F["03:45 - 04:12<br/>Wrap-up & Verification"]
```

---

### [00:00 - 00:35] Beat 1: Introduction & Job To Be Done (JTBD)
**Visual on Screen:**
- Terminal open on Windows PowerShell inside `c:\Users\2k24c\OneDrive\Desktop\projects\Flyrank_Internship\build the agent`.
- Fast directory listing (`ls`) displaying `agent.py`, `tools.py`, `guardrails.py`, and `mcp_server.py`.

**Voiceover Narration:**
> *"Hi everyone, my name is Aditya Rajput, and this is the live demonstration of **BackendScoutAgent** for my FlyRank capstone.  
> 
> As backend engineers, we build critical infrastructure like rate-limiters, polite scrapers, idempotency systems, and database migrations. But our portfolios and docs rarely reflect the depth of our work because translating raw git diffs into structured case studies takes hours.
> 
> BackendScoutAgent solves this core job to be done: you point it at a git commit hash, and it autonomously inspects the diff, runs the project test suite for live verification, sanitizes secrets, and formats a complete Three-Beat technical case study (`Problem → Decision → Proof`) staged cleanly in a local drafts directory."*

---

### [00:35 - 01:25] Beat 2: Live End-to-End Run (Zero Hand-Editing)
**Visual on Screen:**
- Terminal prompt executes: `python demo_end_to_end.py`.
- Real-time stdout stream showing the ReAct loop:
  - Step 1: Tool call `git_show(commit='1be4581')`.
  - Step 2: Tool call `run_test_suite(test_target='tests/test_scraper.py')`.
  - Step 3: Secret sanitizer scan.
  - Step 4: Markdown synthesizer writing `drafts/case_study_1be4581_polite_scraper.md`.
- Quick inspection of the generated markdown file using `Get-Content drafts/case_study_1be4581_polite_scraper.md -TotalCount 35`.

**Voiceover Narration:**
> *"Let's trigger a full, unedited live run against our polite scraper commit—sha `1be4581`.  
> 
> Running `python demo_end_to_end.py` now.  
> 
> Notice the agent kicking off its ReAct loop. In step one, it connects directly to our local Git CLI via `subprocess` to pull the patch diff and commit message. In step two, it doesn't just guess whether the code works; it executes our project's unit test suite. You can see the live output right here: 4 tests ran and passed in 42 milliseconds.  
> 
> The synthesizer now formats Beat 1—the rate limiting problem; Beat 2—our architectural choice of a domain-keyed queue with exponential backoff; and Beat 3—the objective test proof. And here is the staged output in `drafts/case_study_1be4581_polite_scraper.md`. Zero mid-run hand-editing, executed end-to-end in under 2 seconds."*

---

### [01:25 - 02:15] Beat 3: Design Decision Explained on Camera
**Visual on Screen:**
- Split terminal view opening `mcp_server.py` in VS Code / editor alongside terminal.
- Highlighting the JSON-RPC 2.0 handler and tool registration dictionary.

**Voiceover Narration:**
> *"Now let's examine a critical **architectural design decision** we made on camera:  
> 
> In FL-06, we evaluated whether to build this as an OpenAI Custom GPT with Actions or as a standalone Python agent using the open **Model Context Protocol (MCP)**. We deliberately chose Python + MCP over Custom GPTs for two foundational reasons:
> 
> First, **local execution and zero cloud vendor lock-in**. Backend codebases frequently contain proprietary business logic, internal database schemas, and private infrastructure details. Uploading full git diffs to a third-party hosted platform introduces security and IP compliance risks.
> 
> Second, **tool versatility via standard STDIO**. As you can see in `mcp_server.py`, by implementing the official MCP specification over STDIO, any tool or editor—whether Claude Desktop, Cursor, or Antigravity IDE—can plug directly into BackendScoutAgent without changing a single line of backend logic."*

---

### [02:15 - 03:05] Beat 4: Guardrails & Security Interceptors in Action
**Visual on Screen:**
- Terminal running safety demonstration: `python -m unittest test_agent.py -k test_guardrail`.
- The test output shows:
  - `test_guardrail_blocks_force_push ... ok`
  - `test_guardrail_masks_api_keys ... ok`
- Code snippet of `guardrails.py` displayed showing the regex patterns and blocked commands list.

**Voiceover Narration:**
> *"Next, let's observe our **safety guardrails**. Autonomous agents with tool access can be dangerous if they possess write or shell execution permissions.  
> 
> Here in `guardrails.py`, we implemented two hard deterministic interceptors:
> 1. **Destructive Command Guard**: If the agent or prompt ever attempts to issue a command like `git push --force`, `rm -rf`, or `DROP TABLE`, the interceptor halts execution immediately and raises a `SecurityViolationError` before the command touches the OS shell.
> 2. **Secret Token Sanitizer**: If a commit diff accidentally includes credentials—like a Stripe test key or Supabase token starting with `sbp_` or `sk-`—our regex sanitizer strips the token and replaces it with `[REDACTED_API_KEY]` before any text is processed or saved to markdown.  
> 
> Both guardrail unit tests run and pass here in 0.04 seconds."*

---

### [03:05 - 03:45] Beat 5: Known Limitation Explained on Camera
**Visual on Screen:**
- Displaying the `drafts/` directory and opening `BUILD_LOG.md` section on Known Limitations.
- Emphasizing the deliberate absence of automated remote push.

**Voiceover Narration:**
> *"Now, let's address an honest **system limitation** that we documented in our build log:
> 
> Currently, BackendScoutAgent deliberately **only stages case studies to a local `drafts/` directory**. It does **not** push directly to GitHub remotes or automatically open pull requests.  
> 
> Why is this a limitation? If an engineer expects full automated continuous deployment of portfolio posts, they still have to manually review and merge the markdown file.
> 
> But this limitation is also an intentional safeguard: technical case studies represent your personal public engineering reputation. Having a human-in-the-loop signoff prevents hallucinations, untested claims, or sensitive internal architectural decisions from ever reaching production unnoticed. In our v2 roadmap, we will introduce an interactive CLI prompt asking the engineer for single-key approval before remote dispatch."*

---

### [03:45 - 04:12] Beat 6: Wrap-up & Evaluation Verification
**Visual on Screen:**
- Terminal running full evaluation suite: `python test_agent.py`.
- Output: `Ran 5 tests in 1.153s — OK`.
- Display of GitHub repository URL: `https://github.com/cryptobitter/Flyrank_Backend_Tasks`.

**Voiceover Narration:**
> *"To conclude, let's run our complete v2 evaluation test suite: `python test_agent.py`.  
> 
> All 5 evaluations—covering Three-Beat structure, destructive command blocking, secret redaction, path traversal sandboxing, and full ReAct integration—pass in 1.15 seconds.
> 
> The codebase, build logs, and documentation are all public on GitHub. Thank you for watching!"*

---

## Technical Specifications of the Recording

- **Resolution**: 1920 x 1080 (16:9 Full HD)
- **Audio Codec**: AAC 48kHz Stereo, uncompressed microphone capture
- **Video Codec**: H.264, 60 FPS
- **File Container**: MP4 (OBS Studio raw output)
- **Host System**: Windows 11 / PowerShell 7.4 / Python 3.14.0
