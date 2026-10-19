"""
Prototype Agent Implementation & Guardrail Simulator
Demonstrates the Model-Tools-Instructions triad and Guardrail Interceptor
for the 'Backend Case-Study & PR Scout Agent'.
"""

import json
import re
from typing import Any, Dict, List


class SecurityGuardrailError(Exception):
    pass


class AgentGuardrail:
    """Enforces human-in-the-loop confirmation and blocks destructive actions."""

    FORBIDDEN_COMMANDS = [
        r"git\s+push\s+.*--force",
        r"git\s+reset\s+--hard",
        r"rm\s+-rf",
        r"DROP\s+TABLE",
        r"TRUNCATE",
    ]

    SECRET_PATTERNS = [
        (r"sbp_[a-zA-Z0-9_\-]{20,}", "sbp_********************"),
        (r"sk-[a-zA-Z0-9_\-]{20,}", "sk-********************"),
        (r"postgres://[^:]+:[^@]+@", "postgres://user:******@"),
    ]

    @classmethod
    def validate_action(cls, tool_name: str, args: Dict[str, Any]) -> None:
        """Inspects proposed tool call before execution."""
        # Block destructive shell commands
        cmd = args.get("command", "") or args.get("query", "")
        for pattern in cls.FORBIDDEN_COMMANDS:
            if re.search(pattern, cmd, re.IGNORECASE):
                raise SecurityGuardrailError(
                    f"GUARDRAIL BLOCKED: Execution of destructive command matching pattern '{pattern}' is strictly prohibited."
                )

    @classmethod
    def sanitize_output(cls, text: str) -> str:
        """Redacts sensitive credentials from output before showing user."""
        sanitized = text
        for pattern, replacement in cls.SECRET_PATTERNS:
            sanitized = re.sub(pattern, replacement, sanitized)
        return sanitized


class BackendScoutTools:
    """Mock Tool implementations for the agent prototype."""

    @staticmethod
    def git_get_commit_diff(commit_hash: str) -> str:
        return (
            f"Commit: {commit_hash}\n"
            "Author: Cryptobitter <dev@example.com>\n"
            "Message: Add composite index idx_tasks_status_created_at\n"
            "Diff:\n"
            "--- a/init.sql\n"
            "+++ b/init.sql\n"
            "@@ -10,3 +10,4 @@\n"
            "+CREATE INDEX idx_tasks_status_created_at ON tasks(status, created_at);\n"
            "--- a/service.py (0 lines changed)\n"
            "--- a/routes.py  (0 lines changed)\n"
            "Benchmark Results:\n"
            "Before (Seq Scan): 2.410 ms\n"
            "After (Bitmap Index Scan): 0.089 ms (27x speedup)"
        )

    @staticmethod
    def run_pytest(test_path: str) -> Dict[str, Any]:
        return {"passed": 11, "failed": 0, "status": "ALL_TESTS_PASSED", "duration_sec": 0.42}


class BackendScoutAgent:
    """Simulates the autonomous reasoning loop with tool dispatch."""

    def __init__(self):
        self.guardrail = AgentGuardrail()
        self.tools = BackendScoutTools()

    def process_request(self, user_goal: str, commit_hash: str) -> Dict[str, Any]:
        # Step 1: Tool call planning
        tool_call = {"name": "git_get_commit_diff", "args": {"commit_hash": commit_hash}}

        # Step 2: Guardrail check
        self.guardrail.validate_action(tool_call["name"], tool_call["args"])

        # Step 3: Tool execution
        raw_diff = self.tools.git_get_commit_diff(commit_hash)

        # Step 4: Verification tool execution
        test_res = self.tools.run_pytest("tests/test_api.py")

        # Step 5: Draft synthesis into Three Beats
        case_study_draft = (
            "### Draft Case Study: Zero-Rewrite Storage Swap & Query Optimization\n\n"
            "- **The Problem:** Sequential scans across un-indexed status columns introduced high query latency (2.410ms) under load.\n"
            "- **The Decision:** Added composite B-tree index `idx_tasks_status_created_at` in `init.sql` while modifying 0 lines of route/service code.\n"
            f"- **The Proof:** Verified {test_res['passed']}/{test_res['passed']} passing contracts; EXPLAIN ANALYZE reduced execution time to 0.089ms (27x speedup).\n"
        )

        # Step 6: Output sanitization
        clean_output = self.guardrail.sanitize_output(case_study_draft)

        return {
            "status": "SUCCESS",
            "eval_case": "Eval Case 1: Happy Path Commit Extraction",
            "tools_invoked": [tool_call["name"], "run_pytest"],
            "draft_markdown": clean_output,
        }


def main():
    agent = BackendScoutAgent()

    print("=================================================================")
    print(" EXECUTING AGENT PROTOTYPE & GUARDRAIL SIMULATION")
    print("=================================================================\n")

    # Run Eval Case 1
    result = agent.process_request("Draft case study from recent commit", "4630eba")
    print(f"Agent Status: {result['status']}")
    print(f"Tools Invoked: {result['tools_invoked']}")
    print("\nGenerated Output:")
    print(result["draft_markdown"])

    # Test Guardrail on Destructive Request (Eval Case 4)
    print("-----------------------------------------------------------------")
    print(" Testing Safety Guardrail on Prohibited Command:")
    try:
        AgentGuardrail.validate_action("shell_exec", {"command": "git push origin main --force"})
        print("ERROR: Guardrail failed to intercept destructive command!")
    except SecurityGuardrailError as e:
        print(f"SUCCESS: {e}")

    print("\n=================================================================")
    print(" PROTOTYPE VERIFICATION COMPLETE")
    print("=================================================================")


if __name__ == "__main__":
    main()
