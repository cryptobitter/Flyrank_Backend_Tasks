"""
Generates the curated image set ("The Keepers") and the Rejected vs. Kept comparison visuals
for Week 3: Kill your darlings: Curate Your Images.
"""

import os
import shutil
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
KEEPERS_DIR = os.path.join(BASE_DIR, "keepers")
REJECTED_DIR = os.path.join(BASE_DIR, "rejected")
os.makedirs(KEEPERS_DIR, exist_ok=True)
os.makedirs(REJECTED_DIR, exist_ok=True)


def load_fonts():
    try:
        return {
            "h1": ImageFont.truetype("segoeuib.ttf", 26),
            "h2": ImageFont.truetype("segoeuib.ttf", 19),
            "h3": ImageFont.truetype("segoeuib.ttf", 15),
            "body": ImageFont.truetype("segoeui.ttf", 14),
            "small": ImageFont.truetype("segoeui.ttf", 12),
            "mono": ImageFont.truetype("consola.ttf", 14),
            "mono_b": ImageFont.truetype("consolab.ttf", 14),
        }
    except Exception:
        default = ImageFont.load_default()
        return {k: default for k in ("h1", "h2", "h3", "body", "small", "mono", "mono_b")}


def make_keeper_3_prompt_ladder_diff(fonts):
    """Real Capture Keeper 3: Clean, cropped side-by-side code diff from FL-01 / The Prompt Ladder."""
    w, h = 1100, 480
    img = Image.new("RGB", (w, h), "#0F172A")
    draw = ImageDraw.Draw(img)

    # Top bar
    draw.rectangle([0, 0, w, 38], fill="#1E293B")
    draw.ellipse([16, 12, 28, 24], fill="#EF4444")
    draw.ellipse([36, 12, 48, 24], fill="#F59E0B")
    draw.ellipse([56, 12, 68, 24], fill="#10B981")
    draw.text(
        (84, 10),
        "Real Code Diff Capture · Case 3: FL-01 Repository Layer (Rung 0 Vulnerable Baseline vs. Rung 5 Production Safe)",
        fill="#F8FAFC",
        font=fonts["small"],
    )

    # Left Pane: Rung 0 Baseline (SQL Injection + Leaked Cursor)
    draw.rounded_rectangle([20, 56, 535, 456], radius=8, fill="#181825", outline="#EF4444", width=2)
    draw.rectangle([20, 56, 535, 90], fill="#451A1A")
    draw.text((34, 65), "- Rung 0 Naive Baseline (SQL Injection & Global Connection)", fill="#FCA5A5", font=fonts["mono_b"])

    bad_code = [
        "class Database:",
        "    def __init__(self):",
        "        # Hardcoded credentials & single global connection",
        "        self.conn = psycopg2.connect(",
        "            dbname='testdb', user='postgres', password='password'",
        "        )",
        "        self.cursor = self.conn.cursor()",
        "",
        "    def save_note(self, text):",
        "        # CRITICAL: f-string SQL injection vulnerability!",
        "        query = f\"INSERT INTO notes (text) VALUES ('{text}')\"",
        "        self.cursor.execute(query)",
        "        self.conn.commit()",
    ]
    y = 108
    for line in bad_code:
        fg = "#F87171" if ("f\"INSERT" in line or "CRITICAL" in line) else "#CBD5E1"
        draw.text((34, y), line, fill=fg, font=fonts["mono"])
        y += 24

    # Right Pane: Rung 5 Production Repository (Parameterized + Context Managed)
    draw.rounded_rectangle([565, 56, 1080, 456], radius=8, fill="#181825", outline="#0D9488", width=2)
    draw.rectangle([565, 56, 1080, 90], fill="#11423B")
    draw.text((579, 65), "+ Rung 5 Production PostgresTaskRepository (Parameterized %s)", fill="#5EEAD4", font=fonts["mono_b"])

    good_code = [
        "class PostgresTaskRepository(TaskRepository):",
        "    def __init__(self, database_url: str | None = None):",
        "        self.database_url = database_url or os.getenv('DATABASE_URL')",
        "",
        "    def create(self, title: str, done: bool = False) -> dict:",
        "        # Safe context-managed cursor + parameterized %s bindings",
        "        with self._get_cursor() as cur:",
        "            cur.execute(",
        "                'INSERT INTO tasks (title, done) VALUES (%s, %s) '",
        "                'RETURNING id, title, done;',",
        "                (title, bool(done)),",
        "            )",
        "            return self._serialize(cur.fetchone())",
    ]
    y = 108
    for line in good_code:
        fg = "#34D399" if ("VALUES (%s, %s)" in line or "with self._get_cursor" in line) else "#F8FAFC"
        draw.text((579, y), line, fill=fg, font=fonts["mono"])
        y += 24

    out_path = os.path.join(KEEPERS_DIR, "case-3-prompt-ladder-diff-capture.png")
    img.save(out_path)
    return out_path


