# AI Interrogation Log · Three Roads: Choose Your Stack with AI

> **Core Skill:** Treating AI as an adviser you interrogate—giving it real constraints, forcing it to lay out three distinct options with honest trade-offs, and pressure-testing the front-runner before deciding in your own words.

---

## Round 1: Giving AI the Four Constraints & Demanding Three Stack Options

### Prompt Sent to AI
```text
I need to choose the stack for my technical portfolio site. Do NOT give me a single recommendation. Lay out three distinct stack options from simplest (Road 1: No-code) to middle (Road 2: Plain code with AI on a free host) to most powerful (Road 3: Full frontend framework), based strictly on my four real constraints below:

1. BUDGET CONSTRAINT:
   - 100% free only (both building and hosting forever, no credit-card trials or paid tier traps).

2. MY HONEST SKILL LEVEL:
   - Strong in Python, FastAPI, SQL (PostgreSQL & SQLite), Docker Compose, Git, and reading/editing clean HTML & CSS with AI assistance.
   - I am NOT a frontend React/Next.js specialist and I do not want to spend my build weeks debugging webpack/bundler errors or React hydration mismatches.

3. WHAT MY PORTFOLIO NEEDS TO DO (MY SITEMAP & CONTENT MAP):
   - One-Line Claim: "I build containerized Python backends where routes stay five lines long and data survives any restart."
   - Single Primary Conversion Action (every page ladders up to this): Book a 15-minute technical walkthrough call on my calendar.
   - Page 1 (Home / Proof Index - index.html):
     * Hero with one-line claim + primary calendar CTA
     * Lead Case Spotlight (Case 1: A3 Containerize Your Stack — FastAPI + PostgreSQL 16 + Redis 7, 0 lines changed in routes.py/service.py, 2.410ms -> 0.089ms EXPLAIN ANALYZE speedup)
     * Supporting Case Grid (Case 2: W3-A2 Persistent SQLite CRUD API with 11/11 pytest contracts; Case 3: Supabase JWT HTTPBearer Auth API + 6-Stage Prompt Ladder)
     * Footer Conversion Banner
   - Page 2 (Case Studies / Deep-Dive Proof - cases.html):
     * Quick-jump index (#a3-docker-postgres, #w3-a2-sqlite, #auth-and-prompt-ladder)
     * Full Three-Beat breakdowns (Problem -> Decision -> Proof) for all 3 cases
     * Bottom Technical CTA
   - Page 3 (Architecture & Contact - about.html):
     * Engineering Philosophy ("Why My Routes Stay 5 Lines Long" + Stage 6/7 AI vs. Me verification)
     * Verified Technical Stack Matrix linking directly to GitHub folders
     * Direct Calendar & Contact Block

4. HOW MY WORK MUST BE DISPLAYED & DYNAMIC REQUIREMENT:
   - My proof is backend architecture: it must display long-form technical reading (Three-Beat case studies), pixel-sharp monospace terminal outputs (PostgreSQL EXPLAIN ANALYZE query plans), high-resolution cropped screenshots (DB Browser for SQLite, side-by-side code diffs), custom SVG icons/favicon, and direct links to my GitHub repositories.
   - Does anything have to be dynamic yet? NO. Nothing on the portfolio site needs a database, user login, or dynamic server state right now. (In Week 08 I will wire one small live request, which can be a simple client-side fetch).

For each of the 3 options, specify:
- How I would build it
- Where I would host it for free
- Whether it needs a backend
- The real trade-off for my specific backend-focused portfolio
```

---

### AI Response (Three Options with Trade-Offs)

#### Road 1 (Simplest): No-Code Visual Builder (`Carrd` Free Tier or `Framer` Free)
- **How You'd Build:** Drag-and-drop visual blocks inside a browser canvas; paste text and upload screenshots manually.
- **Where You'd Host (Free):** Hosted on a free platform subdomain (e.g., `.carrd.co` or `.framer.website`).
- **Needs a Backend?** **No.**
- **The Real Trade-Off:** You get a live page in 20 minutes without touching a code editor, **but** Carrd's free tier locks you into a single-page layout (breaking your 3-page `index.html` / `cases.html` / `about.html` sitemap), restricts custom `<svg>` favicons and semantic `<pre><code>` blocks, and places a "Made with No-Code" badge on a portfolio meant to prove software engineering rigor.

