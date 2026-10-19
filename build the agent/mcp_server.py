"""
MCP Server for Backend Case-Study & PR Scout Agent
Exposes the agent's live Git, filesystem, and test runner tools
via standard Model Context Protocol (JSON-RPC 2.0 over STDIO).
Conforms to Anthropic & MCP official specification.
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict

from guardrails import AgentGuardrails, SecurityGuardrailError
from tools import BackendScoutTools, ToolRegistry


class BackendScoutMCPServer:
    """Model Context Protocol (MCP) Server for the Scout Agent."""

    def __init__(self, repo_root: str = None):
        self.tools_backend = BackendScoutTools(repo_root=repo_root)
        self.registry = ToolRegistry(self.tools_backend)
        self.guardrails = AgentGuardrails()
        self.protocol_version = "2024-11-05"
        self.server_info = {
            "name": "backend-pr-scout-mcp",
            "version": "1.0.0",
            "description": "Live Git CLI and test runner MCP connector for backend portfolio generation"
        }

    def handle_message(self, line: str) -> Dict[str, Any]:
        """Handles incoming JSON-RPC 2.0 request."""
        try:
            req = json.loads(line)
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": f"Parse error: {str(e)}"}
            }

        msg_id = req.get("id")
        method = req.get("method")
        params = req.get("params", {})

        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "protocolVersion": self.protocol_version,
                    "capabilities": {
                        "tools": {"listChanged": False},
                        "resources": {"subscribe": False, "listChanged": False},
                        "prompts": {"listChanged": False}
                    },
                    "serverInfo": self.server_info
                }
            }

        elif method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "tools": self.registry.get_mcp_tools()
                }
            }

        elif method == "tools/call":
            tool_name = params.get("name")
            tool_args = params.get("arguments", {})

            # Guardrail inspection
            try:
                self.guardrails.validate_action(tool_name, tool_args)
            except SecurityGuardrailError as sge:
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "content": [{"type": "text", "text": f"GUARDRAIL BLOCKED: {str(sge)}"}],
                        "isError": True
                    }
                }

            # Execute tool
            exec_res = self.registry.dispatch(tool_name, tool_args)
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps(exec_res, indent=2)}],
                    "isError": not exec_res.get("success", False)
                }
            }

        elif method == "resources/list":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "resources": [
                        {
                            "uri": "resource://repo/recent-commits",
                            "name": "Recent Git Commits",
                            "mimeType": "application/json"
                        },
                        {
                            "uri": "resource://system/health",
                            "name": "Backend Test & Environment Health",
                            "mimeType": "application/json"
                        }
                    ]
                }
            }

        elif method == "resources/read":
            uri = params.get("uri")
            if uri == "resource://repo/recent-commits":
                commits = self.tools_backend.git_log_recent(limit=5)
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "contents": [{
                            "uri": uri,
                            "mimeType": "application/json",
                            "text": json.dumps(commits, indent=2)
                        }]
                    }
                }
            elif uri == "resource://system/health":
                tests = self.tools_backend.run_test_suite()
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "contents": [{
                            "uri": uri,
                            "mimeType": "application/json",
                            "text": json.dumps(tests, indent=2)
                        }]
                    }
                }
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {"code": -32602, "message": f"Resource not found: {uri}"}
            }

        elif method == "prompts/list":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "prompts": [
                        {
                            "name": "scout_commit",
                            "description": "Analyze commit diff and synthesize Three-Beat case study",
                            "arguments": [
                                {
                                    "name": "commit_hash",
                                    "description": "Git commit hash",
                                    "required": True
                                }
                            ]
                        }
                    ]
                }
            }

        else:
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {"code": -32601, "message": f"Method not found: {method}"}
            }

    def run_stdio_server(self):
        """Standard STDIO loop for MCP clients."""
        for line in sys.stdin:
            if not line.strip():
                continue
            res = self.handle_message(line.strip())
            sys.stdout.write(json.dumps(res) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    server = BackendScoutMCPServer()
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        # Self-test initialization and tool listing
        print("Testing MCP initialize...")
        init_req = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
        print(server.handle_message(init_req))

        print("\nTesting MCP tools/list...")
        tools_req = json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        print(server.handle_message(tools_req))
    else:
        server.run_stdio_server()
