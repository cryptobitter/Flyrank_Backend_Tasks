"""
PDF Report Generator Module using ReportLab.

Constructs an executive-grade, multi-page PDF document featuring:
- Two-pass NumberedCanvas for 'Page X of Y' dynamic footers
- Styled KPI cards and executive summary callouts
- Embedded vector/raster analytical charts
- Formatted tabular data from SQL aggregations
- Clean modern color palette with WCAG compliance
"""

from datetime import datetime, timezone
import hashlib
import os
import sys
import time
from typing import Any, Dict, List, Optional

# Ensure local module imports resolve cleanly
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    HRFlowable,
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from charts import generate_category_hours_chart, generate_status_donut_chart
from database import (
    init_db,
    query_assignee_workload,
    query_category_breakdown,
    query_executive_metrics,
    query_priority_breakdown,
    query_recent_tasks,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ARTIFACTS_DIR = os.path.join(BASE_DIR, "artifacts", "reports")


class NumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas that accumulates total page count and stamps
    running headers and footers with accurate 'Page X of Y' notation.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._saved_page_states: List[Dict[str, Any]] = []

    def showPage(self) -> None:
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self) -> None:
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_header_footer(num_pages)
            super().showPage()
        super().save()

    def draw_header_footer(self, page_count: int) -> None:
        self.saveState()
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(colors.HexColor("#64748B"))

        # Running Header (pages > 1)
        if self._pageNumber > 1:
            self.drawString(54, 750, "FLYRANK PLATFORM ENGINEERING | SPRINT ANALYTICS REPORT")
            self.drawRightString(612 - 54, 750, datetime.now(timezone.utc).strftime("%Y-%m-%d UTC"))
            self.setStrokeColor(colors.HexColor("#CBD5E1"))
            self.setLineWidth(0.5)
            self.line(54, 744, 612 - 54, 744)

        # Running Footer (all pages)
        self.setFont("Helvetica", 8)
        self.drawString(54, 38, "Flyrank Background Report Engine | Production Artifact v2.4")
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(612 - 54, 38, page_str)
        self.setStrokeColor(colors.HexColor("#E2E8F0"))
        self.setLineWidth(0.5)
        self.line(54, 48, 612 - 54, 48)

        self.restoreState()


def get_styles() -> Dict[str, ParagraphStyle]:
    """Return dictionary of customized typography styles."""
    styles = getSampleStyleSheet()

    custom_styles = {
        "DocTitle": ParagraphStyle(
            "DocTitle",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=22,
            leading=26,
            textColor=colors.HexColor("#0F172A"),
            spaceAfter=4,
        ),
        "DocSubtitle": ParagraphStyle(
            "DocSubtitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#475569"),
            spaceAfter=12,
        ),
        "SectionHeader": ParagraphStyle(
            "SectionHeader",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=17,
            textColor=colors.HexColor("#1E293B"),
            spaceBefore=14,
            spaceAfter=8,
        ),
        "CardValue": ParagraphStyle(
            "CardValue",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=20,
            alignment=1,  # Centered
            textColor=colors.HexColor("#0F172A"),
        ),
        "CardLabel": ParagraphStyle(
            "CardLabel",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            alignment=1,  # Centered
            textColor=colors.HexColor("#64748B"),
        ),
        "TableCell": ParagraphStyle(
            "TableCell",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=11,
            textColor=colors.HexColor("#334155"),
        ),
        "TableCellBold": ParagraphStyle(
            "TableCellBold",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8.5,
            leading=11,
            textColor=colors.HexColor("#1E293B"),
        ),
        "TableHeader": ParagraphStyle(
            "TableHeader",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8.5,
            leading=11,
            textColor=colors.white,
        ),
    }
    return custom_styles


def _build_kpi_cards(metrics: Dict[str, Any], styles: Dict[str, ParagraphStyle]) -> Table:
    """Build a modern 4-column KPI metric summary card component."""
    card_data = [
        [
            Paragraph(str(metrics.get("total_tasks", 0)), styles["CardValue"]),
            Paragraph(f"{metrics.get('completion_rate', 0)}%", styles["CardValue"]),
            Paragraph(str(metrics.get("completed_tasks", 0)), styles["CardValue"]),
            Paragraph(f"{metrics.get('total_actual_hours', 0)}h", styles["CardValue"]),
        ],
        [
            Paragraph("TOTAL TASKS", styles["CardLabel"]),
            Paragraph("COMPLETION RATE", styles["CardLabel"]),
            Paragraph("SHIPPED TASKS", styles["CardLabel"]),
            Paragraph("EFFORT LOGGED", styles["CardLabel"]),
        ],
    ]

    table = Table(card_data, colWidths=[1.25 * inch, 1.25 * inch, 1.25 * inch, 1.25 * inch])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#E2E8F0")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ]
        )
    )
    return table


