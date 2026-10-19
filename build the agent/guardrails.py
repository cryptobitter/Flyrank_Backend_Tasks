"""
Guardrails and Safety Interceptors for Backend Case-Study & PR Scout Agent.
Enforces hard system boundaries, blocks destructive operations, masks secrets,
and coordinates human-in-the-loop review.
"""

import re
from typing import Any, Dict, List, Tuple


class SecurityGuardrailError(Exception):
    """Raised when an agent action violates safety policies."""
    pass


class AgentGuardrails:
    """Enforces human-in-the-loop confirmation and blocks destructive actions."""

    # Prohibited destructive shell and database commands
    FORBIDDEN_COMMANDS = [
        r"git\s+push\s+.*--force",
        r"git\s+push\s+-f",
        r"git\s+reset\s+--hard",
        r"git\s+checkout\s+\.",
        r"git\s+clean\s+-fd",
        r"rm\s+-rf",
        r"rmdir\s+/s\s+/q",
        r"del\s+/f\s+/s\s+/q",
        r"DROP\s+TABLE",
        r"DROP\s+DATABASE",
        r"TRUNCATE",
        r"DELETE\s+FROM",
    ]

    # Sensitive credential redaction patterns: (regex, replacement)
    SECRET_PATTERNS: List[Tuple[str, str]] = [
        (r"sbp_[a-zA-Z0-9_\-]{20,}", "sbp_********************"),
        (r"sk-[a-zA-Z0-9_\-]{20,}", "sk-********************"),
        (r"ghp_[a-zA-Z0-9]{20,}", "ghp_********************"),
        (r"postgres(?:ql)?:\/\/([^:]+):([^@]+)@", r"postgres://\1:******@"),
        (r"Bearer\s+[a-zA-Z0-9_\-\.]{25,}", "Bearer ********************"),
        (r"(?i)api[_-]?key\s*[:=]\s*['\"][a-zA-Z0-9_\-]{16,}['\"]", 'api_key="******"'),
        (r"(?i)password\s*[:=]\s*['\"][^'\"]+['\"]", 'password="******"'),
    ]

    @classmethod
    def validate_action(cls, tool_name: str, args: Dict[str, Any]) -> None:
        """
        Inspects proposed tool call before execution.
        Raises SecurityGuardrailError if a prohibited pattern is detected.
        """
        # Inspect all string arguments for destructive command injection
        for key, value in args.items():
            if isinstance(value, str):
                for pattern in cls.FORBIDDEN_COMMANDS:
                    if re.search(pattern, value, re.IGNORECASE):
                        raise SecurityGuardrailError(
                            f"GUARDRAIL BLOCKED: Execution of destructive command matching '{pattern}' "
                            f"in argument '{key}' is strictly prohibited. Agent permissions are strictly read-only."
                        )

        # Scoped path verification for write operations
        if tool_name == "stage_case_study":
            slug = args.get("slug", "")
            if ".." in slug or "/" in slug or "\\" in slug:
                raise SecurityGuardrailError(
                    f"GUARDRAIL BLOCKED: Path traversal attempt detected in slug '{slug}'."
                )

    @classmethod
    def sanitize_output(cls, text: str) -> Tuple[str, List[str]]:
        """
        Redacts sensitive credentials from output before showing user or writing files.
        Returns the sanitized text and a list of detected redaction warnings.
        """
        sanitized = text
        warnings = []

        for pattern, replacement in cls.SECRET_PATTERNS:
            matches = re.findall(pattern, sanitized)
            if matches:
                warnings.append(f"Redacted sensitive secret matching pattern: {pattern}")
                sanitized = re.sub(pattern, replacement, sanitized)

        return sanitized, warnings
