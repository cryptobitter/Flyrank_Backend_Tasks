"""
Command-Line Interface (CLI) for PDF Report Generator Pipeline.

Usage:
    python cli.py generate [--title "My Report"]
    python cli.py query
    python cli.py list
    python cli.py schedule [--interval 30]
"""

import argparse
import os
import sys
import time

# Ensure local module imports resolve cleanly
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from database import (
    init_db,
    query_category_breakdown,
    query_executive_metrics,
    query_priority_breakdown,
)
from report_generator import generate_pdf_report
from scheduler import scheduler


def cmd_generate(args: argparse.Namespace) -> None:
    print(f"\n[1/3] Querying SQLite and initializing pipeline...")
    print(f"[2/3] Rendering charts and compiling PDF report: '{args.title}'...")
    result = generate_pdf_report(report_title=args.title)
    print(f"[3/3] Report generated successfully!")
    print(f"  Artifact Path:   {result['file_path']}")
    print(f"  File Size:       {result['file_size_kb']} KB ({result['file_size_bytes']} bytes)")
    print(f"  SHA-256 Check:   {result['sha256']}")
    print(f"  Execution Time:  {result['duration_seconds']}s")
    print(f"  Total Tasks:     {result['metrics']['total_tasks']}")
    print(f"  Completion Rate: {result['metrics']['completion_rate']}%\n")


def cmd_query(args: argparse.Namespace) -> None:
    init_db()
    metrics = query_executive_metrics()
    priorities = query_priority_breakdown()
    categories = query_category_breakdown()

    print("\n" + "=" * 60)
    print("           SQL AGGREGATION ANALYTICS DASHBOARD")
    print("=" * 60)
    print(f"Total Tasks:       {metrics['total_tasks']}")
    print(f"Completed Tasks:   {metrics['completed_tasks']} ({metrics['completion_rate']}%)")
    print(f"In Progress:       {metrics['in_progress_tasks']}")
    print(f"Pending:           {metrics['pending_tasks']}")
    print(f"Effort (Est/Act):  {metrics['total_estimated_hours']}h / {metrics['total_actual_hours']}h")
    print(f"Avg Turnaround:    {metrics['avg_turnaround_hours']}h")
    print(f"Active Engineers:  {metrics['active_contributors']}")

    print("\n--- Priority Breakdown (SQL GROUP BY priority) ---")
    print(f"{'Priority':<12} {'Total':<8} {'Done':<8} {'In Prog':<10} {'Pending':<10} {'Done %':<8} {'Hours':<8}")
    print("-" * 64)
    for p in priorities:
        print(f"{p['priority']:<12} {p['total']:<8} {p['completed']:<8} {p['in_progress']:<10} {p['pending']:<10} {p['completion_pct']}%    {p['logged_hours']}h")

    print("\n--- Category Breakdown (SQL GROUP BY category) ---")
    print(f"{'Category':<16} {'Total':<8} {'Done':<8} {'Done %':<10} {'Est Hrs':<10} {'Act Hrs':<10} {'Variance':<10}")
    print("-" * 72)
    for c in categories:
        var = f"+{c['variance_hours']}h" if c['variance_hours'] > 0 else f"{c['variance_hours']}h"
        print(f"{c['category']:<16} {c['total_tasks']:<8} {c['completed_tasks']:<8} {c['completion_rate']}%     {c['est_hours']}h       {c['act_hours']}h       {var:<10}")
    print("=" * 60 + "\n")


def cmd_list(args: argparse.Namespace) -> None:
    artifacts_dir = os.path.join(CURRENT_DIR, "artifacts", "reports")
    if not os.path.exists(artifacts_dir):
        print("No artifacts directory found.")
        return

    files = [f for f in os.listdir(artifacts_dir) if f.endswith(".pdf")]
    print(f"\nStored PDF Artifacts ({len(files)} total):")
    print("-" * 70)
    for f in sorted(files, reverse=True):
        full = os.path.join(artifacts_dir, f)
        size_kb = round(os.path.getsize(full) / 1024, 1)
        print(f"  {f:<45} {size_kb:>8} KB")
    print("-" * 70 + "\n")


def cmd_schedule(args: argparse.Namespace) -> None:
    print(f"\nStarting recurring background scheduler (Interval: {args.interval}s)...")
    scheduler.start(interval_seconds=args.interval)
    print("Scheduler running. Press Ctrl+C to terminate.")
    try:
        while True:
            status = scheduler.get_status()
            print(f"  [Heartbeat] Runs Completed: {status['total_runs_completed']} | Next Run: {status['next_run_at']}")
            time.sleep(min(args.interval, 10))
    except KeyboardInterrupt:
        print("\nStopping scheduler...")
        scheduler.stop()
        print("Scheduler stopped cleanly.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Flyrank PDF Report Generator CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # generate
    gen_parser = subparsers.add_parser("generate", help="Generate on-demand PDF report")
    gen_parser.add_argument("--title", default="Sprint Analytics & Operations Report", help="Report Title")

    # query
    subparsers.add_parser("query", help="Run SQL aggregations and display summary")

    # list
    subparsers.add_parser("list", help="List stored PDF artifacts")

    # schedule
    sched_parser = subparsers.add_parser("schedule", help="Start scheduled background runner")
    sched_parser.add_argument("--interval", type=int, default=30, help="Interval in seconds (default: 30s)")

    args = parser.parse_args()
    if args.command == "generate":
        cmd_generate(args)
    elif args.command == "query":
        cmd_query(args)
    elif args.command == "list":
        cmd_list(args)
    elif args.command == "schedule":
        cmd_schedule(args)


if __name__ == "__main__":
    main()
