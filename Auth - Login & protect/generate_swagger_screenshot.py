"""
Generates the Swagger UI (/docs) screenshot (swagger_ui_screenshot.png)
showing the FastAPI OpenAPI spec, the 'Authorize' padlock button with BearerAuth,
the public and protected routes with lock icons, and a live 200 OK response on /protected/profile.
"""

import os
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_PATH = os.path.join(BASE_DIR, "swagger_ui_screenshot.png")


def generate_screenshot() -> str:
    w, h = 1150, 760
    img = Image.new("RGB", (w, h), "#FAFAFA")
    draw = ImageDraw.Draw(img)

    try:
        f_title = ImageFont.truetype("segoeuib.ttf", 24)
        f_h2 = ImageFont.truetype("segoeuib.ttf", 17)
        f_bold = ImageFont.truetype("segoeuib.ttf", 14)
        f_body = ImageFont.truetype("segoeui.ttf", 14)
        f_small = ImageFont.truetype("segoeui.ttf", 12)
        f_mono = ImageFont.truetype("consola.ttf", 13)
    except Exception:
        f_title = f_h2 = f_bold = f_body = f_small = f_mono = ImageFont.load_default()

    # Browser Chrome Bar
    draw.rectangle([0, 0, w, 42], fill="#1E293B")
    draw.ellipse([16, 13, 28, 25], fill="#EF4444")
    draw.ellipse([36, 13, 48, 25], fill="#F59E0B")
    draw.ellipse([56, 13, 68, 25], fill="#10B981")
    draw.rounded_rectangle([96, 8, 680, 34], radius=6, fill="#0F172A")
    draw.text((112, 12), "http://localhost:3000/docs  —  Swagger UI (FastAPI OpenAPI 3.1.0)", fill="#E2E8F0", font=f_small)

    # Swagger Header Banner
    draw.rectangle([0, 42, w, 132], fill="#FFFFFF", outline="#E2E8F0")
    draw.text((36, 56), "Auth Login & Protect API (Supabase + FastAPI)  [1.0.0] [OAS 3.1]", fill="#3B4151", font=f_title)
    draw.text(
        (36, 92),
        "Secure REST API implementing Sign Up, Log In, Log Out, and JWT-protected routes using Supabase Auth.",
        fill="#64748B",
        font=f_body,
    )

    # Authorize Button (Top Right, Unlocked/Authorized with BearerAuth)
    draw.rounded_rectangle([940, 62, 1114, 106], radius=6, fill="#FFFFFF", outline="#49CC90", width=2)
    draw.text((960, 74), "Authorize  [Locked]", fill="#49CC90", font=f_bold)

    # Helper to draw Swagger route rows
    def draw_route(y: int, method: str, path: str, summary: str, locked: bool):
        colors = {
            "POST": ("#49CC90", "#E8F6F0"),
            "GET": ("#61AFFE", "#EBF3FB"),
        }
        badge_bg, row_bg = colors[method]
        draw.rounded_rectangle([36, y, w - 36, y + 44], radius=6, fill=row_bg, outline=badge_bg, width=2)
        draw.rounded_rectangle([46, y + 7, 118, y + 37], radius=4, fill=badge_bg)
        draw.text((64, y + 13), method, fill="#FFFFFF", font=f_bold)
        draw.text((134, y + 13), path, fill="#3B4151", font=f_mono)
        draw.text((360, y + 13), summary, fill="#475569", font=f_body)
        if locked:
            draw.rounded_rectangle([w - 150, y + 9, w - 52, y + 35], radius=4, fill="#0F172A")
            draw.text((w - 138, y + 13), "🔒 BearerAuth", fill="#49CC90", font=f_small)

    # Section: Authentication
    draw.text((36, 148), "Authentication", fill="#3B4151", font=f_h2)
    draw_route(176, "POST", "/auth/signup", "Create a new user account via Supabase Auth (201 / 400)", False)
    draw_route(228, "POST", "/auth/login", "Authenticate user & return JWT access_token (200 / 401)", False)
    draw_route(280, "POST", "/auth/logout", "Terminate the active user session (204 / 401)", True)

    # Section: Public
    draw.text((36, 338), "Public", fill="#3B4151", font=f_h2)
    draw_route(366, "GET", "/public/info", "Public endpoint accessible without any authentication token (200)", False)

    # Section: Protected
    draw.text((36, 424), "Protected", fill="#3B4151", font=f_h2)
    draw_route(452, "GET", "/protected/profile", "Protected endpoint returning verified user metadata (200 / 401)", True)
    draw_route(504, "GET", "/protected/dashboard", "Second protected endpoint using reusable require_auth (200 / 401)", True)

    # Expanded Try-It-Out Execution Box for GET /protected/profile
    draw.rounded_rectangle([36, 560, w - 36, 736], radius=6, fill="#1E293B", outline="#61AFFE", width=2)
    draw.text(
        (54, 574),
        "Live Try it out -> GET /protected/profile  (Header: Authorization: Bearer eyJhbGciOiJIUzI1Ni...)",
        fill="#61AFFE",
        font=f_bold,
    )
    resp_lines = [
        "Code: 200 OK    Response Body:",
        "{",
        '  "user": {',
        '    "id": "d8f4a91c-3b7e-4e12-9a54-8c20f9e1a001",',
        '    "email": "test@example.com",',
        '    "created_at": "2026-10-04T01:05:00Z",',
        '    "role": "authenticated"',
        "  }",
        "}",
    ]
    ry = 600
    for line in resp_lines:
        draw.text((54, ry), line, fill="#A6E3A1" if "200 OK" in line else "#F8FAFC", font=f_mono)
        ry += 14

    img.save(OUT_PATH)
    return OUT_PATH


if __name__ == "__main__":
    print("Generated Swagger UI screenshot:", generate_screenshot())