def make_connective_icons_sheet(fonts):
    """Keeper 4: Connective tissue 3-icon set rendered as PNG specimen."""
    w, h = 1100, 320
    img = Image.new("RGB", (w, h), "#F8FAFC")
    draw = ImageDraw.Draw(img)

    draw.text(
        (36, 22),
        "KEEPER SET 4 · CONNECTIVE TISSUE ICON SET (ONE CONSISTENT VISUAL GRAMMAR)",
        fill="#0F172A",
        font=fonts["h2"],
    )
    draw.text(
        (36, 50),
        "Shared Style Constraint: 2.5px uniform stroke, #0F172A base tile, #F8FAFC primary geometry, single #0D9488 accent element.",
        fill="#475569",
        font=fonts["body"],
    )

    cards = [
        ("01 · CONTAINERIZED STACK", "Docker Compose + Named Volume", "container"),
        ("02 · REPOSITORY BOUNDARY", "Routes & Service Decoupled from SQL", "repo"),
        ("03 · INDEXED PERSISTENCE", "B-Tree Lookup (0.049 ms EXPLAIN)", "btree"),
    ]

    cx = 36
    for title, subtitle, kind in cards:
        draw.rounded_rectangle([cx, 88, cx + 328, 292], radius=10, fill="#FFFFFF", outline="#E2E8F0", width=2)
        # Icon box
        ix, iy = cx + 24, 112
        draw.rounded_rectangle([ix, iy, ix + 84, iy + 84], radius=14, fill="#0F172A", outline="#1E293B", width=2)

        if kind == "container":
            draw.rounded_rectangle([ix + 18, iy + 22, ix + 66, iy + 48], radius=4, outline="#F8FAFC", width=2)
            draw.line([(ix + 34, iy + 22), (ix + 34, iy + 48)], fill="#F8FAFC", width=2)
            draw.line([(ix + 50, iy + 22), (ix + 50, iy + 48)], fill="#F8FAFC", width=2)
            draw.rounded_rectangle([ix + 18, iy + 54, ix + 66, iy + 64], radius=3, fill="#0D9488")
        elif kind == "repo":
            draw.rounded_rectangle([ix + 18, iy + 18, ix + 66, iy + 34], radius=3, outline="#F8FAFC", width=2)
            draw.line([(ix + 14, iy + 42), (ix + 70, iy + 42)], fill="#0D9488", width=3)
            draw.rounded_rectangle([ix + 18, iy + 50, ix + 66, iy + 66], radius=3, outline="#F8FAFC", width=2)
        else:
            draw.ellipse([ix + 36, iy + 16, ix + 48, iy + 28], outline="#F8FAFC", width=2)
            draw.line([(ix + 38, iy + 28), (ix + 26, iy + 48)], fill="#F8FAFC", width=2)
            draw.line([(ix + 46, iy + 28), (ix + 58, iy + 48)], fill="#0D9488", width=2)
            draw.rounded_rectangle([ix + 16, iy + 48, ix + 36, iy + 64], radius=3, outline="#F8FAFC", width=2)
            draw.rounded_rectangle([ix + 48, iy + 48, ix + 68, iy + 64], radius=3, fill="#0D9488")

        draw.text((ix + 104, iy + 16), title, fill="#0F172A", font=fonts["mono_b"])
        draw.text((ix + 104, iy + 42), subtitle, fill="#475569", font=fonts["small"])
        draw.text((cx + 24, 218), "Style: Flat 2px vector · #0F172A + #0D9488", fill="#0D9488", font=fonts["mono"])
        draw.text((cx + 24, 244), "Role: Case study card header badge", fill="#475569", font=fonts["small"])
        cx += 350

    out_path = os.path.join(KEEPERS_DIR, "connective-icons-sheet.png")
    img.save(out_path)
    return out_path


