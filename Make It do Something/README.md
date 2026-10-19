# Week 08 Deliverable: Make It Do Something

> **Phase:** Submit | **Estimated Hours:** 4  
> **Assignment Reference:** [FlyRank AI Fluency — Week 08: Make It Do Something](https://aifluency.flyrank.ai/week-08.html#make-it-do-something)  
> **Core Concept:** A static portfolio tells; a portfolio with one real feature *does*. Wiring exactly one thing, and understanding it, is the difference between a poster and a tool.

---

## 1. Quick Links to Deliverables

| Deliverable Item | File Link | Description |
| :--- | :--- | :--- |
| **The Live Working Feature** | [`contact-form.html`](./contact-form.html) | Complete accessible HTML5/CSS component matching our Week 03 Visual Identity Kit with honeypot anti-spam, graceful failure states, and free-tier backend wiring. |
| **Plain-Words Explainer** | [`plain-words-explainer.md`](./plain-words-explainer.md) | Honest, jargon-free explanation of what a backend is, what this feature does, and a 6-stage data flow trace from browser keystrokes to Gmail inbox. |
| **Automated Test & Verifier** | [`test_submission.py`](./test_submission.py) | Python test script validating form structure, honeypots, and executing live HTTPS test submissions. |
| **Verified Server Receipt** | [`submission-evidence.json`](./submission-evidence.json) | Captured server response (HTTP 200 OK, latency, payload, UTC timestamp) proving live end-to-end function. |
| **Visual Proof Artifact** | [`live-form-and-submission-proof.png`](./live-form-and-submission-proof.png) | High-resolution side-by-side terminal verification and receipt graphic. |
| **Portfolio Integration** | [`../index.html`](../index.html#contact) | Live integration of the walkthrough form into the main portfolio page. |

---

## 2. The One Feature Chosen

Rather than half-wiring three separate features, we wired **exactly one dynamic feature** that our backend engineering portfolio urgently requires:

**The 15-Minute Technical Walkthrough Request Form**
- **The Job:** Allows technical leads and recruiters to request a 15-minute walkthrough of our containerized FastAPI/PostgreSQL architecture, 0.089ms index benchmarks, or SQLite zero-rewrite migrations.
- **The Backend:** A zero-maintenance, free-tier serverless form gateway (Netlify Forms + Formsubmit.co) that catches incoming submissions, validates against spam, formats an HTML notification, and dispatches it straight to `adityarajput.86046@gmail.com`.
- **Cost:** **$0.00 / Free Tier forever**.

---

## 3. End-to-End Data Flow Summary

```mermaid
sequenceDiagram
    autonumber
    actor Recruiter as Recruiter / Visitor
    participant Browser as Client Browser (index.html)
    participant Gateway as Free-Tier Form Backend
    actor Developer as Cryptobitter Inbox (adityarajput.86046@gmail.com)

    Recruiter->>Browser: Enters Name, Email, Topic, and Message
    Recruiter->>Browser: Hits "Send Walkthrough Request →"
    Note over Browser: Validates non-empty fields & email format.<br/>Checks hidden honeypot (_honey) field.
    Browser->>Gateway: HTTPS POST /ajax (JSON payload)
    Note over Gateway: Checks spam tokens, verifies origin,<br/>dispatches SMTP notification email.
    Gateway->>Developer: Delivers message to Gmail inbox
    Gateway-->>Browser: Returns HTTP 200 OK {"success": "true"}
    Note over Browser: Replaces form with confirmed<br/>"Request Received!" state.
```

---

## 4. How It Fails Gracefully

In accordance with the assignment brief, the form includes graceful handling for real-world failure cases:

1. **Empty Submission:** If submitted without name or message, JavaScript halts submission, prevents page reload, highlights the field, and displays a friendly inline alert (*"Please provide your name or organization so I know who I am speaking with."*).
2. **Invalid Email Address:** Rejects malformed strings like `alex@domain` without erasing the user's message.
3. **Automated Spam Crawlers:** A visually hidden honeypot input (`_honey`) traps automated bot scrapers. Genuine users never see it; bots fill it out and are silently dropped with zero spam delivered to the inbox.
4. **Network Outage:** If the visitor's internet disconnects, the form catches the network error and provides a calm fallback with a direct email link.

---

## 5. Visual Proof of Live Execution

![Live Form & Submission Proof](./live-form-and-submission-proof.png)

---

## 6. Pass / Revise Self-Evaluation Checklist

- [x] **Exactly one feature, working live end to end, not several half-wired:** The 15-Minute Technical Walkthrough Request form is 100% wired from HTML inputs to Gmail notification.
- [x] **It is on a free tier and genuinely functions on a real test:** Wired via free-tier gateway; live HTTPS test verified in `submission-evidence.json` with HTTP 200 OK.
- [x] **The explainer is correct, in own words, and shows understanding of the data flow:** Detailed in [`plain-words-explainer.md`](./plain-words-explainer.md) using the restaurant kitchen analogy and 6-stage trace.
