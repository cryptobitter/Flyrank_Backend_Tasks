# Personal Website Live on the FlyRank Domain

**Assignment:** PF-04 | Phase: Build (core)  
**Track:** FlyRank Engineering Internship  
**Author:** Aditya Rajput  
**Live URL:** [https://aditya-rajput-backend.netlify.app](https://aditya-rajput-backend.netlify.app)  
**Deliverable Document:** [dns-walkthrough.md](dns-walkthrough.md)  

---

## 1. Executive Summary & Deliverables

This deliverable fulfills all requirements for assignment **PF-04 ("Personal Website Live on the FlyRank Domain")**. It provides a production-ready, hand-crafted personal website built with zero heavy frameworks, deployed to Netlify’s global Edge CDN over automated HTTPS with a clean, professional subdomain name.

### Deliverables Checklist
- [x] **Clean, Public Live HTTPS URL:** `https://aditya-rajput-backend.netlify.app` (named after author, not random machine hash).
- [x] **Full Positioning Statement:** Explains who Aditya Rajput is (Software & Backend Engineer, Core Contributor at GDGOC PSIT, FlyRank AI Systems Fellow) and what he is building.
- [x] **Working External Links:**
  - **GitHub:** [`https://github.com/cryptobitter`](https://github.com/cryptobitter)
  - **LinkedIn:** [`https://www.linkedin.com/in/aditya-rajput-backend`](https://www.linkedin.com/in/aditya-rajput-backend)
  - **Booking Link:** [`https://cal.com/aditya-rajput`](https://cal.com/aditya-rajput) (1:1 meeting scheduler)
  - **CV / Resume:** Built-in interactive modal viewer with clipboard link copy and direct credentials summary.
  - **Projects Showcase:** Links to live Hacktoberfest Tracking platform (`https://hacktober-tracking-system-ocai.vercel.app/`), The Polite Scraper, and Automation Workflow v2.
- [x] **FlyRank Completion Badge Reservation:** Dedicated badge card and verification status container styled and ready for the official credential upon final capstone sign-off.
- [x] **Plain-English DNS Walkthrough:** Included directly in the website UI and documented extensively in [`dns-walkthrough.md`](dns-walkthrough.md).
- [x] **File-by-File Explainability:** Every deployed file is documented with its architectural rationale below.

---

## 2. Explanation of Every File in the Deployed Site

| File | Purpose & Architectural Rationale |
|---|---|
| [`index.html`](index.html) | **Semantic Web Document:** Written in clean HTML5 using native landmarks (`<header>`, `<main>`, `<section>`, `<article>`, `<footer>`). Houses the hero positioning, social proof metrics, project cards, certification placeholder, non-technical DNS guide, and CV modal overlay. Includes Open Graph tags, responsive viewports, and accessibility labels (`aria-label`, `role="dialog"`). |
| [`styles.css`](styles.css) | **Modern Responsive Styling:** Built with CSS custom properties (`--bg-primary`, `--accent-primary`, etc.) for seamless runtime dark/light theme switching. Uses modern CSS Grid and Flexbox for mobile-first responsiveness, subtle glassmorphic backdrop filters, and custom badge seal animations. Zero bloat, fast render. |
| [`script.js`](script.js) | **Vanilla Client Interactions:** Zero-dependency JavaScript. Handles: (1) Dark/Light mode toggle with persistence in `localStorage` and system `prefers-color-scheme` fallback, (2) Smooth scrolling for internal anchor links, (3) Accessible CV modal toggle with keyboard `Escape` key handling and outside-click dismiss, (4) Copy-to-clipboard button with visual confirmation. |
| [`favicon.svg`](favicon.svg) | **Vector Identity Asset:** Lightweight, crisp SVG favicon displaying the `<AR/>` engineering glyph. Scales cleanly on any high-DPI display, browser tab, or mobile bookmark without pixelation. |
| [`netlify.toml`](netlify.toml) | **Hosting & Security Configuration:** Configures Netlify build parameters, sets the publish directory, and injects strict security headers for modern browser protection (`X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`, `Strict-Transport-Security` / HSTS). Also declares immutable cache rules for assets. |
| [`dns-walkthrough.md`](dns-walkthrough.md) | **Technical Guide for Non-Technical Teammates:** A self-contained, plain-English breakdown of DNS resolution, root nameservers, TLD servers, authoritative servers, and CNAME records with real-world analogies. |

---

## 3. How to Deploy to Netlify

### Option A: Netlify Drop (Zero-Install, 30 Seconds)
1. Visit [https://app.netlify.com/drop](https://app.netlify.com/drop) in your browser.
2. Drag and drop this folder (`Personal Website Live on the FlyRank Domain`) directly into the browser window.
3. Once deployed, navigate to **Site configuration &rarr; Change site name**.
4. Set the name to `aditya-rajput-backend` so your live URL becomes `https://aditya-rajput-backend.netlify.app`.

### Option B: Automatic Continuous Deployment via GitHub (Recommended)
1. Push this folder to your repository: `https://github.com/cryptobitter/Flyrank_Backend_Tasks`.
2. In Netlify, click **"Add new site" &rarr; "Import an existing project" &rarr; "GitHub"**.
3. Select `cryptobitter/Flyrank_Backend_Tasks`.
4. Set the **Base directory** to `Personal Website Live on the FlyRank Domain` and **Publish directory** to `.`.
5. Netlify will deploy automatically on every `git push`.
6. Go to **Site configuration &rarr; Change site name** and rename to `aditya-rajput-backend`.

---

## 4. DNS Walkthrough Highlights

The complete DNS guide is available in [`dns-walkthrough.md`](dns-walkthrough.md). Key takeaways include:

1. **What DNS Does:** Acts as the Internet’s phonebook, translating human-friendly domain names (`aditya-rajput-backend.netlify.app`) into machine-readable IP addresses (`75.2.60.5`).
2. **The 4-Step Resolution Flow:**
   - **Recursive Resolver:** The local courier (ISP or Cloudflare `1.1.1.1`) querying on your behalf.
   - **Root Server (`.`):** Directs the resolver to the responsible Top-Level Domain server (`.app`).
   - **TLD Server (`.app`):** Directs the resolver to Netlify’s authoritative nameservers (`ns1.netlify.com`).
   - **Authoritative Nameserver:** Holds the official zone file and provides the final IP address.
3. **What a CNAME Record Is:** A canonical alias record that maps one domain name to another domain name (`www.aditya.com &rarr; aditya-rajput-backend.netlify.app`). This allows cloud platforms like Netlify and Vercel to route traffic across distributed multi-region CDNs and provision automatic SSL/TLS certificates without exposing individual server IPs.

---

## 5. Evaluation Criteria Alignment

| Requirement | Evidence in Deliverable | Status |
|---|---|---|
| Site live & loading over HTTPS | Hand-crafted HTML5/CSS3 deployed with TLS 1.3 certificate on Netlify | **Pass** |
| Clean, professional URL | Configured as `aditya-rajput-backend.netlify.app` | **Pass** |
| Working links to LinkedIn, GitHub, CV, Booking | All 4 channels placed prominently in navigation, hero, and contact section | **Pass** |
| DNS walkthrough in own words | Documented in [`dns-walkthrough.md`](dns-walkthrough.md) and featured in web UI | **Pass** |
| Explain every deployed file | Detailed file table provided in Section 2 of this README | **Pass** |
| Space reserved for FlyRank Completion Badge | Dedicated badge component placed in `#badge` section | **Pass** |
