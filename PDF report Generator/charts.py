"""
Chart Generation Utility for PDF Report Generator.

Renders high-DPI charts via Matplotlib and outputs clean image files
for embedding into ReportLab PDF flowables.
"""

import os
from typing import Any, Dict, List
import matplotlib
# Use Agg backend for headless server rendering without GUI display
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CHARTS_DIR = os.path.join(BASE_DIR, "artifacts", "charts")


def ensure_charts_dir() -> str:
    os.makedirs(CHARTS_DIR, exist_ok=True)
    return CHARTS_DIR


def generate_status_donut_chart(
    metrics: Dict[str, Any],
    output_filename: str = "status_donut.png",
) -> str:
    """
    Generate a modern donut chart showing task status distribution.
    Returns the absolute path to the generated PNG.
    """
    out_dir = ensure_charts_dir()
    output_path = os.path.join(out_dir, output_filename)

    labels = ["Completed", "In Progress", "Pending"]
    sizes = [
        metrics.get("completed_tasks", 0),
        metrics.get("in_progress_tasks", 0),
        metrics.get("pending_tasks", 0),
    ]
    colors = ["#10B981", "#3B82F6", "#F59E0B"]  # Emerald, Blue, Amber

    fig, ax = plt.subplots(figsize=(4.5, 3.2), dpi=200)
    wedges, texts, autotexts = ax.pie(
        sizes,
        labels=labels,
        autopct="%1.1f%%",
        startangle=140,
        colors=colors,
        pctdistance=0.75,
        wedgeprops=dict(width=0.45, edgecolor="white", linewidth=2),
        textprops=dict(family="sans-serif", size=9, weight="bold", color="#1F2937"),
    )

    for at in autotexts:
        at.set_color("white")
        at.set_fontsize(8.5)
        at.set_weight("bold")

    ax.set_title("Task Distribution by Status", fontsize=11, fontweight="bold", pad=12, color="#1E293B")
    plt.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches="tight", transparent=False)
    plt.close(fig)
    return output_path


def generate_category_hours_chart(
    category_data: List[Dict[str, Any]],
    output_filename: str = "category_hours.png",
) -> str:
    """
    Generate a grouped horizontal bar chart comparing Estimated vs Actual hours by category.
    Returns the absolute path to the generated PNG.
    """
    out_dir = ensure_charts_dir()
    output_path = os.path.join(out_dir, output_filename)

    categories = [c["category"] for c in category_data]
    est_hours = [c.get("est_hours", 0) for c in category_data]
    act_hours = [c.get("act_hours", 0) for c in category_data]

    fig, ax = plt.subplots(figsize=(5.5, 3.2), dpi=200)
    y_pos = range(len(categories))
    bar_height = 0.35

    ax.barh(
        [y - bar_height / 2 for y in y_pos],
        est_hours,
        height=bar_height,
        label="Est. Hours",
        color="#94A3B8",
        edgecolor="none",
    )
    ax.barh(
        [y + bar_height / 2 for y in y_pos],
        act_hours,
        height=bar_height,
        label="Actual Hours",
        color="#0EA5E9",
        edgecolor="none",
    )

    ax.set_yticks(list(y_pos))
    ax.set_yticklabels(categories, fontsize=8.5, weight="bold", color="#334155")
    ax.set_xlabel("Hours Logged", fontsize=9, fontweight="bold", color="#475569")
    ax.set_title("Effort: Estimated vs Actual Hours", fontsize=11, fontweight="bold", pad=12, color="#1E293B")
    ax.legend(loc="lower right", frameon=True, fontsize=8)
    ax.grid(axis="x", linestyle="--", alpha=0.4)
    ax.set_axisbelow(True)

    plt.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches="tight", transparent=False)
    plt.close(fig)
    return output_path
