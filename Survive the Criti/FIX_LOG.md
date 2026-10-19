# Fix Log: Must-Fixes Addressed on the Live Portfolio

**Assignment:** Survive the Crit (Checkpoint 1)  
**Author:** Aditya Rajput  
**Target File:** `index.html` (Deployed on GitHub Pages / Netlify)  

---

## 1. Summary of Changes Applied

| Fix ID | Component | Change Type | Status on Live Site |
|---|---|---|---|
| **FIX-01** | Hero Headline & Subtitle | Content / Positioning Rewrite | **DEPLOYED & VERIFIED** |
| **FIX-02** | Brand Header & Metadata | Identity Alignment (Aditya Rajput) | **DEPLOYED & VERIFIED** |
| **FIX-03** | Case Studies 02 & 03 | Converted Static Cards to Clickable Repo Links | **DEPLOYED & VERIFIED** |
| **FIX-04** | Benchmark Caption Contrast | WCAG AA/AAA Darkening & Outline | **DEPLOYED & VERIFIED** |
| **FIX-05** | Mobile Sticky Bar | Added Responsive Fixed Bottom CTA Bar | **DEPLOYED & VERIFIED** |

---

## 2. Granular Code Diffs

### FIX-01: Hero Headline & Subtitle (10-Second Test Resolution)
**Rationale:** Directly state role and target audience (B2B SaaS startups) instead of witty developer slogans.

```diff
- <h1>I build containerized Python backends where routes stay five lines long and data survives any restart.</h1>
- <p class="lead">
-   Verified on real mobile viewports: touch targets exceed 48px, text passes WCAG AA contrast, terminal transcripts wrap safely, and the portfolio is wired end-to-end with a live walkthrough request form on a free-tier serverless backend.
- </p>
+ <h1>I build containerized Python REST APIs and relational database architectures for early-stage B2B SaaS.</h1>
+ <p class="lead">
+   Built for Engineering Leads and Technical Founders who need maintainable backend services with clean repository patterns, sub-millisecond database queries, and zero hand-holding.
+ </p>
```

---

### FIX-02: Identity & Name Prominence
**Rationale:** Ensure prospective employers and founders recognize Aditya Rajput immediately.

```diff
- <title>Cryptobitter · Backend &amp; API Systems Portfolio</title>
+ <title>Aditya Rajput · Backend &amp; API Systems Portfolio (@cryptobitter)</title>

- <span class="brand-name">cryptobitter</span>
+ <span class="brand-name">Aditya Rajput <span style="font-weight: 400; color: var(--text-muted); font-size: 0.85rem;">(@cryptobitter)</span></span>
```

---

### FIX-03: Clickable Deep-Links on Case Studies 02 & 03
**Rationale:** Replace static text slots with active GitHub links to real code and test suites.

```diff
- <div class="slot-card">
-   <span class="slot-title">02 · Supporting Case: Zero-Rewrite SQLite Repository Migration (W3-A2)</span>
-   <span class="slot-meta">[11/11 Pytest Contracts · Passed]</span>
- </div>
+ <a class="slot-card" href="https://github.com/cryptobitter/Flyrank_Backend_Tasks/tree/main/W3-A2" target="_blank" rel="noopener noreferrer" style="text-decoration: none;">
+   <div>
+     <span class="slot-title">02 · Supporting Case: Zero-Rewrite SQLite Repository Migration (W3-A2)</span>
+     <p style="font-size: 0.82rem; color: var(--text-muted); margin-top: 0.25rem;">Clean repository pattern separating route handlers from SQLite/PostgreSQL drivers.</p>
+   </div>
+   <span class="slot-meta">[11/11 Pytest Contracts &middot; View Code &rarr;]</span>
+ </a>

- <div class="slot-card">
-   <span class="slot-title">03 · Security &amp; Reliability: Supabase JWT Middleware + Prompt Ladder</span>
-   <span class="slot-meta">[HTTPBearer + 6-Stage Eval · Passed]</span>
- </div>
+ <a class="slot-card" href="https://github.com/cryptobitter/Flyrank_Backend_Tasks/tree/main/Auth%20-%20Login%20%26%20protect" target="_blank" rel="noopener noreferrer" style="text-decoration: none;">
+   <div>
+     <span class="slot-title">03 · Security &amp; Reliability: Supabase JWT Middleware &amp; Guardrails</span>
+     <p style="font-size: 0.82rem; color: var(--text-muted); margin-top: 0.25rem;">Protected endpoints with HTTPBearer dependency injection and prompt safety filters.</p>
+   </div>
+   <span class="slot-meta">[HTTPBearer + Tests &middot; View Code &rarr;]</span>
+ </a>
```

---

### FIX-04: Mobile Sticky Action Bar
**Rationale:** Ensure phone users never lose sight of the single primary action: booking the 15-minute walkthrough call.

```html
<!-- Mobile Sticky Action Bar -->
<div class="mobile-sticky-cta" aria-label="Quick Action">
  <div style="font-size: 0.8rem; font-weight: 600; color: var(--text-ink);">Need a backend engineer?</div>
  <a class="btn-primary" href="#contact" style="padding: 0.5rem 0.85rem; font-size: 0.85rem; min-height: 40px;">
    Book 15-Min Walkthrough &darr;
  </a>
</div>
```

With supporting responsive CSS:
```css
.mobile-sticky-cta {
  display: none;
}

@media (max-width: 640px) {
  .mobile-sticky-cta {
    display: flex;
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    background: rgba(248, 250, 252, 0.95);
    backdrop-filter: blur(8px);
    border-top: 1px solid var(--border-subtle);
    padding: 0.65rem 1rem;
    justify-content: space-between;
    align-items: center;
    z-index: 100;
  }
}
```
