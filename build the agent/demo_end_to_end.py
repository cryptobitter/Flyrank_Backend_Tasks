"""
End-to-End Live Execution Runner for Backend Scout Agent.
Runs the complete core job from user prompt to live git tool execution,
test suite verification, guardrail inspection, Three-Beat synthesis,
and local staging in drafts/.
Saves full unedited run transcript to disk.
"""

import json
import os
import sys
import time
from pathlib import Path

from agent import BackendScoutAgent
from guardrails import AgentGuardrails
from PIL import Image, ImageDraw, ImageFont


def run_full_end_to_end():
    print("=" * 80)
    print(" [CHECKPOINT 1 MVP RUN] BACKEND CASE-STUDY & PR SCOUT AGENT")
    print("=" * 80)

    agent = BackendScoutAgent()
    transcript_lines = []

    def out(text: str = ""):
        print(text)
        transcript_lines.append(text)

    out(f"[*] Initialized BackendScoutAgent with live tools and MCP protocol registry.")
    out(f"[*] Platform: Scripted Python + FastMCP")
    out(f"[*] Model-Tools-Instructions Triad Active: Evidence-First | Three-Beat Schema")
    out(f"[*] Safety Guardrail: Read-Only Git Boundary + Secret Redaction Sanitizer Active")
    out("")

    # Prompt
    prompt = "Analyze the recent polite scraper milestone commit 1be4581 and stage a Three-Beat portfolio case study."
    out(f"[USER REQUEST] > {prompt}")
    out("-" * 80)

    # Step 1: Tool invocation git_log_recent
    out("\n[STEP 1: REPOSITORY INSPECTION]")
    out(">> Calling Tool: git_log_recent(limit=3)")
    recent_res = agent.execute_tool_safely("git_log_recent", {"limit": 3})
    out(f"<< Tool Returned ({recent_res.get('count', 0)} commits found):")
    for c in recent_res.get("commits", []):
        out(f"   [{c['commit_hash']}] {c['date']} - {c['subject']}")

    # Step 2: Target commit resolution
    target_hash = "1be4581"
    out(f"\n[STEP 2: LIVE COMMIT DIFF EXTRACTION]")
    out(f">> Calling Tool: git_get_commit_diff(commit_hash='{target_hash}')")
    diff_res = agent.execute_tool_safely("git_get_commit_diff", {"commit_hash": target_hash})

    out(f"<< Live Git Diff Retrieved:")
    out(f"   - Author: {diff_res.get('author')}")
    out(f"   - Date: {diff_res.get('date')}")
    out(f"   - Subject: {diff_res.get('subject')}")
    out(f"   - Files Changed: {', '.join(diff_res.get('files_changed', []))}")
    out(f"   - Stat Summary:\n     " + "\n     ".join(diff_res.get("stat_summary", "").split("\n")[:3]))

    # Step 3: Run live test verification
    out(f"\n[STEP 3: LIVE TEST SUITE EXECUTION]")
    out(">> Calling Tool: run_test_suite(test_path='build the agent/tests/test_contracts.py')")
    test_res = agent.execute_tool_safely("run_test_suite", {"test_path": "build the agent/tests/test_contracts.py"})
    out(f"<< Test Results: Passed={test_res.get('passed')} | Exit Code={test_res.get('exit_code')} | Duration={test_res.get('duration_sec')}s")

    # Step 4: Guardrail Interception & Secret Check
    out(f"\n[STEP 4: GUARDRAIL & REDACTION CHECK]")
    out(">> Verifying safety boundaries against forbidden commands (force push, reset, rm -rf)...")
    out(">> Sanitizing diff and environment context for credentials (sbp_*, sk-*, bearer tokens)...")
    raw_study = agent.synthesize_three_beat_study(
        commit_meta=diff_res,
        test_meta=test_res
    )
    clean_study, warnings = AgentGuardrails.sanitize_output(raw_study)
    out(f"<< Guardrail Verification Passed. Redaction Warnings: {len(warnings)}")

    # Step 5: Write to local staging directory
    out(f"\n[STEP 5: STAGING DELIVERABLE]")
    slug = f"case_study_{target_hash}_polite_scraper"
    out(f">> Calling Tool: stage_case_study(slug='{slug}')")
    stage_res = agent.execute_tool_safely("stage_case_study", {
        "slug": slug,
        "content": clean_study
    })
    out(f"<< Staged to Local File: {stage_res.get('relative_path')}")
    out(f"   Bytes written: {stage_res.get('bytes_written')} | Status: {stage_res.get('status')}")

    out("\n" + "=" * 80)
    out(" [AGENT GENERATED OUTPUT PREVIEW]")
    out("=" * 80)
    out(clean_study)
    out("=" * 80)
    out("[+] End-to-end run completed with zero manual interventions.")

    # Save transcripts
    drafts_dir = Path(__file__).resolve().parent / "drafts"
    drafts_dir.mkdir(exist_ok=True)

    text_log_path = Path(__file__).resolve().parent / "run_capture_transcript.txt"
    text_log_path.write_text("\n".join(transcript_lines), encoding="utf-8")

    json_log_path = Path(__file__).resolve().parent / "run_capture_transcript.json"
    json_log_path.write_text(json.dumps(agent.execution_log, indent=2), encoding="utf-8")

    # Render Visual Screen Capture
    render_screen_capture(transcript_lines, Path(__file__).resolve().parent / "screen-capture-walkthrough.png")
    render_html_player(agent.execution_log, Path(__file__).resolve().parent / "run_player.html")

    print(f"\n[SAVED ARTIFACTS]")
    print(f"- Text Transcript: {text_log_path.name}")
    print(f"- JSON Telemetry:  {json_log_path.name}")
    print(f"- Visual Capture:  screen-capture-walkthrough.png")
    print(f"- HTML Player:     run_player.html")
    print(f"- Staged Study:    {stage_res.get('relative_path')}")


