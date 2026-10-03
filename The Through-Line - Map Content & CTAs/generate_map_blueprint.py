"""
Generates the visual Content Map & CTA Ladder Blueprint (content-map-blueprint.png)
for Week 3: The Through-Line: Map Content & CTAs.
"""

import os
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def load_fonts():
    try:
        return {
            "h1": ImageFont.truetype("segoeuib.ttf", 24),
            "h2": ImageFont.truetype("segoeuib.ttf", 17),
            "h3": ImageFont.truetype("segoeuib.ttf", 14),
            "body": ImageFont.truetype("segoeui.ttf", 13),
            "small": ImageFont.truetype("segoeui.ttf", 12),
            "mono": ImageFont.truetype("consola.ttf", 13),
            "mono_b": ImageFont.truetype("consolab.ttf", 13),
        }
    except Exception:
        default = ImageFont.load_default()
        return {k: default for k in ("h1", "h2", "h3", "body", "small", "mono", "mono_b")}


def generate_blueprint():
    fonts = load_fonts()
    w, h = 1200, 740
    img = Image.new("RGB", (w, h), "#F8FAFC")
    draw = ImageDraw.Draw(img)

    # Top Header: One-Line Claim
    draw.rectangle([0, 0, w, 104], fill="#0F172A")
    draw.text(
        (36, 18),
        "THE THROUGH-LINE · CONTENT MAP & CTA LADDER BLUEPRINT",
        fill="#0D9488",
        font=fonts["mono_b"],
    )
    draw.text(
        (36, 44),
        "One-Line Claim: \"I build containerized Python backends where routes stay five lines long and data survives any restart.\"",
        fill="#F8FAFC",
        font=fonts["h2"],
    )
    draw.text(
        (36, 74),
        "Target Audience: Engineering Lead / Technical Founder at an early-stage B2B SaaS startup",
        fill="#94A3B8",
        font=fonts["body"],
    )

    # 3 Page Columns
    pages = [
        (
            "PAGE 1: HOME (/) — Proof Overview",
            [
                ("1. Hero Banner", "One-line claim + target audience subhead", "CTA: Inspect the Live Architecture ↓"),
                ("2. Lead Case (Strongest): A3 Stack", "Docker + Postgres Volume + Redis + 37.6x EXPLAIN", "CTA: Read Case 1 & View Diff →"),
                ("3. Secondary Case: W3-A2 SQLite", "Memory-to-SQLite swap + identical A1 tests pass", "CTA: Read Case 2 & SQL Proof →"),
                ("4. Case 3: FL-01 Prompt Ladder", "Rung 0 SQLi fix -> Rung 5 safe cursor context", "CTA: Inspect 6-Rung Audit →"),
                ("5. Direct Conversion Footer", "Restates claim + zero-friction calendar link", "PRIMARY CTA: Book 15-Min Walkthrough →"),
            ],
        ),
        (
            "PAGE 2: CASE DEEP-DIVES (/cases)",
            [
                ("1. Case 1 Three-Beat Breakdown", "Problem -> Repository Decision -> 1-file swap", "CTA: View A3 Source on GitHub ↗"),
                ("2. EXPLAIN ANALYZE Benchmark", "10,000 rows: 1.842ms Seq Scan -> 0.049ms Index", "CTA: Run benchmark_index.sql ↗"),
                ("3. Case 2 Three-Beat Breakdown", "SQLite persistence across restarts + DB Browser", "CTA: View W3-A2 Source on GitHub ↗"),
                ("4. Contract Proof (test_api.py)", "Proves storage is an implementation detail", "CTA: Inspect pytest Suite ↗"),
                ("5. Walkthrough Conversion Block", "Invite lead to inspect live containers together", "PRIMARY CTA: Book 15-Min Walkthrough →"),
            ],
        ),
        (
            "PAGE 3: ABOUT & STANDARDS (/about)",
            [
                ("1. Engineer Bio & Real Photo", "Voice card bio (direct, plain, no buzzwords)", "CTA: Jump to Calendar Slot ↓"),
                ("2. Production Readiness Checklist", "Parameterized SQL, transactions, healthchecks", "CTA: See Verification Rules →"),
                ("3. How I Work with AI", "Specification-driven prompting + code review", "CTA: View AI vs. Me Diff →"),
                ("4. Upcoming Pipeline (W4–W8)", "Redis jobs/caching & live cloud deployment", "CTA: Follow Repo Commits ↗"),
                ("5. Embedded Calendar Booking", "Direct 15-minute slot picker (zero email ping-pong)", "PRIMARY CTA: Confirm 15-Min Walkthrough →"),
            ],
        ),
    ]

    px = 32
    col_w = 364
    for page_title, sections in pages:
        draw.rounded_rectangle([px, 124, px + col_w, 596], radius=10, fill="#FFFFFF", outline="#CBD5E1", width=2)
        draw.rectangle([px, 124, px + col_w, 162], fill="#1E293B")
        draw.text((px + 16, 134), page_title, fill="#F8FAFC", font=fonts["h3"])

        sy = 176
        for sec_title, sec_desc, sec_cta in sections:
            is_primary = "PRIMARY CTA" in sec_cta
            box_bg = "#F0FDFA" if is_primary else "#F8FAFC"
            box_border = "#0D9488" if is_primary else "#E2E8F0"
            draw.rounded_rectangle([px + 14, sy, px + col_w - 14, sy + 74], radius=6, fill=box_bg, outline=box_border, width=2 if is_primary else 1)
            draw.text((px + 24, sy + 8), sec_title, fill="#0F172A", font=fonts["h3"])
            draw.text((px + 24, sy + 28), sec_desc, fill="#475569", font=fonts["small"])
            cta_color = "#0D9488" if is_primary else "#1E293B"
            draw.text((px + 24, sy + 48), sec_cta, fill=cta_color, font=fonts["mono_b" if is_primary else "mono"])
            sy += 82

        px += col_w + 22

    # Bottom Funnel Bar: Laddering Up to the Week 1 Single Action
    draw.rounded_rectangle([32, 616, w - 32, 714], radius=10, fill="#0F172A", outline="#0D9488", width=2)
    draw.text(
        (54, 632),
        "ALL PAGE CTAs LADDER UP TO THE SINGLE WEEK 1 CONVERSION ACTION:",
        fill="#5EEAD4",
        font=fonts["mono_b"],
    )
    draw.text(
        (54, 660),
        "Book a 15-minute technical walkthrough call on my calendar (to inspect the live Docker + PostgreSQL architecture together).",
        fill="#F8FAFC",
        font=fonts["h2"],
    )

    out_path = os.path.join(BASE_DIR, "content-map-blueprint.png")
    img.save(out_path)
    return out_path


if __name__ == "__main__":
    print("Generated:", generate_blueprint())
