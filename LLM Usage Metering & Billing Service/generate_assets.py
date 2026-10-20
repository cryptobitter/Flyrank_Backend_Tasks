"""
Visual Diagram Generator for LLM Usage Metering & Billing Engine.
Generates high-resolution architecture and lifecycle flowcharts.
"""

from PIL import Image, ImageDraw, ImageFont
import os

def create_architecture_diagram(output_path: str):
    width, height = 1200, 750
    img = Image.new("RGBA", (width, height), (15, 23, 42, 255)) # Dark slate
    draw = ImageDraw.Draw(img)

    try:
        title_font = ImageFont.truetype("arial.ttf", 28)
        header_font = ImageFont.truetype("arialbd.ttf", 18)
        body_font = ImageFont.truetype("arial.ttf", 14)
        small_font = ImageFont.truetype("arial.ttf", 12)
    except IOError:
        title_font = header_font = body_font = small_font = ImageFont.load_default()

    # Title & Subtitle
    draw.text((50, 35), "LLM Usage Metering & Billing Engine — Architecture", fill=(248, 250, 252, 255), font=title_font)
    draw.text((50, 75), "Idempotent Metering • Quota Boundary Enforcement • Money Math • Stripe Test Mode", fill=(148, 163, 184, 255), font=body_font)

    # 4 Architecture Columns / Boxes
    boxes = [
        {
            "title": "1. Client & API Boundary",
            "rect": (50, 130, 300, 520),
            "header_color": (37, 99, 235),
            "lines": [
                "POST /api/v1/generate",
                "  • Header: Idempotency-Key",
                "  • Input Token Simulation",
                "",
                "GET /api/v1/usage",
                "  • Tenant Rollup Query",
                "",
                "POST /api/v1/billing/checkout",
                "  • Upgrade to Pro ($29/mo)",
                "",
                "Boundary Validation:",
                "  • Pydantic Schema Gating",
                "  • Clean 4xx, Never 500",
                "  • 429 Too Many Requests",
                "  • 402 Payment Required"
            ]
        },
        {
            "title": "2. Core Logic & Math",
            "rect": (330, 130, 580, 520),
            "header_color": (13, 148, 136),
            "lines": [
                "MeterService:",
                "  • Check Idempotency Cache",
                "  • Replay? Return cached 200",
                "",
                "QuotaService:",
                "  • Check Month API & Tokens",
                "  • At 1,000 / 1,000 -> Allow",
                "  • At 1,001 -> Reject 429",
                "",
                "Exact Money Math:",
                "  • Zero floats (micro-dollars)",
                "  • Fresh: $0.150 / 1M tokens",
                "  • Cached: $0.0375 (75% off)",
                "  • Reasoning: $0.600 / 1M",
                "  • Output: $0.600 / 1M",
                "  • Integer Cents Conversion"
            ]
        },
        {
            "title": "3. Storage & Isolation",
            "rect": (610, 130, 860, 520),
            "header_color": (147, 51, 234),
            "lines": [
                "SQLite / PostgreSQL Engine:",
                "  • Multi-tenant Data Isolation",
                "  • Strict Foreign Keys ON",
                "",
                "Tables:",
                "  • tenants (metadata, Stripe ID)",
                "  • plans (Free, Pro quotas)",
                "  • subscriptions (status, periods)",
                "  • usage_events (meters & cost)",
                "  • idempotency_records (cache)",
                "  • webhook_events (dedup log)",
                "  • reconciliation_logs",
                "",
                "Indexes:",
                "  • (tenant_id, timestamp)",
                "  • (idempotency_key)"
            ]
        },
        {
            "title": "4. Stripe & Background",
            "rect": (890, 130, 1140, 520),
            "header_color": (234, 88, 12),
            "lines": [
                "Stripe Webhook Handler:",
                "  • HMAC-SHA256 Verification",
                "  • whsec_ Signature Check",
                "  • Forged? Return 400",
                "  • Replay? Ignored duplicate",
                "",
                "Events Handled:",
                "  • checkout.session.completed",
                "  • customer.subscription.updated",
                "  • customer.subscription.deleted",
                "",
                "Background Jobs:",
                "  • 80% & 100% Quota Alerts",
                "  • Nightly Stripe Sync Audit"
            ]
        }
    ]

    for b in boxes:
        x0, y0, x1, y1 = b["rect"]
        # Background box
        draw.rectangle((x0, y0, x1, y1), fill=(30, 41, 59, 255), outline=(51, 65, 85, 255), width=2)
        # Header banner
        draw.rectangle((x0, y0, x1, y0 + 40), fill=b["header_color"])
        draw.text((x0 + 12, y0 + 10), b["title"], fill=(255, 255, 255, 255), font=header_font)
        
        # Text lines
        curr_y = y0 + 55
        for line in b["lines"]:
            if line.startswith("  •"):
                draw.text((x0 + 18, curr_y), line, fill=(203, 213, 225, 255), font=small_font)
            elif line.endswith(":"):
                draw.text((x0 + 12, curr_y), line, fill=(56, 189, 248, 255), font=body_font)
            else:
                draw.text((x0 + 12, curr_y), line, fill=(241, 245, 249, 255), font=body_font)
            curr_y += 20

    # Footer note
    draw.rectangle((50, 550, 1140, 700), fill=(24, 33, 47, 255), outline=(51, 65, 85, 255), width=1)
    draw.text((70, 565), "KEY ARCHITECTURAL PROMISES & VERIFICATION GATES", fill=(251, 191, 36, 255), font=header_font)
    draw.text((70, 595), "1. Exactly-Once Metering: Client retries with same Idempotency-Key return cached response; zero duplicate usage events created.", fill=(226, 232, 240, 255), font=small_font)
    draw.text((70, 615), "2. Honest Quota Boundaries: Tenant allowed at 1,000 calls; rejected at 1,001 with HTTP 429 Too Many Requests & Retry-After.", fill=(226, 232, 240, 255), font=small_font)
    draw.text((70, 635), "3. Pinned Integer Money Math: Zero floating point numbers. Scaled micro-dollars ($1 = 1,000,000) for exact sub-cent token accounting.", fill=(226, 232, 240, 255), font=small_font)
    draw.text((70, 655), "4. Cryptographic Stripe Sync: Webhooks verified via HMAC-SHA256 (forged -> 400). Event deduplication prevents double-upgrade attacks.", fill=(226, 232, 240, 255), font=small_font)
    draw.text((70, 675), "5. Asynchronous Audit Worker: Background reconciliation job audits local state vs Stripe; alerts dispatched at 80% and 100% quota.", fill=(226, 232, 240, 255), font=small_font)

    img.save(output_path, "PNG")
    print(f"[SAVED] {output_path}")

if __name__ == "__main__":
    out_dir = os.path.dirname(__file__)
    create_architecture_diagram(os.path.join(out_dir, "architecture-diagram.png"))
