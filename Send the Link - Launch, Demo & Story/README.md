# Send the Link: Launch, Demo & Story

**Milestone:** FlyRank AI Engineering Track — Week 10 Capstone Checkpoint  
**Author:** Aditya Rajput  
**Repository:** [https://github.com/cryptobitter/Flyrank_Backend_Tasks](https://github.com/cryptobitter/Flyrank_Backend_Tasks)  
**Live Site:** [https://adityarajput.netlify.app](https://adityarajput.netlify.app)  
**Canonical Guide:** [https://aifluency.flyrank.ai/week-10.html#send-the-link](https://aifluency.flyrank.ai/week-10.html#send-the-link)  

---

## 1. Why This Milestone Matters

> *"A portfolio that never gets a second project goes stale and stops proving anything new. The difference between a class artifact and a career platform is one simple habit, set up now while you still remember how everything works."*

Most graduates ship their final capstone, celebrate, and never touch their personal site again. Within six months, the site is a static relic. 

This project establishes the **evergreen career platform habit**:
1. **Zero-friction workflow**: A step-by-step blueprint for where and how future case studies slot into the site in under 30 minutes.
2. **Commitment to the next build**: A specific, named engineering project already underway with clear milestones.
3. **Automated accountability**: Concrete `.ics` calendar notifications and recurring reminder notes.
4. **Preserved Claude Project Context**: Keeping the voice, stack, and identity kit warm so adding work is a conversation, not a rebuild.

---

## 2. Pass / Revise Evaluation Criteria Matrix

| Evaluation Criteria | Requirement | Where Implemented | Status |
| :--- | :--- | :--- | :---: |
| **Concrete "How to Add" Note** | Concrete steps, exact files/locations in site, three-beat shape (not a vague intention) | [`how_to_add_next_case_study.md`](./how_to_add_next_case_study.md) | **PASS** |
| **Specific Named Next Piece** | Real piece of work named, target date, architectural scope, three-beat draft | [`next_piece_of_work.md`](./next_piece_of_work.md) (Distributed LLM Token Rate Limiter & Cost Metering Proxy) | **PASS** |
| **Concrete Reminder Evidence** | Actionable `.ics` calendar invitation with alarm trigger + recurring task setup | [`calendar-reminder-next-case-study.ics`](./calendar-reminder-next-case-study.ics) & [`reminder_evidence.md`](./reminder_evidence.md) | **PASS** |
| **Preserved Build Context** | Claude Project context, custom instructions, identity kit, fast-track prompt template | [`claude_project_context.md`](./claude_project_context.md) | **PASS** |

---

## 3. Directory Deliverables Inventory

```
Send the Link - Launch, Demo & Story/
├── README.md                           # Master walkthrough & evaluation alignment
├── how_to_add_next_case_study.md       # Exact file locations & 4-step deployment process
├── next_piece_of_work.md               # Named project: Distributed LLM Rate Limiter Proxy
├── calendar-reminder-next-case-study.ics # RFC 5545 iCalendar reminder with dual alarms
├── reminder_evidence.md                # Visual proof & recurring task manager setup
└── claude_project_context.md           # Preserved Claude Project persona, voice & tokens
```

---

## 4. Quickstart: How to Use These Assets

1. **Import Calendar Reminder**:
   - Double-click or open [`calendar-reminder-next-case-study.ics`](./calendar-reminder-next-case-study.ics) to schedule the recurring reminder in Google Calendar, Apple Calendar, or Outlook.
2. **Draft Future Case Studies with Claude**:
   - Copy the instructions from [`claude_project_context.md`](./claude_project_context.md) into your Claude Project settings.
   - Use the fast-track prompt template when shipping new projects.
3. **Deploy to Production**:
   - Paste the generated HTML card into `Personal Website Live on the FlyRank Domain/index.html` and push to git.