#### Road 2 (Middle — Front-Runner): Plain Code with AI on a Free Static Host (`Semantic HTML5 + Vanilla CSS` on `GitHub Pages` / `Netlify`)
- **How You'd Build:** Write clean semantic HTML5 files (`index.html`, `cases.html`, `about.html`) and a shared `styles.css` using CSS custom properties (`--bg-canvas: #F8FAFC`, `--text-ink: #0F172A`, `--surface-slate: #1E293B`, `--accent-teal: #0D9488`) with AI generating the markup from your content map.
- **Where You'd Host (Free):** **GitHub Pages** (directly from your existing Git repository) or **Netlify Drop** (drag-and-drop / Git deploy).
- **Needs a Backend?** **No.** All case studies, terminal transcripts, and screenshots are static assets. When Week 08 arrives (`Wire One Real Thing`), a 10-line vanilla `fetch()` script can ping a live endpoint without changing your hosting model.
- **The Real Trade-Off:** You copy shared header/footer markup across 3 HTML files instead of using component imports, **but** you have zero build step, zero npm dependencies that can break, instant `<50ms` page loads, complete control over `JetBrains Mono` code blocks and high-DPI screenshots, and your GitHub repo itself reinforces your engineering credibility.

#### Road 3 (Most Powerful): Full Frontend Framework (`Next.js App Router + TypeScript + Tailwind CSS` on `Vercel`)
- **How You'd Build:** Scaffold a Node.js project (`npx create-next-app`), configure Tailwind, build reusable React server/client components, and compile static/SSR routes.
- **Where You'd Host (Free):** Vercel Hobby tier or Cloudflare Pages.
- **Needs a Backend?** **No** (though Next.js bundles Node API routes you do not currently need).
- **The Real Trade-Off:** Gives you reusable JSX components and a full JavaScript ecosystem, **but** introduces `node_modules` (hundreds of megabytes), build-step failures, React hydration quirks, and Tailwind configuration overhead for a 3-page static portfolio—classic "bringing a bulldozer to plant a flower."

---

## Round 2: Pressure-Testing the Front-Runner (Road 2: Plain HTML5 + CSS on GitHub Pages / Netlify)

### Prompt Sent to AI
```text
Road 2 (Plain semantic HTML5 + Vanilla CSS custom properties on GitHub Pages / Netlify) is my front-runner. Pressure-test this choice honestly against four specific questions:
1. What breaks in my Week 03 plan if I pick the simplest option (Road 1: No-Code) instead?
2. What exact maintenance burden do I take on if I pick the most powerful option (Road 3: Next.js + Tailwind) instead?
3. Can I realistically finish the entire 3-page site in two weeks using Road 2?
4. Does Road 2 display my specific evidence (PostgreSQL EXPLAIN ANALYZE outputs, side-by-side Python diffs, SQLite DB Browser captures, and long-form Three-Beat engineering narratives) the way a senior backend engineer expects to read it?
```

### AI Pressure-Test Analysis
1. **What breaks if you pick the simplest (Road 1: No-Code)?**
   - Your **3-page Content Map breaks immediately** on Carrd Free (which only allows one page) or forces awkward workarounds.
   - Your **Identity Kit breaks**: free no-code tiers restrict custom SVG favicons (`favicon.svg`), exact CSS `:root` variable locking, and accessible `<pre><code>` blocks for `EXPLAIN ANALYZE` output.
   - **Credibility mismatch**: When an Engineering Lead inspects a backend candidate's site, seeing heavy no-code builder wrappers around Python/SQL proofs feels incongruent.
2. **What do you maintain if you pick the most powerful (Road 3: Next.js Framework)?**
   - You maintain `package.json`, `package-lock.json`, Node.js version compatibility, Next.js compiler configs, and npm security advisories (`npm audit`).
   - If you open the repo 6 months from now to add one case study, a broken build plugin or deprecated Node version can block a 2-minute text edit.
3. **Can you finish in two weeks with Road 2 (Plain HTML5 + Vanilla CSS)?**
   - **Easily.** With only 3 pages (`index.html`, `cases.html`, `about.html`) and one stylesheet (`styles.css`), there is zero setup friction. Your "Empty but Live" starter (`index.html`) is already deployed on Day 1, meaning Week 05 is 100% focused on slotting in your already-written Three-Beat copy and curated screenshots.
4. **Does Road 2 show your work the way it needs to be shown?**
   - **Yes—better than any other option.** Backend proof is read like an engineering specification or RFC: clean `65ch` prose (`Inter`), sharp monospace terminal cards (`JetBrains Mono` on `#1E293B`), uncompressed PNG screenshots (`<img loading="lazy">`), and direct links to the raw Python/SQL files in the same GitHub repository.
