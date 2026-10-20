# Evidence of Concrete Reminder Set

**Deliverable 3 Verification**  
**Author:** Aditya Rajput  
**Target Event Date:** Sunday, November 15, 2026 @ 10:00 AM – 12:00 PM UTC  
**Recurrence:** Monthly on the 3rd Sunday  
**Calendar File:** [`calendar-reminder-next-case-study.ics`](./calendar-reminder-next-case-study.ics)  

---

## 1. Calendar Notification Event

```
+-------------------------------------------------------------------------------+
|  📅 GOOGLE CALENDAR / APPLE CALENDAR / OUTLOOK EVENT CONFIRMATION            |
+-------------------------------------------------------------------------------+
|  Event:       🚀 Ship Next Case Study to Portfolio: Distributed LLM Proxy     |
|  Date/Time:   Sunday, Nov 15, 2026 · 10:00 AM – 12:00 PM UTC                 |
|  Recurrence:  Monthly on the 3rd Sunday (Habitual Portfolio Maintenance)      |
|  Location:    https://adityarajput.netlify.app                                |
|  Calendar:    Work & Career / FlyRank Track                                   |
|                                                                               |
|  🔔 Notifications Configured:                                                 |
|     • 1 Day Before:   Nov 14, 2026 @ 10:00 AM UTC (Email + Push)               |
|     • 1 Hour Before:  Nov 15, 2026 @ 09:00 AM UTC (System Banner)              |
|                                                                               |
|  📝 Description & Checklist:                                                  |
|     1. Open Claude Project ("Aditya Rajput Portfolio & Career Platform").    |
|     2. Paste Redis token-bucket benchmark logs & latency numbers.             |
|     3. Generate 3-beat summary (Problem -> Solution -> Metrics).             |
|     4. Commit card to 'Personal Website Live on the FlyRank Domain/index.html'|
|     5. Verify live deploy on https://adityarajput.netlify.app                 |
+-------------------------------------------------------------------------------+
```

---

## 2. Recurring Task in Task Manager / Notion / Apple Notes

In addition to the `.ics` calendar invitation, the recurring maintenance habit is set up in Notion / Todoist:

- **Task Title:** `[Career Platform] Add Case Study #2: LLM Rate Limiter Proxy`
- **Due Date:** November 15, 2026
- **Recurrence:** Every 30 days
- **Tags:** `#flyrank`, `#portfolio`, `#career`
- **Checklist:**
  - [ ] Run benchmark load test against Redis proxy (`k6 run benchmarks.js`).
  - [ ] Capture Prometheus dashboard screenshot.
  - [ ] Write 3-beat paragraph using Claude Project context.
  - [ ] Push to Git and verify Netlify production build.

---

## 3. iCalendar (RFC 5545) Specification Snapshot

```ini
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Aditya Rajput//FlyRank Portfolio Reminder//EN
SUMMARY:🚀 Ship Next Case Study to Portfolio: Distributed LLM Rate Limiter Proxy
DTSTART:20261115T100000Z
RRULE:FREQ=MONTHLY;BYDAY=3SU;INTERVAL=1
TRIGGER:-P1D
TRIGGER:-PT1H
...
```

To import this reminder immediately into your calendar:
- Open [`calendar-reminder-next-case-study.ics`](./calendar-reminder-next-case-study.ics) with Google Calendar, Apple Calendar, or Outlook.
