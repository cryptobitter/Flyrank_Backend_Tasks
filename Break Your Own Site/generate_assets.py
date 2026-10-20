"""
Asset Generator for Week 09 Break Your Own Site
Generates:
1. og-preview.png (1200x630 Open Graph / Twitter Card social preview)
2. break-test-and-hardening-matrix.png (Infographic of adversarial testing and hardening triage)
"""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


def render_og_preview(output_paths: list):
    """Renders 1200x630 Open Graph / Twitter Card social share preview."""
    width, height = 1200, 630
    img = Image.new("RGB", (width, height), color=(15, 23, 42))  # #0F172A Slate 900
    draw = ImageDraw.Draw(img)

    # Decorative background grid / borders
    draw.rectangle([(20, 20), (width - 20, height - 20)], outline=(30, 41, 59), width=2)
    draw.rectangle([(40, 40), (width - 40, height - 40)], outline=(13, 148, 136), width=1)

    # Accent decorative gradient bar on top
    draw.rectangle([(40, 40), (width - 40, 48)], fill=(13, 148, 136))

    # Fonts
    try:
        font_eyebrow = ImageFont.truetype("consolab.ttf", 20)
        font_name = ImageFont.truetype("consolab.ttf", 46)
        font_title = ImageFont.truetype("consolab.ttf", 32)
        font_sub = ImageFont.truetype("consola.ttf", 22)
        font_tag = ImageFont.truetype("consolab.ttf", 16)
        font_badge = ImageFont.truetype("consola.ttf", 15)
    except Exception:
        font_eyebrow = ImageFont.load_default()
        font_name = font_eyebrow
        font_title = font_eyebrow
        font_sub = font_eyebrow
        font_tag = font_eyebrow
        font_badge = font_eyebrow

    # Terminal Brand Mark
    draw.rectangle([(80, 80), (140, 140)], fill=(30, 41, 59), outline=(13, 148, 136), width=2)
    draw.text((95, 90), ">_", fill=(45, 212, 191), font=font_title)

    # Eyebrow
    draw.text((160, 95), "BACKEND & API SYSTEMS ARCHITECTURE", fill=(13, 148, 136), font=font_eyebrow)

    # Name & Handle
    draw.text((80, 170), "Aditya Rajput", fill=(248, 250, 252), font=font_name)
    draw.text((450, 185), "(@cryptobitter)", fill=(148, 163, 184), font=font_sub)

    # Value Proposition
    lead_text_1 = "I build containerized Python backends where routes stay five lines long"
    lead_text_2 = "and data survives any restart."
    draw.text((80, 245), lead_text_1, fill=(226, 232, 240), font=font_title)
    draw.text((80, 290), lead_text_2, fill=(45, 212, 191), font=font_title)

    # Technical Case Studies Card
    card_x, card_y, card_w, card_h = 80, 360, 1040, 150
    draw.rectangle([(card_x, card_y), (card_x + card_w, card_y + card_h)], fill=(30, 41, 59), outline=(51, 65, 85), width=1)

    # Beats proof badges inside card
    draw.text((110, 385), "$ proof: 2.410ms -> 0.089ms (27x EXPLAIN ANALYZE Speedup on 10,000 Tasks)", fill=(56, 189, 248), font=font_sub)
    draw.text((110, 425), "$ stack: FastAPI + PostgreSQL 16 + Redis 7 + Supabase JWT Middleware", fill=(226, 232, 240), font=font_sub)
    draw.text((110, 465), "$ scout: Autonomous Python PR Scout Agent + Model Context Protocol (MCP)", fill=(168, 85, 247), font=font_sub)

    # Bottom Pill Badges
    pills = [
        "Python 3.12",
        "FastAPI",
        "PostgreSQL 16",
        "Redis",
        "Docker Compose",
        "MCP Protocol",
        "Live Form Wired",
        "WCAG AAA"
    ]
    px = 80
    for p in pills:
        pill_w = len(p) * 11 + 20
        draw.rectangle([(px, 540), (px + pill_w, 575)], fill=(2, 6, 23), outline=(13, 148, 136), width=1)
        draw.text((px + 10, 548), p, fill=(45, 212, 191), font=font_tag)
        px += pill_w + 12

    for p in output_paths:
        img.save(str(p), format="PNG")
        print(f"[SAVED] Rendered {p.name}")