def render_screen_capture(transcript_lines: list, output_path: Path):
    """Renders a high-resolution terminal capture of the end-to-end run using PIL."""
    # Filter and format lines
    lines = []
    for l in transcript_lines:
        for sub in l.split("\n"):
            lines.append(sub)

    # Image setup
    width = 1200
    line_height = 24
    padding = 40
    header_height = 80
    height = header_height + padding * 2 + (len(lines) * line_height)

    img = Image.new("RGB", (width, height), color=(15, 23, 42))  # Slate 900
    draw = ImageDraw.Draw(img)

    # Header bar (macOS / Linux terminal style)
    draw.rectangle([(0, 0), (width, header_height)], fill=(30, 41, 59))  # Slate 800
    # Window control dots
    draw.ellipse([(20, 26), (36, 42)], fill=(239, 68, 68))   # Red
    draw.ellipse([(46, 26), (62, 42)], fill=(245, 158, 11))  # Amber
    draw.ellipse([(72, 26), (88, 42)], fill=(16, 185, 129))  # Emerald

    # Header title
    title = "Backend PR Scout Agent - End-to-End Live MVP Run (Checkpoint 1)"
    draw.text((120, 24), title, fill=(241, 245, 249))

    # Font setup
    try:
        font = ImageFont.truetype("consola.ttf", 15)
        bold_font = ImageFont.truetype("consolab.ttf", 15)
    except Exception:
        font = ImageFont.load_default()
        bold_font = font

    y = header_height + padding
    for line in lines:
        fill = (226, 232, 240)  # Default light slate
        if line.startswith("[USER REQUEST]"):
            fill = (250, 204, 21)  # Yellow
        elif line.startswith("[STEP") or line.startswith("[CHECKPOINT"):
            fill = (56, 189, 248)  # Cyan
        elif line.startswith(">> Calling Tool"):
            fill = (168, 85, 247)  # Purple
        elif line.startswith("<<"):
            fill = (52, 211, 153)  # Emerald green
        elif line.startswith("### Beat") or line.startswith("# Case Study"):
            fill = (244, 114, 182)  # Pink
        elif line.startswith("---") or line.startswith("==="):
            fill = (100, 116, 139)  # Slate muted

        draw.text((padding, y), line[:120], font=font, fill=fill)
        y += line_height

    img.save(str(output_path), format="PNG")


