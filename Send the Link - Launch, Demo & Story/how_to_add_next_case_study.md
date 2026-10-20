# How to Add the Next Case Study

**Author:** Aditya Rajput  
**Repository:** `cryptobitter/Flyrank_Backend_Tasks`  
**Site:** `adityarajput.netlify.app` (Live on FlyRank Domain)  
**Standard:** Week 2 Three-Beat Shape (Problem $\rightarrow$ What You Did $\rightarrow$ What Came of It)  

---

## 1. Exactly Where It Goes in the Site & Repository

The case study lives in two coupled locations:

1. **Portfolio Showcase Section (`index.html`)**:
   - Location: [`Personal Website Live on the FlyRank Domain/index.html`](file:///c:/Users/2k24c/OneDrive/Desktop/projects/Flyrank_Internship/Personal%20Website%20Live%20on%20the%20FlyRank%20Domain/index.html) inside `<section id="work" class="py-20">`.
   - Grid Container: Directly inside the `<div class="grid grid-cols-1 md:grid-cols-2 gap-8">` container as an `<article class="group relative rounded-2xl border border-slate-800 bg-slate-900/50 p-6 ...">`.
   - Navigation Link: Tagged with category badge `data-category="backend-ai"` for filtering.

2. **Dedicated Deep-Dive Case Study Page**:
   - File Path: `Personal Website Live on the FlyRank Domain/case-studies/{project-slug}.html`
   - Linked from: Card's primary CTA button `"Read Case Study →"` and GitHub source pill.

---

## 2. The 4-Step Process to Add It (Under 30 Minutes)

### Step 1: Open Your Preserved Claude Project
Open the **"Aditya Rajput | Portfolio & Career Platform"** Claude Project (see [`claude_project_context.md`](./claude_project_context.md)). It already knows your identity kit, concise engineering tone, and CSS component classes. Paste your raw terminal logs, architecture sketch, and git commit history into the prompt:
> *"Draft my next portfolio card and deep-dive page using our three-beat shape and Tailwind tokens."*

### Step 2: Format Using the Three-Beat Shape
Every case study must strictly conform to the three-beat shape:

```markdown
### [Project Title]: [One-Line Value Proposition]
- **Beat 1: The Problem** (2–3 sentences)
  What broke, bottlenecked, or wasted hours in the wild? Name the friction without academic fluff.
- **Beat 2: What You Did** (3–4 sentences)
  What concrete engineering system did you build? Name the stack, architecture, and the single hardest technical choice.
- **Beat 3: What Came of It** (2 sentences + metrics callout)
  What is the measurable quantitative outcome? Latency reduction, error rate, throughput, or hours saved.
```

### Step 3: Insert Component Card HTML
Copy the standardized component block into `Personal Website Live on the FlyRank Domain/index.html`:

```html
<article class="group relative rounded-2xl border border-slate-800 bg-slate-900/40 p-6 transition-all hover:border-indigo-500/50 hover:bg-slate-900/80">
  <div class="flex items-center justify-between text-xs font-mono text-slate-400 mb-3">
    <span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
      Production Live
    </span>
    <span>November 2026</span>
  </div>
  <h3 class="text-xl font-bold text-white group-hover:text-indigo-400 transition-colors">
    [Project Title]
  </h3>
  <p class="mt-2 text-sm text-slate-300 leading-relaxed">
    <strong>Problem:</strong> [Beat 1]<br>
    <strong>Solution:</strong> [Beat 2]<br>
    <strong>Impact:</strong> [Beat 3]
  </p>
  <div class="mt-4 flex flex-wrap gap-2 text-xs font-mono text-slate-400">
    <span class="px-2 py-1 rounded bg-slate-800/80">[Tool 1]</span>
    <span class="px-2 py-1 rounded bg-slate-800/80">[Tool 2]</span>
    <span class="px-2 py-1 rounded bg-slate-800/80">[Tool 3]</span>
  </div>
  <div class="mt-5 flex items-center gap-4">
    <a href="https://github.com/cryptobitter/[repo]" class="text-xs font-semibold text-indigo-400 hover:text-indigo-300 flex items-center gap-1">
      Source Code ↗
    </a>
    <a href="https://[live-url]" class="text-xs font-semibold text-slate-400 hover:text-white flex items-center gap-1">
      Live Demo ↗
    </a>
  </div>
</article>
```

### Step 4: Deploy & Verify
```bash
# Test locally
npx serve "Personal Website Live on the FlyRank Domain"

# Deploy live via Git (Netlify auto-publishes upon commit push)
git add "Personal Website Live on the FlyRank Domain/index.html"
git commit -m "feat(portfolio): add new case study using three-beat shape"
git push origin main
```
Netlify automatically runs CI/CD and updates `https://adityarajput.netlify.app` over HTTPS within 45 seconds.