def render_break_matrix(output_path: Path):
    """Renders comprehensive break test results and triage infographic."""
    width, height = 1200, 800
    img = Image.new("RGB", (width, height), color=(15, 23, 42))  # Slate 900
    draw = ImageDraw.Draw(img)

    try:
        font_header = ImageFont.truetype("consolab.ttf", 22)
        font_bold = ImageFont.truetype("consolab.ttf", 16)
        font_body = ImageFont.truetype("consola.ttf", 14)
        font_small = ImageFont.truetype("consola.ttf", 12)
    except Exception:
        font_header = ImageFont.load_default()
        font_bold = font_header
        font_body = font_header
        font_small = font_header

    # Window title bar
    draw.rectangle([(0, 0), (width, 60)], fill=(30, 41, 59))
    draw.ellipse([(20, 22), (36, 38)], fill=(239, 68, 68))
    draw.ellipse([(44, 22), (60, 38)], fill=(245, 158, 11))
    draw.ellipse([(68, 22), (84, 38)], fill=(16, 185, 129))
    draw.text((110, 20), "Week 09: Break Your Own Site · Stress Test & Hardening Triage Matrix", fill=(241, 245, 249), font=font_header)

    # Section 1: Break Tests (Left Column)
    draw.rectangle([(30, 80), (580, 760)], fill=(2, 6, 23), outline=(51, 65, 85), width=1)
    draw.rectangle([(30, 80), (580, 120)], fill=(30, 41, 59))
    draw.text((45, 92), "1. ADVERSARIAL EDGE CASE BREAK TESTS", fill=(244, 114, 182), font=font_bold)

    tests = [
        ("Test 01 · Empty & Whitespace Submit", "FAIL INITIALLY", "PASSED", "Form caught whitespace-only; inline alert displayed without refresh."),
        ("Test 02 · Double Submit (Rapid Click)", "VULNERABLE", "PASSED", "Atomic isSubmitting lock added; button disables in 0ms."),
        ("Test 03 · XSS Injection (<script>)", "RISK", "PASSED", "DOM uses textContent exclusively; zero script execution possible."),
        ("Test 04 · 50KB Buffer Overflow", "PAYLOAD BLOAT", "PASSED", "Strict maxlength (100 name, 254 email, 2000 msg) enforced."),
        ("Test 05 · Invalid Email Formats", "PARTIAL", "PASSED", "RFC 5322 regex validation prevents malformed domain submissions."),
        ("Test 06 · Link & Asset 404 Audit", "CLEAN", "PASSED", "100% internal anchors and external GitHub links verified active."),
        ("Test 07 · Screen Resizing (320px-4K)", "TEXT OVERFLOW", "PASSED", "Fluid clamp() & safe margin padding eliminates horizontal scroll."),
        ("Test 08 · SEO Meta & Social Cards", "MISSING OG", "PASSED", "Complete Open Graph, Twitter Cards, Canonical & JSON-LD added.")
    ]

    y = 135
    for title, before, after, desc in tests:
        draw.text((45, y), title, fill=(248, 250, 252), font=font_bold)
        draw.rectangle([(420, y - 2), (480, y + 16)], fill=(127, 29, 29))
        draw.text((425, y), before[:7], fill=(254, 202, 202), font=font_small)

        draw.rectangle([(495, y - 2), (565, y + 16)], fill=(6, 78, 59))
        draw.text((505, y), after, fill=(167, 243, 208), font=font_small)

        draw.text((45, y + 20), desc, fill=(148, 163, 184), font=font_small)
        y += 55
        draw.line([(45, y - 10), (565, y - 10)], fill=(30, 41, 59), width=1)

    # Section 2: Hardening Triage Matrix (Right Column)
    draw.rectangle([(620, 80), (1170, 760)], fill=(2, 6, 23), outline=(51, 65, 85), width=1)
    draw.rectangle([(620, 80), (1170, 120)], fill=(30, 41, 59))
    draw.text((635, 92), "2. HARDENING TRIAGE: FIX-NOWS VS LIMITATIONS", fill=(56, 189, 248), font=font_bold)

    y = 135
    draw.text((635, y), "[FIX-NOWS: 100% RESOLVED IN CODE]", fill=(52, 211, 153), font=font_bold)
    y += 28

    fix_nows = [
        ("FN-1: Debounce Race Condition", "Added atomic 'isSubmitting' mutex lock in submit listener."),
        ("FN-2: Form Input Truncation", "Bounded name (100), email (254), message (2000) chars."),
        ("FN-3: Complete SEO & Meta", "Added Open Graph, Twitter Card, Canonical URL, Robots."),
        ("FN-4: Schema.org Structured Data", "Embedded JSON-LD Person & WebSite schema for search."),
        ("FN-5: Font Display Optimization", "Added 'display=swap' to Google Fonts to prevent FOIT.")
    ]
    for fn_title, fn_desc in fix_nows:
        draw.text((635, y), f"✓ {fn_title}", fill=(241, 245, 249), font=font_bold)
        draw.text((655, y + 18), fn_desc, fill=(148, 163, 184), font=font_small)
        y += 42

    y += 15
    draw.line([(635, y), (1155, y)], fill=(51, 65, 85), width=1)
    y += 15

    draw.text((635, y), "[KNOWN LIMITATIONS: NAMED & DOCUMENTED]", fill=(250, 204, 21), font=font_bold)
    y += 28

    limitations = [
        ("KL-1: Formsubmit Gateway Latency (1.5-3.0s)", "Free tier external API transit latency. Documented with friendly spinner."),
        ("KL-2: Static Client-Side Processing", "GitHub Pages static hosting cannot run Python backend directly on edge."),
        ("KL-3: Free-Tier Rate Limits (50 msgs/month)", "Adequate for portfolio leads; high-volume SaaS requires paid SendGrid."),
        ("KL-4: Offline Submission Queueing", "Browsers without connection cannot queue offline; fallback mailto provided.")
    ]
    for kl_title, kl_desc in limitations:
        draw.text((635, y), f"⚠ {kl_title}", fill=(254, 240, 138), font=font_bold)
        draw.text((655, y + 18), kl_desc, fill=(148, 163, 184), font=font_small)
        y += 42

    img.save(str(output_path), format="PNG")
    print(f"[SAVED] Rendered {output_path.name}")


if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parent
    root_dir = base_dir.parent

    # Render og-preview in both Break Your Own Site and root directory for index.html
    og_paths = [base_dir / "og-preview.png", root_dir / "og-preview.png"]
    render_og_preview(og_paths)

    # Render break matrix infographic
    matrix_path = base_dir / "break-test-and-hardening-matrix.png"
    render_break_matrix(matrix_path)