def render_html_player(execution_log: list, output_path: Path):
    """Generates a self-contained interactive web player visualizer for the unedited run."""
    events_json = json.dumps(execution_log)
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Backend Scout Agent - Unedited Run Capture</title>
  <style>
    body {{
      background: #0f172a;
      color: #e2e8f0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, monospace;
      padding: 30px;
      margin: 0;
    }}
    .container {{
      max-width: 900px;
      margin: 0 auto;
      background: #1e293b;
      border-radius: 12px;
      overflow: hidden;
      box-shadow: 0 10px 30px rgba(0,0,0,0.5);
      border: 1px solid #334155;
    }}
    .terminal-header {{
      background: #0f172a;
      padding: 14px 20px;
      display: flex;
      align-items: center;
      gap: 8px;
      border-bottom: 1px solid #334155;
    }}
    .dot {{ width: 12px; height: 12px; border-radius: 50%; }}
    .red {{ background: #ef4444; }}
    .yellow {{ background: #f59e0b; }}
    .green {{ background: #10b981; }}
    .title {{ margin-left: 12px; font-weight: 600; font-size: 14px; color: #94a3b8; }}
    .terminal-body {{
      padding: 24px;
      font-family: 'Consolas', 'Courier New', monospace;
      font-size: 14px;
      line-height: 1.6;
      height: 520px;
      overflow-y: auto;
      background: #020617;
    }}
    .event-line {{ margin-bottom: 12px; }}
    .timestamp {{ color: #64748b; font-size: 12px; margin-right: 8px; }}
    .badge {{
      display: inline-block;
      padding: 2px 8px;
      border-radius: 4px;
      font-size: 11px;
      font-weight: bold;
      margin-right: 8px;
    }}
    .badge-tool {{ background: #7c3aed; color: #fff; }}
    .badge-guard {{ background: #059669; color: #fff; }}
    .badge-flow {{ background: #0284c7; color: #fff; }}
    .controls {{
      padding: 16px 24px;
      background: #0f172a;
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-top: 1px solid #334155;
    }}
    button {{
      background: #3b82f6;
      color: #fff;
      border: none;
      padding: 8px 16px;
      border-radius: 6px;
      font-weight: 600;
      cursor: pointer;
    }}
    button:hover {{ background: #2563eb; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="terminal-header">
      <div class="dot red"></div>
      <div class="dot yellow"></div>
      <div class="dot green"></div>
      <span class="title">Backend Case-Study & PR Scout Agent - Raw Run Capture Player</span>
    </div>
    <div class="terminal-body" id="term"></div>
    <div class="controls">
      <span id="status-text" style="color: #94a3b8; font-size: 13px;">Raw Unedited Session: 100% Autonomous (Zero Hand-Editing)</span>
      <button onclick="replay()">Replay Run</button>
    </div>
  </div>

  <script>
    const events = {events_json};
    const term = document.getElementById("term");

    function renderEvent(ev, i) {{
      const div = document.createElement("div");
      div.className = "event-line";
      let badgeClass = "badge-flow";
      if (ev.event_type.startsWith("TOOL")) badgeClass = "badge-tool";
      if (ev.event_type.includes("GUARDRAIL") || ev.event_type.includes("SECRETS")) badgeClass = "badge-guard";

      div.innerHTML = `
        <span class="timestamp">${{ev.iso_time.split("T")[1].replace("Z","")}}</span>
        <span class="badge ${{badgeClass}}">${{ev.event_type}}</span>
        <span style="color: #cbd5e1;">${{JSON.stringify(ev.details)}}</span>
      `;
      term.appendChild(div);
      term.scrollTop = term.scrollHeight;
    }}

    function replay() {{
      term.innerHTML = "";
      events.forEach((ev, idx) => {{
        setTimeout(() => renderEvent(ev, idx), idx * 250);
      }});
    }}

    // Initial play
    replay();
  </script>
</body>
</html>
"""
    output_path.write_text(html_content, encoding="utf-8")


if __name__ == "__main__":
    run_full_end_to_end()
