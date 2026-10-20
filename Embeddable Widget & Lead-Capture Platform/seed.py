"""
Database Seed Script for Embeddable Widget & Lead-Capture Platform.

Seeds:
- Two isolated tenant accounts (Tenant A: Acme Corp, Tenant B: Globex)
- 3 production widgets with different themes and form fields
- Pre-populated realistic leads with geo data for dashboard analytics
"""

import json
import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from app.auth import hash_password
from app.database import get_db, init_db, utc_now_iso


def seed_database():
    print("Initializing SQLite schema...")
    init_db()

    with get_db() as conn:
        print("Seeding tenant accounts...")

        # Clear existing seed data for idempotent setup
        conn.execute("DELETE FROM submissions;")
        conn.execute("DELETE FROM widgets;")
        conn.execute("DELETE FROM tenants;")

        # 1. Tenants
        tenant_a_id = "tnt_acme_corp"
        tenant_b_id = "tnt_globex_inc"
        now = utc_now_iso()

        conn.execute(
            "INSERT INTO tenants (id, name, email, password_hash, created_at) VALUES (?, ?, ?, ?, ?)",
            (tenant_a_id, "Acme Corporation", "alex@acme.com", hash_password("acme_secret_123"), now),
        )
        conn.execute(
            "INSERT INTO tenants (id, name, email, password_hash, created_at) VALUES (?, ?, ?, ?, ?)",
            (tenant_b_id, "Globex Industries", "sarah@globex.com", hash_password("globex_secret_456"), now),
        )

        print("Seeding widgets...")
        # 2. Widgets
        widget_1_id = "wgt_demo123"
        fields_w1 = json.dumps([
            {"name": "name", "label": "Full Name", "type": "text", "required": True, "placeholder": "Jane Doe"},
            {"name": "email", "label": "Work Email", "type": "email", "required": True, "placeholder": "jane@company.com"},
            {"name": "company", "label": "Company Name", "type": "text", "required": False, "placeholder": "Acme Inc."},
        ])

        conn.execute(
            """
            INSERT INTO widgets (
                id, tenant_id, title, description, widget_type, button_text,
                form_fields, theme_color, is_active, allowed_domains, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, '*', ?, ?)
            """,
            (
                widget_1_id,
                tenant_a_id,
                "Acme Cloud Engineering Newsletter",
                "Weekly technical deep dives on containerized backends and SQL tuning.",
                "signup_form",
                "Subscribe Free",
                fields_w1,
                "#0D9488",
                now,
                now,
            ),
        )

        widget_2_id = "wgt_contact456"
        fields_w2 = json.dumps([
            {"name": "name", "label": "Your Name", "type": "text", "required": True, "placeholder": "Alex Smith"},
            {"name": "email", "label": "Business Email", "type": "email", "required": True, "placeholder": "alex@enterprise.com"},
            {"name": "message", "label": "How can we help?", "type": "textarea", "required": True, "placeholder": "Describe your use case..."},
        ])

        conn.execute(
            """
            INSERT INTO widgets (
                id, tenant_id, title, description, widget_type, button_text,
                form_fields, theme_color, is_active, allowed_domains, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, '*', ?, ?)
            """,
            (
                widget_2_id,
                tenant_a_id,
                "Book a 15-Minute Technical Walkthrough",
                "Talk directly to our backend engineering team about your architecture.",
                "contact_modal",
                "Request Walkthrough",
                fields_w2,
                "#2563EB",
                now,
                now,
            ),
        )

        # Tenant B Widget (for multi-tenant isolation testing)
        widget_3_id = "wgt_globex789"
        fields_w3 = json.dumps([
            {"name": "email", "label": "Your Email", "type": "email", "required": True, "placeholder": "user@globex.org"},
        ])

        conn.execute(
            """
            INSERT INTO widgets (
                id, tenant_id, title, description, widget_type, button_text,
                form_fields, theme_color, is_active, allowed_domains, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, '*', ?, ?)
            """,
            (
                widget_3_id,
                tenant_b_id,
                "Globex Early Access Program",
                "Join the waitlist for Globex next-generation logistics API.",
                "signup_form",
                "Join Waitlist",
                fields_w3,
                "#DC2626",
                now,
                now,
            ),
        )

        print("Seeding initial submission leads...")
        # 3. Submissions for Widget 1
        sample_submissions = [
            ("sub_001", widget_1_id, tenant_a_id, {"name": "Jordan Lee", "email": "jordan@startup.io", "company": "VectorTech"}, "198.51.100.1", "United States", "New York", "New York", "provider_a", 0),
            ("sub_002", widget_1_id, tenant_a_id, {"name": "Elena Rostova", "email": "elena@berlin-tech.de", "company": "FinScale"}, "203.0.113.4", "Germany", "Berlin", "Berlin", "provider_a", 0),
            ("sub_003", widget_1_id, tenant_a_id, {"name": "Kenji Sato", "email": "kenji@tokyo-dev.jp", "company": "CloudKobo"}, "192.0.2.8", "Japan", "Tokyo", "Tokyo", "provider_b", 0),
            ("sub_004", widget_1_id, tenant_a_id, {"name": "Carlos Gomez", "email": "carlos@madrid.es", "company": "DataHub"}, "198.51.100.22", "Spain", "Madrid", "Madrid", "provider_a", 0),
            ("sub_005", widget_1_id, tenant_a_id, {"name": "SpamBot 3000", "email": "bot@spam-farm.ru", "company": "BuyCrypto"}, "198.51.100.99", "Unknown", "Unknown", "Unknown", "honeypot_caught", 1),
            ("sub_006", widget_2_id, tenant_a_id, {"name": "Marcus Vance", "email": "m.vance@enterprise.com", "message": "Need help migrating 400TB PostgreSQL cluster."}, "203.0.113.88", "United Kingdom", "London", "England", "provider_b", 0),
        ]

        for sub in sample_submissions:
            s_id, w_id, t_id, data, ip, country, city, region, provider, is_spam = sub
            conn.execute(
                """
                INSERT INTO submissions (
                    id, widget_id, tenant_id, data, ip_address, user_agent,
                    country, city, region, geo_provider, is_spam, created_at
                ) VALUES (?, ?, ?, ?, ?, 'Mozilla/5.0 Chrome/120', ?, ?, ?, ?, ?, ?)
                """,
                (s_id, w_id, t_id, json.dumps(data), ip, country, city, region, provider, is_spam, now),
            )

        conn.commit()

    print("\nDatabase successfully seeded!")
    print("=" * 65)
    print("DEMO CREDENTIALS:")
    print("  Tenant A (Acme):   alex@acme.com     / acme_secret_123")
    print("  Tenant B (Globex): sarah@globex.com  / globex_secret_456")
    print("\nDEMO WIDGETS:")
    print(f"  Widget 1 (Acme):   wgt_demo123       (Signup Form)")
    print(f"  Widget 2 (Acme):   wgt_contact456    (Contact Modal)")
    print(f"  Widget 3 (Globex): wgt_globex789     (Waitlist)")
    print("\nEMBED SNIPPET:")
    print('  <script src="http://localhost:8000/v1/widget.js?id=wgt_demo123" defer></script>')
    print("=" * 65 + "\n")


if __name__ == "__main__":
    seed_database()