def _build_priority_table(
    priority_data: List[Dict[str, Any]],
    styles: Dict[str, ParagraphStyle],
) -> Table:
    """Render SQL aggregated priority breakdown into a stylized table."""
    headers = [
        Paragraph("Priority", styles["TableHeader"]),
        Paragraph("Total", styles["TableHeader"]),
        Paragraph("Completed", styles["TableHeader"]),
        Paragraph("In Progress", styles["TableHeader"]),
        Paragraph("Pending", styles["TableHeader"]),
        Paragraph("Done %", styles["TableHeader"]),
        Paragraph("Hours Logged", styles["TableHeader"]),
    ]

    rows = [headers]
    for row in priority_data:
        prio = row["priority"]
        badge_color = "#DC2626" if prio == "Critical" else ("#EA580C" if prio == "High" else "#2563EB")
        rows.append(
            [
                Paragraph(f"<font color='{badge_color}'><b>{prio}</b></font>", styles["TableCell"]),
                Paragraph(str(row["total"]), styles["TableCell"]),
                Paragraph(str(row["completed"]), styles["TableCell"]),
                Paragraph(str(row["in_progress"]), styles["TableCell"]),
                Paragraph(str(row["pending"]), styles["TableCell"]),
                Paragraph(f"{row['completion_pct']}%", styles["TableCellBold"]),
                Paragraph(f"{row['logged_hours']}h", styles["TableCell"]),
            ]
        )

    t = Table(rows, colWidths=[1.1 * inch, 0.7 * inch, 0.7 * inch, 0.8 * inch, 0.7 * inch, 0.8 * inch, 0.9 * inch])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E293B")),
                ("ALIGN", (1, 0), (-1, -1), "CENTER"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return t


def _build_category_table(
    category_data: List[Dict[str, Any]],
    styles: Dict[str, ParagraphStyle],
) -> Table:
    """Render category velocity and estimation variance table."""
    headers = [
        Paragraph("Category", styles["TableHeader"]),
        Paragraph("Tasks", styles["TableHeader"]),
        Paragraph("Completed", styles["TableHeader"]),
        Paragraph("Completion %", styles["TableHeader"]),
        Paragraph("Est. Hours", styles["TableHeader"]),
        Paragraph("Act. Hours", styles["TableHeader"]),
        Paragraph("Variance", styles["TableHeader"]),
    ]

    rows = [headers]
    for c in category_data:
        var = c["variance_hours"]
        var_str = f"+{var}h" if var > 0 else f"{var}h"
        var_color = "#DC2626" if var > 2.0 else ("#16A34A" if var <= 0 else "#D97706")

        rows.append(
            [
                Paragraph(f"<b>{c['category']}</b>", styles["TableCell"]),
                Paragraph(str(c["total_tasks"]), styles["TableCell"]),
                Paragraph(str(c["completed_tasks"]), styles["TableCell"]),
                Paragraph(f"{c['completion_rate']}%", styles["TableCellBold"]),
                Paragraph(f"{c['est_hours']}h", styles["TableCell"]),
                Paragraph(f"{c['act_hours']}h", styles["TableCell"]),
                Paragraph(f"<font color='{var_color}'><b>{var_str}</b></font>", styles["TableCell"]),
            ]
        )

    t = Table(rows, colWidths=[1.2 * inch, 0.65 * inch, 0.75 * inch, 0.95 * inch, 0.8 * inch, 0.8 * inch, 0.85 * inch])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F766E")),  # Teal-800
                ("ALIGN", (1, 0), (-1, -1), "CENTER"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return t


def _build_task_items_table(
    tasks: List[Dict[str, Any]],
    styles: Dict[str, ParagraphStyle],
) -> Table:
    """Render itemized recent sprint task records with status badges."""
    headers = [
        Paragraph("ID", styles["TableHeader"]),
        Paragraph("Task Description", styles["TableHeader"]),
        Paragraph("Category", styles["TableHeader"]),
        Paragraph("Priority", styles["TableHeader"]),
        Paragraph("Status", styles["TableHeader"]),
        Paragraph("Assignee", styles["TableHeader"]),
        Paragraph("Hours", styles["TableHeader"]),
    ]

    rows = [headers]
    for t in tasks:
        status_color = "#16A34A" if t["status"] == "Completed" else ("#2563EB" if t["status"] == "In Progress" else "#D97706")
        rows.append(
            [
                Paragraph(str(t["id"]), styles["TableCellBold"]),
                Paragraph(t["title"], styles["TableCell"]),
                Paragraph(t["category"], styles["TableCell"]),
                Paragraph(t["priority"], styles["TableCell"]),
                Paragraph(f"<font color='{status_color}'><b>{t['status']}</b></font>", styles["TableCell"]),
                Paragraph(t["assignee"], styles["TableCell"]),
                Paragraph(f"{t['actual_hours']}/{t['estimated_hours']}h", styles["TableCell"]),
            ]
        )

    table = Table(
        rows,
        colWidths=[0.35 * inch, 2.1 * inch, 0.85 * inch, 0.75 * inch, 0.85 * inch, 0.95 * inch, 0.75 * inch],
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#334155")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
                ("TOPPADDING", (0, 0), (-1, -1), 4.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4.5),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    return table


def generate_pdf_report(
    db_path: Optional[str] = None,
    output_filename: Optional[str] = None,
    report_title: str = "Sprint Engineering & Operations Analytics",
) -> Dict[str, Any]:
    """
    Main pipeline entry point:
    1. Queries SQL aggregations from SQLite
    2. Renders high-DPI visual charts
    3. Assembles multi-page PDF document
    4. Computes SHA256 checksum, file size, and execution duration
    Returns dict containing artifact metadata.
    """
    start_time = time.time()
    init_db(db_path)

    os.makedirs(ARTIFACTS_DIR, exist_ok=True)
    timestamp_slug = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = output_filename or f"task_analytics_report_{timestamp_slug}.pdf"
    file_path = os.path.join(ARTIFACTS_DIR, filename)

    # 1. Query SQL aggregations
    metrics = query_executive_metrics(db_path)
    priority_data = query_priority_breakdown(db_path)
    category_data = query_category_breakdown(db_path)
    recent_tasks = query_recent_tasks(limit=10, db_path=db_path)

    # 2. Generate embedded chart images
    donut_chart_path = generate_status_donut_chart(metrics, f"status_{timestamp_slug}.png")
    cat_chart_path = generate_category_hours_chart(category_data, f"cat_{timestamp_slug}.png")

    # 3. Build Document Flowables
    doc = SimpleDocTemplate(
        file_path,
        pagesize=letter,
        leftMargin=45,
        rightMargin=45,
        topMargin=54,
        bottomMargin=54,
    )

    styles = get_styles()
    story: List[Any] = []

    # Title & Header
    story.append(Paragraph(report_title, styles["DocTitle"]))
    generated_dt = datetime.now(timezone.utc).strftime("%B %d, %Y at %H:%M:%S UTC")
    subtitle_text = f"Automated Background Pipeline Report &bull; Generated: {generated_dt} &bull; Environment: Production"
    story.append(Paragraph(subtitle_text, styles["DocSubtitle"]))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0284C7"), spaceAfter=14))

    # KPI Summary Cards
    story.append(Paragraph("Executive Summary & Operational KPIs", styles["SectionHeader"]))
    story.append(_build_kpi_cards(metrics, styles))
    story.append(Spacer(1, 14))

    # Analytical Visuals
    story.append(Paragraph("Visual Breakdown & Effort Distribution", styles["SectionHeader"]))
    chart_table_data = [
        [
            Image(donut_chart_path, width=2.6 * inch, height=1.7 * inch),
            Image(cat_chart_path, width=3.2 * inch, height=1.7 * inch),
        ]
    ]
    chart_table = Table(chart_table_data, colWidths=[2.9 * inch, 3.5 * inch])
    chart_table.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    story.append(chart_table)
    story.append(Spacer(1, 10))

    # Aggregated SQL Priority Breakdown
    story.append(Paragraph("Task Distribution by Priority Level", styles["SectionHeader"]))
    story.append(_build_priority_table(priority_data, styles))

    # Page Break for Category Analytics & Detailed Task Ledger
    story.append(PageBreak())

    # Page 2: Aggregated SQL Category Breakdown
    story.append(Paragraph("Velocity & Effort Variance by Category", styles["DocTitle"]))
    story.append(Paragraph("Category breakdown analyzing resource expenditure and sprint velocity variance.", styles["DocSubtitle"]))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#0284C7"), spaceAfter=10))
    story.append(_build_category_table(category_data, styles))
    story.append(Spacer(1, 14))

    # Itemized Detail Records
    story.append(Paragraph("Itemized Task Log & Activity History", styles["SectionHeader"]))
    story.append(_build_task_items_table(recent_tasks, styles))

    # Build PDF with NumberedCanvas
    doc.build(story, canvasmaker=NumberedCanvas)

    duration = round(time.time() - start_time, 3)
    file_size = os.path.getsize(file_path)

    # Compute SHA-256 for artifact auditability
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    sha256 = hasher.hexdigest()

    return {
        "status": "success",
        "filename": filename,
        "file_path": file_path,
        "file_size_bytes": file_size,
        "file_size_kb": round(file_size / 1024, 1),
        "sha256": sha256,
        "metrics": metrics,
        "duration_seconds": duration,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


if __name__ == "__main__":
    result = generate_pdf_report()
    print("Report Generated Successfully:")
    print(f"Path: {result['file_path']}")
    print(f"Size: {result['file_size_kb']} KB")
    print(f"SHA256: {result['sha256']}")
    print(f"Duration: {result['duration_seconds']}s")

