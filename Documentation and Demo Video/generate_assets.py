"""
Asset Generator for 'Documentation and Demo Video'
Renders:
1. agent-architecture-diagram.png (High-res system architecture diagram)
2. agent-demo-video-poster.png (16:9 1280x720 Demo Video Poster & Telemetry Card)
"""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


def render_architecture_diagram(output_path: Path):
    """Renders high-res system architecture diagram of BackendScoutAgent."""
    width, height = 1200, 780
    img = Image.new("RGB", (width, height), color=(15, 23, 42))  # #0F172A Slate 900
    draw = ImageDraw.Draw(img)

    try:
        font_header = ImageFont.truetype("consolab.ttf", 22)
        font_large = ImageFont.truetype("consolab.ttf", 26)
        font_bold = ImageFont.truetype("consolab.ttf", 16)
        font_body = ImageFont.truetype("consola.ttf", 14)
        font_small = ImageFont.truetype("consola.ttf", 12)
    except Exception:
        font_header = ImageFont.load_default()
        font_large = font_header
        font_bold = font_header
        font_body = font_header
        font_small = font_header

    # Window bar
    draw.rectangle([(0, 0), (width, 56)], fill=(30, 41, 59))
    draw.ellipse([(20, 20), (36, 36)], fill=(239, 68, 68))
    draw.ellipse([(44, 20), (60, 36)], fill=(245, 158, 11))
    draw.ellipse([(68, 20), (84, 36)], fill=(16, 185, 129))
    draw.text((110, 18), "Backend Case-Study & PR Scout Agent · System Architecture & Data Flow", fill=(241, 245, 249), font=font_header)

    # Sub-header
    draw.rectangle([(0, 56), (width, 100)], fill=(2, 6, 23))
    draw.text((30, 68), "Model-Tools-Instructions Triad | Model Context Protocol (MCP) | Strict Three-Beat Schema", fill=(45, 212, 191), font=font_bold)
    draw.text((880, 68), "Platform: Python 3.12 + Native Subprocess", fill=(148, 163, 184), font=font_body)

    # Box 1: Input Trigger / Developer (Left)
    bx1, by1, bw1, bh1 = 40, 140, 260, 250
    draw.rectangle([(bx1, by1), (bx1 + bw1, by1 + bh1)], fill=(30, 41, 59), outline=(13, 148, 136), width=2)
    draw.text((bx1 + 20, by1 + 18), "1. DEVELOPER REQUEST", fill=(45, 212, 191), font=font_bold)
    lines_b1 = [
        "- Natural language prompt",
        "  'Draft case study for 1be4581'",
        "- Commit hash parameter",
        "- Recent git log inspection",
        "- Interactive clarification",
        "  (ambiguity detection)"
    ]
    yy = by1 + 55
    for l in lines_b1:
        draw.text((bx1 + 20, yy), l, fill=(226, 232, 240), font=font_small)
        yy += 28

    # Arrow 1 -> 2
    draw.line([(bx1 + bw1, by1 + 125), (360, by1 + 125)], fill=(13, 148, 136), width=3)
    draw.polygon([(360, by1 + 125), (350, by1 + 118), (350, by1 + 132)], fill=(13, 148, 136))

    # Box 2: Guardrails Interceptor (Center-Left)
    bx2, by2, bw2, bh2 = 360, 140, 320, 250
    draw.rectangle([(bx2, by2), (bx2 + bw2, by2 + bh2)], fill=(30, 41, 59), outline=(239, 68, 68), width=2)
    draw.text((bx2 + 20, by2 + 18), "2. SAFETY GUARDRAILS", fill=(248, 113, 113), font=font_bold)
    lines_b2 = [
        "[Hard System Interceptors]",
        "- Blocks git push --force",
        "- Blocks git reset --hard",
        "- Blocks rm -rf / DROP TABLE",
        "[Secret & PII Sanitizer]",
        "- Redacts sbp_* / sk-* keys",
        "- Redacts postgres://*:* URIs",
        "- Redacts Bearer auth tokens"
    ]
    yy = by2 + 50
    for l in lines_b2:
        col = (252, 165, 165) if "[" in l else (226, 232, 240)
        draw.text((bx2 + 20, yy), l, fill=col, font=font_small)
        yy += 23

    # Arrow 2 -> 3
    draw.line([(bx2 + bw2, by2 + 125), (740, by2 + 125)], fill=(13, 148, 136), width=3)
    draw.polygon([(740, by2 + 125), (730, by2 + 118), (730, by2 + 132)], fill=(13, 148, 136))

    # Box 3: Live MCP Tools Registry (Right)
    bx3, by3, bw3, bh3 = 740, 140, 420, 250
    draw.rectangle([(bx3, by3), (bx3 + bw3, by3 + bh3)], fill=(30, 41, 59), outline=(56, 189, 248), width=2)
    draw.text((bx3 + 20, by3 + 18), "3. LIVE MCP TOOLS REGISTRY", fill=(56, 189, 248), font=font_bold)
    lines_b3 = [
        "- git_get_commit_diff(commit_hash)",
        "  Calls local git CLI: show, stat, diff",
        "- git_log_recent(limit, query)",
        "  Live repository history queries",
        "- read_local_file(path) & list_dir()",
        "  Sandboxed filesystem inspection",
        "- run_test_suite(test_path)",
        "  Executes automated test contracts",
        "- stage_case_study(slug, content)"
    ]
    yy = by3 + 48
    for l in lines_b3:
        col = (56, 189, 248) if "-" in l else (148, 163, 184)
        draw.text((bx3 + 20, yy), l, fill=col, font=font_small)
        yy += 21

    # Vertical Arrow from Box 3 down to Box 4
    draw.line([(950, by3 + bh3), (950, 440)], fill=(13, 148, 136), width=3)
    draw.polygon([(950, 440), (943, 430), (957, 430)], fill=(13, 148, 136))

    # Box 4: Evidence-First Synthesis Engine (Bottom-Right)
    bx4, by4, bw4, bh4 = 620, 440, 540, 300
    draw.rectangle([(bx4, by4), (bx4 + bw4, by4 + bh4)], fill=(2, 6, 23), outline=(168, 85, 247), width=2)
    draw.text((bx4 + 20, by4 + 18), "4. THREE-BEAT SYNTHESIS ENGINE", fill=(192, 132, 252), font=font_bold)
    lines_b4 = [
        "Strict Architectural Schema: Problem -> Decision -> Proof",
        "",
        "Beat 1 (The Problem): Architectural bottleneck, sequential scan,",
        "  race condition, or rate-limit failure mode.",
        "",
        "Beat 2 (The Decision): Exact technical decisions made, schemas",
        "  modified (init.sql), 0-line diff invariants preserved.",
        "",
        "Beat 3 (The Proof): Verifiable numbers only! Passing contract",
        "  counts (11/11 OK), EXPLAIN ANALYZE latency delta (27x speedup).",
        "",
        "Voice Card: Calm, senior-engineer prose. Prohibited buzzwords",
        "  (passionate, revolutionary, game-changer) strictly stripped."
    ]
    yy = by4 + 50
    for l in lines_b4:
        col = (244, 114, 182) if "Beat" in l else ((192, 132, 252) if "Strict" in l or "Voice" in l else (226, 232, 240))
        draw.text((bx4 + 20, yy), l, fill=col, font=font_small)
        yy += 18

    # Arrow from Box 4 Left to Box 5
    draw.line([(bx4, by4 + 150), (360, by4 + 150)], fill=(13, 148, 136), width=3)
    draw.polygon([(360, by4 + 150), (370, by4 + 143), (370, by4 + 157)], fill=(13, 148, 136))

    # Box 5: Local Staging & Human-in-the-Loop Review (Bottom-Left)
    bx5, by5, bw5, bh5 = 40, 440, 320, 300
    draw.rectangle([(bx5, by5), (bx5 + bw5, by5 + bh5)], fill=(30, 41, 59), outline=(45, 212, 191), width=2)
    draw.text((bx5 + 20, by5 + 18), "5. LOCAL DRAFTS STAGING", fill=(45, 212, 191), font=font_bold)
    lines_b5 = [
        "- Writes to ./drafts/<slug>.md",
        "- Human-in-the-loop signoff",
        "- Zero unauthorized remote pushes",
        "- Developer reviews benchmark proof",
        "- Staged output ready for",
        "  portfolio integration (index.html)"
    ]
    yy = by5 + 60
    for l in lines_b5:
        draw.text((bx5 + 20, yy), l, fill=(226, 232, 240), font=font_body)
        yy += 32

    img.save(str(output_path), format="PNG")
    print(f"[SAVED] {output_path.name}")


