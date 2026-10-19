"""
Live Tool Registry and System Connectors for Backend Case-Study & PR Scout Agent.
Implements real connections to local Git CLI, local filesystem, test runner,
and MCP (Model Context Protocol) tool schema standards.
"""

import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


class ToolExecutionError(Exception):
    pass


class BackendScoutTools:
    """Live tools interfacing directly with the local repository and operating system."""

    def __init__(self, repo_root: Optional[str] = None):
        if repo_root is None:
            # Default to the root repository (one directory up from 'build the agent')
            current_dir = Path(__file__).resolve().parent
            self.repo_root = current_dir.parent
        else:
            self.repo_root = Path(repo_root).resolve()

        self.drafts_dir = Path(__file__).resolve().parent / "drafts"
        self.drafts_dir.mkdir(parents=True, exist_ok=True)

    def git_get_commit_diff(self, commit_hash: str) -> Dict[str, Any]:
        """
        Fetches commit metadata, changed file list, file stat summary, and unified diff
        for a specific Git commit hash using the local Git CLI.
        """
        try:
            # 1. Fetch metadata and subject
            meta_cmd = [
                "git", "show", "-s",
                "--format=%H|%h|%an|%ae|%ad|%s%n%b",
                "--date=iso",
                commit_hash
            ]
            meta_res = subprocess.run(
                meta_cmd,
                cwd=str(self.repo_root),
                capture_output=True,
                text=True,
                check=True,
                encoding="utf-8",
                errors="replace"
            )
            meta_lines = meta_res.stdout.strip().split("\n")
            header_parts = meta_lines[0].split("|")
            full_hash = header_parts[0] if len(header_parts) > 0 else commit_hash
            short_hash = header_parts[1] if len(header_parts) > 1 else commit_hash[:7]
            author = header_parts[2] if len(header_parts) > 2 else "Unknown"
            email = header_parts[3] if len(header_parts) > 3 else ""
            date = header_parts[4] if len(header_parts) > 4 else ""
            subject = header_parts[5] if len(header_parts) > 5 else ""
            body = "\n".join(meta_lines[1:]).strip()

            # 2. Fetch list of changed files and stats
            stat_cmd = ["git", "show", "--stat", "--oneline", commit_hash]
            stat_res = subprocess.run(
                stat_cmd,
                cwd=str(self.repo_root),
                capture_output=True,
                text=True,
                check=True,
                encoding="utf-8",
                errors="replace"
            )

            # 3. Fetch unified patch diff (trimmed if overly large)
            diff_cmd = ["git", "show", "--patch", "--unified=3", commit_hash]
            diff_res = subprocess.run(
                diff_cmd,
                cwd=str(self.repo_root),
                capture_output=True,
                text=True,
                check=True,
                encoding="utf-8",
                errors="replace"
            )

            raw_diff = diff_res.stdout
            # Extract changed file names
            name_cmd = ["git", "show", "--name-only", "--format=", commit_hash]
            name_res = subprocess.run(
                name_cmd,
                cwd=str(self.repo_root),
                capture_output=True,
                text=True,
                check=True,
                encoding="utf-8",
                errors="replace"
            )
            files_changed = [f.strip() for f in name_res.stdout.strip().split("\n") if f.strip()]

            return {
                "success": True,
                "commit_hash": short_hash,
                "full_hash": full_hash,
                "author": author,
                "email": email,
                "date": date,
                "subject": subject,
                "body": body,
                "files_changed": files_changed,
                "stat_summary": stat_res.stdout.strip(),
                "diff_snippet": raw_diff[:8000],  # Bound context window
                "total_diff_length": len(raw_diff)
            }
        except subprocess.CalledProcessError as e:
            return {
                "success": False,
                "error": f"Git CLI execution error: {e.stderr.strip() or str(e)}"
            }
        except Exception as ex:
            return {"success": False, "error": str(ex)}

    def git_log_recent(self, limit: int = 5, query: str = "") -> Dict[str, Any]:
        """
        Queries recent git commits from the local repository.
        Optionally filters commit subjects by a search query.
        """
        try:
            cmd = ["git", "log", f"-n{max(1, min(limit, 20))}", "--pretty=format:%h|%ad|%s", "--date=short"]
            if query:
                cmd.extend(["--grep", query])

            res = subprocess.run(
                cmd,
                cwd=str(self.repo_root),
                capture_output=True,
                text=True,
                check=True,
                encoding="utf-8",
                errors="replace"
            )
            raw_entries = res.stdout.strip().split("\n")
            commits = []
            for entry in raw_entries:
                if not entry.strip():
                    continue
                parts = entry.split("|", 2)
                if len(parts) == 3:
                    commits.append({
                        "commit_hash": parts[0].strip(),
                        "date": parts[1].strip(),
                        "subject": parts[2].strip()
                    })

            return {
                "success": True,
                "count": len(commits),
                "commits": commits,
                "query": query
            }
        except subprocess.CalledProcessError as e:
            return {"success": False, "error": e.stderr.strip() or str(e)}
        except Exception as ex:
            return {"success": False, "error": str(ex)}

    def read_local_file(self, path: str) -> Dict[str, Any]:
        """
        Reads local repository files (e.g. database DDL, test files, configs).
        Enforces sandbox boundaries within repository directory.
        """
        target = (self.repo_root / path).resolve()
        try:
            # Boundary check
            if not str(target).startswith(str(self.repo_root)):
                return {"success": False, "error": f"Access denied: path '{path}' escapes repository boundary."}

            if not target.exists():
                return {"success": False, "error": f"File not found: '{path}'"}

            if target.is_dir():
                return {"success": False, "error": f"Target path '{path}' is a directory, not a file."}

            content = target.read_text(encoding="utf-8", errors="replace")
            return {
                "success": True,
                "path": path,
                "size_bytes": len(content),
                "content": content[:10000]  # Safe length window
            }
        except Exception as ex:
            return {"success": False, "error": str(ex)}

    def list_directory(self, path: str = ".") -> Dict[str, Any]:
        """
        Lists files and subdirectories at the given relative path within repository.
        Used for autonomous self-correction when referenced files are moved or renamed.
        """
        target = (self.repo_root / path).resolve()
        try:
            if not str(target).startswith(str(self.repo_root)):
                return {"success": False, "error": f"Access denied: path '{path}' escapes repository boundary."}

            if not target.exists():
                return {"success": False, "error": f"Directory not found: '{path}'"}

            entries = []
            for item in target.iterdir():
                # Skip hidden/virtualenv directories for clarity
                if item.name.startswith(".") or item.name in ["venv", "__pycache__", "node_modules"]:
                    continue
                entries.append({
                    "name": item.name,
                    "is_directory": item.is_dir(),
                    "size_bytes": item.stat().st_size if item.is_file() else None
                })

            return {
                "success": True,
                "directory": path,
                "entries": entries
            }
        except Exception as ex:
            return {"success": False, "error": str(ex)}

    def run_test_suite(self, test_path: str = "") -> Dict[str, Any]:
        """
        Executes automated tests in the local environment using standard unittest or pytest.
        Returns parsed test metrics: passed, failed, duration, and status.
        """
        start_time = time.time()
        try:
            if test_path:
                full_test_path = (self.repo_root / test_path).resolve()
                if not full_test_path.exists():
                    return {
                        "success": False,
                        "error": f"Test target '{test_path}' does not exist on disk."
                    }
                cmd = ["python", "-m", "unittest", str(full_test_path)]
            else:
                default_target = self.repo_root / "build the agent" / "tests" / "test_contracts.py"
                if default_target.exists():
                    cmd = ["python", "-m", "unittest", str(default_target)]
                else:
                    cmd = ["python", "-m", "unittest", "discover", "-s", str(self.repo_root / "build the agent" / "tests")]

            res = subprocess.run(
                cmd,
                cwd=str(self.repo_root),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace"
            )
            duration = round(time.time() - start_time, 3)

            output = (res.stdout + "\n" + res.stderr).strip()
            # Simple parser for unittest / pytest output
            passed = "OK" in output or "passed" in output.lower()
            exit_code = res.returncode

            return {
                "success": True,
                "passed": passed and exit_code == 0,
                "exit_code": exit_code,
                "duration_sec": duration,
                "raw_output": output[-1500:] if len(output) > 1500 else output
            }
        except Exception as ex:
            return {
                "success": False,
                "error": str(ex),
                "duration_sec": round(time.time() - start_time, 3)
            }

    def stage_case_study(self, slug: str, content: str) -> Dict[str, Any]:
        """
        Writes the generated Three-Beat case study markdown to the local staging directory.
        Human-in-the-loop review occurs here prior to merging into live portfolio.
        """
        try:
            # Clean slug
            clean_slug = "".join(c for c in slug if c.isalnum() or c in ("-", "_")).lower()
            if not clean_slug:
                clean_slug = f"case_study_{int(time.time())}"

            target_file = self.drafts_dir / f"{clean_slug}.md"
            target_file.write_text(content, encoding="utf-8")

            return {
                "success": True,
                "slug": clean_slug,
                "file_path": str(target_file),
                "relative_path": f"build the agent/drafts/{clean_slug}.md",
                "bytes_written": len(content.encode("utf-8")),
                "status": "STAGED_FOR_HUMAN_REVIEW"
            }
        except Exception as ex:
            return {"success": False, "error": str(ex)}


