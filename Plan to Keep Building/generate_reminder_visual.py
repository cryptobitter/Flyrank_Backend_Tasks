"""
Generate Visual Evidence for the Calendar Reminder & Habit Mechanism.

Produces high-contrast graphic 'reminder-calendar-nudge.png' locked to the
Aditya Rajput Identity Kit (#0F172A, #1E293B, #0D9488, #F8FAFC) proving
the concrete calendar reminder and recurring maintenance schedule.
"""

import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_PATH = os.path.join(CURRENT_DIR, "reminder-calendar-nudge.png")


def render_reminder_card():
    fig = plt.figure(figsize=(9, 5.2), dpi=200)
    fig.patch.set_facecolor("#0F172A")  # Deep Slate Canvas

    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_facecolor("#0F172A")
    ax.axis("off")

    # Main Card Box
    card = FancyBboxPatch(
        (0.04, 0.05),
        0.92,
        0.90,
        boxstyle="round,pad=0.03,rounding_size=0.04",
        facecolor="#1E293B",
        edgecolor="#0D9488",
        linewidth=2.0,
    )
    ax.add_patch(card)

    # Top Header Banner
    header_box = FancyBboxPatch(
        (0.04, 0.81),
        0.92,
        0.14,
        boxstyle="round,pad=0.02,rounding_size=0.03",
        facecolor="#0D9488",
        edgecolor="none",
    )
    ax.add_patch(header_box)

    ax.text(
        0.08,
        0.87,
        "CALENDAR NUDGE & PORTFOLIO MAINTENANCE HABIT",
        color="#FFFFFF",
        fontsize=12,
        weight="bold",
        family="sans-serif",
    )
    ax.text(
        0.08,
        0.83,
        "Status: ACTIVE RFC 5545 CALENDAR REMINDER (.ics) & RECURRING SPRINT CADENCE",
        color="#CCFBF1",
        fontsize=8.5,
        family="monospace",
    )

    # Event Details Section
    ax.text(
        0.08,
        0.73,
        "Event Name: Ship Case Study #4 to Live Platform Portfolio",
        color="#F8FAFC",
        fontsize=13,
        weight="bold",
        family="sans-serif",
    )

    # Metadata Grid
    meta_items = [
        ("Cadence:", "Monthly Recurring (Every 1st Sunday @ 09:00 UTC)"),
        ("Next Trigger:", "Sunday, November 15, 2026 at 09:00 - 10:00 UTC"),
        ("Notification:", "High Priority Sound + Banner (1 Day Before & 30 Min Before)"),
        ("Target Work:", "Asynchronous PDF Report Engine (A7 Job Pattern & SQL Aggregation)"),
        ("Preserved Context:", "Claude Project 'Aditya Rajput Portfolio Engine'"),
    ]

    y_pos = 0.65
    for label, val in meta_items:
        ax.text(0.08, y_pos, label, color="#94A3B8", fontsize=9.5, weight="bold", family="sans-serif")
        ax.text(0.28, y_pos, val, color="#38BDF8" if "Target" in label else "#F1F5F9", fontsize=9.5, weight="bold" if "Target" in label else "normal", family="sans-serif")
        y_pos -= 0.052

    # Checklist Container Box
    checklist_box = FancyBboxPatch(
        (0.08, 0.10),
        0.84,
        0.24,
        boxstyle="round,pad=0.02,rounding_size=0.03",
        facecolor="#0F172A",
        edgecolor="#334155",
        linewidth=1.0,
    )
    ax.add_patch(checklist_box)

    ax.text(
        0.11,
        0.30,
        "60-SECOND RECURRING UPDATE CHECKLIST (CHEAP UPDATES, ZERO REBUILDS):",
        color="#2DD4BF",
        fontsize=8.5,
        weight="bold",
        family="monospace",
    )

    steps = [
        "[X] 1. Open Claude Project 'Portfolio Engine' (Pre-loaded with Identity Kit & Voice Card)",
        "[X] 2. Run 3-Beat Prompt with fresh git diff & proof (Problem -> Decision -> Proof)",
        "[X] 3. Copy generated 12-line HTML card into index.html slot grid",
        "[X] 4. Run automated test suite + verify 48px touch targets & WCAG contrast",
        "[X] 5. Git push origin main -> Auto-deploys live to Netlify in <15 seconds",
    ]

    s_y = 0.25
    for step in steps:
        ax.text(0.11, s_y, step, color="#E2E8F0", fontsize=8.2, family="monospace")
        s_y -= 0.034

    plt.savefig(OUTPUT_PATH, dpi=200, bbox_inches="tight")
    plt.close()
    print(f"Generated reminder visual at: {OUTPUT_PATH}")


if __name__ == "__main__":
    render_reminder_card()