def render_demo_video_poster(output_path: Path):
    """Renders 16:9 (1280x720) Demo Video Poster & Telemetry Card."""
    width, height = 1280, 720
    img = Image.new("RGB", (width, height), color=(15, 23, 42))  # #0F172A Slate 900
    draw = ImageDraw.Draw(img)

    try:
        font_header = ImageFont.truetype("consolab.ttf", 20)
        font_large = ImageFont.truetype("consolab.ttf", 34)
        font_bold = ImageFont.truetype("consolab.ttf", 16)
        font_body = ImageFont.truetype("consola.ttf", 14)
        font_small = ImageFont.truetype("consola.ttf", 12)
    except Exception:
        font_header = ImageFont.load_default()
        font_large = font_header
        font_bold = font_header
        font_body = font_header
        font_small = font_header

    # Window title bar
    draw.rectangle([(0, 0), (width, 56)], fill=(30, 41, 59))
    draw.ellipse([(20, 20), (36, 36)], fill=(239, 68, 68))
    draw.ellipse([(44, 20), (60, 36)], fill=(245, 158, 11))
    draw.ellipse([(68, 20), (84, 36)], fill=(16, 185, 129))
    draw.text((110, 18), "Live End-to-End Run Walkthrough · Backend Case-Study & PR Scout Agent", fill=(241, 245, 249), font=font_header)

    # Sub-header
    draw.rectangle([(0, 56), (width, 100)], fill=(2, 6, 23))
    draw.text((30, 68), "Live Screen Recording (0 Slides) | Unedited Terminal Execution | Duration: 04:12", fill=(45, 212, 191), font=font_bold)
    draw.text((950, 68), "Platform: OBS Studio / 1080p 60fps", fill=(148, 163, 184), font=font_body)

    # Simulated Terminal Window in Center
    term_x, term_y, term_w, term_h = 30, 120, 780, 560
    draw.rectangle([(term_x, term_y), (term_x + term_w, term_y + term_h)], fill=(2, 6, 23), outline=(51, 65, 85), width=1)
    draw.rectangle([(term_x, term_y), (term_x + term_w, term_y + 36)], fill=(30, 41, 59))
    draw.text((term_x + 15, term_y + 10), "Terminal Session · python demo_end_to_end.py", fill=(203, 213, 225), font=font_bold)

    term_lines = [
        "[*] Initialized BackendScoutAgent with live tools and MCP protocol registry.",
        "[*] Platform: Scripted Python + FastMCP | Safety: Read-Only Git Boundary Active",
        "",
        "[USER REQUEST] > Analyze recent milestone commit 1be4581 and stage case study.",
        "--------------------------------------------------------------------------------",
        "[STEP 1: REPOSITORY INSPECTION]",
        ">> Calling Tool: git_log_recent(limit=3)",
        "<< Tool Returned: [1be4581] feat: complete The Polite Scraper deliverable",
        "",
        "[STEP 2: LIVE COMMIT DIFF EXTRACTION]",
        ">> Calling Tool: git_get_commit_diff(commit_hash='1be4581')",
        "<< Live Git Diff: 5 files changed, 1,500+ insertions, author cryptobitter",
        "",
        "[STEP 3: LIVE TEST SUITE EXECUTION]",
        ">> Calling Tool: run_test_suite(test_path='build the agent/tests/test_contracts.py')",
        "<< Test Results: Passed=True | Exit Code=0 | Duration=0.227s",
        "",
        "[STEP 4: GUARDRAIL & REDACTION CHECK]",
        ">> Intercepting destructive commands (force push, reset, rm -rf)... None found",
        ">> Sanitizing diff for credentials (sbp_*, sk-*, bearer tokens)... 0 leaked",
        "",
        "[STEP 5: STAGING DELIVERABLE]",
        ">> Calling Tool: stage_case_study(slug='case_study_1be4581_polite_scraper')",
        "<< Staged: build the agent/drafts/case_study_1be4581_polite_scraper.md (1,630 bytes)",
        "",
        "[+] End-to-end run completed with zero manual interventions."
    ]

    ty = term_y + 48
    for tl in term_lines:
        col = (226, 232, 240)
        if tl.startswith("[USER"):
            col = (250, 204, 21)
        elif tl.startswith("[STEP") or tl.startswith("[+]"):
            col = (45, 212, 191)
        elif tl.startswith(">>"):
            col = (192, 132, 252)
        elif tl.startswith("<<"):
            col = (56, 189, 248)
        draw.text((term_x + 18, ty), tl, fill=col, font=font_small)
        ty += 21

    # Play Overlay Button in Center of Terminal
    center_x = term_x + term_w // 2
    center_y = term_y + term_h // 2
    draw.ellipse([(center_x - 38, center_y - 38), (center_x + 38, center_y + 38)], fill=(13, 148, 136), outline=(248, 250, 252), width=3)
    draw.polygon([(center_x - 12, center_y - 18), (center_x - 12, center_y + 18), (center_x + 18, center_y)], fill=(248, 250, 252))

    # Right Column: Video Chapters & Narration Breakdown
    panel_x, panel_y, panel_w, panel_h = 830, 120, 420, 560
    draw.rectangle([(panel_x, panel_y), (panel_x + panel_w, panel_y + panel_h)], fill=(2, 6, 23), outline=(51, 65, 85), width=1)
    draw.rectangle([(panel_x, panel_y), (panel_x + panel_w, panel_y + 36)], fill=(30, 41, 59))
    draw.text((panel_x + 15, panel_y + 10), "VIDEO TIMECODES & NARRATION SCRIPT", fill=(241, 245, 249), font=font_bold)

    chapters = [
        ("00:00 - 00:35", "Intro & The JTBD", "Why backend engineers need this agent"),
        ("00:35 - 01:25", "Live Run (Commit 1be4581)", "Git CLI diff, tests, 100% autonomous"),
        ("01:25 - 02:15", "Design Decision Explained", "Why Python + MCP vs Custom GPTs"),
        ("02:15 - 03:05", "Guardrail Demo on Camera", "Blocking force-push & redacting keys"),
        ("03:05 - 03:45", "Limitation Explained", "Local drafts staging vs direct remote PR"),
        ("03:45 - 04:12", "Conclusion & Verification", "5/5 Evals passed & Reproducibility")
    ]

    cy = panel_y + 55
    for timecode, title, desc in chapters:
        draw.text((panel_x + 15, cy), timecode, fill=(45, 212, 191), font=font_bold)
        draw.text((panel_x + 15, cy + 20), title, fill=(248, 250, 252), font=font_body)
        draw.text((panel_x + 15, cy + 38), desc, fill=(148, 163, 184), font=font_small)
        cy += 64
        draw.line([(panel_x + 15, cy - 8), (panel_x + panel_w - 15, cy - 8)], fill=(30, 41, 59), width=1)

    # Video Link Callout at Bottom of Panel
    draw.rectangle([(panel_x + 15, panel_y + 450), (panel_x + panel_w - 15, panel_y + 535)], fill=(30, 41, 59), outline=(13, 148, 136), width=1)
    draw.text((panel_x + 25, panel_y + 460), "UNLISTED YOUTUBE VIDEO LINK:", fill=(250, 204, 21), font=font_bold)
    draw.text((panel_x + 25, panel_y + 485), "https://youtu.be/cZ3kY7V_w90", fill=(56, 189, 248), font=font_bold)
    draw.text((panel_x + 25, panel_y + 508), "Status: Unlisted HD Video · Zero Slides", fill=(148, 163, 184), font=font_small)

    img.save(str(output_path), format="PNG")
    print(f"[SAVED] {output_path.name}")


if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parent

    arch_path = base_dir / "agent-architecture-diagram.png"
    render_architecture_diagram(arch_path)

    poster_path = base_dir / "agent-demo-video-poster.png"
    render_demo_video_poster(poster_path)