class ToolRegistry:
    """Manages tool metadata, schemas, and dispatch."""

    def __init__(self, backend_tools: BackendScoutTools):
        self.tools = backend_tools
        self.definitions: Dict[str, Dict[str, Any]] = {
            "git_get_commit_diff": {
                "name": "git_get_commit_diff",
                "description": "Fetches commit metadata, changed files, stat summary, and diff for a commit hash.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "commit_hash": {"type": "string", "description": "Git commit hash (short or full)"}
                    },
                    "required": ["commit_hash"]
                },
                "handler": self.tools.git_get_commit_diff
            },
            "git_log_recent": {
                "name": "git_log_recent",
                "description": "Lists recent commits from the repository, optionally filtered by keyword.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "limit": {"type": "integer", "description": "Max number of commits to return (default 5)"},
                        "query": {"type": "string", "description": "Optional search filter for commit messages"}
                    }
                },
                "handler": self.tools.git_log_recent
            },
            "read_local_file": {
                "name": "read_local_file",
                "description": "Reads source code, database DDL schemas, or configs from the repository.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Relative file path from repository root"}
                    },
                    "required": ["path"]
                },
                "handler": self.tools.read_local_file
            },
            "list_directory": {
                "name": "list_directory",
                "description": "Lists directory contents to inspect file structure or locate renamed files.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Relative folder path (default root '.')"}
                    }
                },
                "handler": self.tools.list_directory
            },
            "run_test_suite": {
                "name": "run_test_suite",
                "description": "Executes automated test suite to gather pass/fail proof metrics.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "test_path": {"type": "string", "description": "Optional relative path to specific test file"}
                    }
                },
                "handler": self.tools.run_test_suite
            },
            "stage_case_study": {
                "name": "stage_case_study",
                "description": "Saves verified Three-Beat case study markdown to the local drafts staging directory.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "slug": {"type": "string", "description": "File slug name without extension"},
                        "content": {"type": "string", "description": "Full markdown content"}
                    },
                    "required": ["slug", "content"]
                },
                "handler": self.tools.stage_case_study
            }
        }

    def dispatch(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Executes a tool by name with arguments."""
        if tool_name not in self.definitions:
            return {"success": False, "error": f"Unknown tool: '{tool_name}'"}
        handler = self.definitions[tool_name]["handler"]
        return handler(**args)

    def get_mcp_tools(self) -> List[Dict[str, Any]]:
        """Returns standard MCP (Model Context Protocol) tool definitions."""
        mcp_tools = []
        for name, spec in self.definitions.items():
            mcp_tools.append({
                "name": spec["name"],
                "description": spec["description"],
                "inputSchema": spec["parameters"]
            })
        return mcp_tools