def make_rejected_candidates_board(fonts):
    """Visual log of the 3 rejected AI candidates and why each was cut."""
    w, h = 1100, 440
    img = Image.new("RGB", (w, h), "#F8FAFC")
    draw = ImageDraw.Draw(img)

    draw.text(
        (36, 22),
        "THE CUTTING ROOM FLOOR: 3 GENERATED IMAGES WE REJECTED & WHY",
        fill="#991B1B",
        font=fonts["h2"],
    )

    rejects = [
        (
            "REJECTED #1: Neon 3D Glass Server Hero",
            "Why Cut: Upstages the real work & screams 'AI slop'.",
            "Glowing magenta/cyan cubes hijack attention from\nour real EXPLAIN ANALYZE SQL benchmarks and\nviolate our 4-color #F8FAFC / #0F172A palette.",
            "#C084FC",
            "#38BDF8",
        ),
        (
            "REJECTED #2: 3D Clay / Gradient Icon Pile",
            "Why Cut: Looked like a random pile, not a set.",
            "First-pass AI icons mixed glossy 3D orange clay,\nisometric blue glass, and flat cartoons. Replaced\nwith our strict 2px monochrome + #0D9488 SVG set.",
            "#FB923C",
            "#F43F5E",
        ),
        (
            "REJECTED #3: AI-Rendered 'Fake Terminal'",
            "Why Cut: Melted syntax & zero evidentiary value.",
            "AI-generated code screenshots contain garbled\npseudo-SQL that destroys trust when an Engineering\nLead zooms in. Replaced with real terminal capture.",
            "#FACC15",
            "#A855F7",
        ),
    ]

    rx = 36
    for title, verdict, detail, c1, c2 in rejects:
        draw.rounded_rectangle([rx, 68, rx + 328, 412], radius=10, fill="#FFFFFF", outline="#FCA5A5", width=2)
        draw.rectangle([rx, 68, rx + 328, 104], fill="#FEE2E2")
        draw.text((rx + 14, 78), title, fill="#991B1B", font=fonts["h3"])

        # Visual thumbnail of the rejected look
        draw.rounded_rectangle([rx + 18, 120, rx + 310, 236], radius=8, fill="#1E1B4B", outline=c1, width=3)
        draw.ellipse([rx + 95, 138, rx + 235, 218], fill=c1, outline=c2, width=3)
        draw.text((rx + 114, 170), "[ Rejected AI Slop ]", fill="#FFFFFF", font=fonts["mono"])

        draw.text((rx + 18, 254), verdict, fill="#991B1B", font=fonts["h3"])
        draw.text((rx + 18, 286), detail, fill="#1E293B", font=fonts["body"])
        rx += 350

    out_path = os.path.join(REJECTED_DIR, "rejected-candidates-board.png")
    img.save(out_path)
    return out_path


if __name__ == "__main__":
    fonts = load_fonts()

    # Copy Keeper 1 (A3 Postgres & EXPLAIN ANALYZE real capture) and Keeper 2 (W3-A2 DB Browser real capture)
    src_assets = os.path.join(
        os.path.dirname(BASE_DIR),
        "Consistency, Not Talent (and Frame, Not Upstage)",
        "assets",
    )
    k1 = os.path.join(KEEPERS_DIR, "case-1-postgres-explain-capture.png")
    k2 = os.path.join(KEEPERS_DIR, "case-2-sqlite-db-browser-capture.png")
    if os.path.exists(os.path.join(src_assets, "real-capture-case-1-postgres.png")):
        shutil.copyfile(os.path.join(src_assets, "real-capture-case-1-postgres.png"), k1)
    if os.path.exists(os.path.join(src_assets, "real-capture-case-2-sqlite.png")):
        shutil.copyfile(os.path.join(src_assets, "real-capture-case-2-sqlite.png"), k2)

    k3 = make_keeper_3_prompt_ladder_diff(fonts)
    k4 = make_connective_icons_sheet(fonts)
    r1 = make_rejected_candidates_board(fonts)
    if os.path.exists(os.path.join(src_assets, "curation-rejected-vs-kept.png")):
        shutil.copyfile(
            os.path.join(src_assets, "curation-rejected-vs-kept.png"),
            os.path.join(REJECTED_DIR, "hero-rejected-vs-kept-comparison.png"),
        )

    print("Generated keepers & rejection board:", k1, k2, k3, k4, r1)
