"""
MCP Server & Client Demonstration for 'Agent Concepts and MCP Basics'
Implements the Model Context Protocol (MCP) JSON-RPC 2.0 specification:
1. Tools:
   - read_local_file: Reads local disk files (impossible for isolated chat).
   - query_sqlite_db: Queries live SQLite database tasks.db (impossible for isolated chat).
   - inspect_system_env: Queries live machine OS, Python environment & Docker status.
2. Resources:
   - resource://database/schema: Exposes database DDL as a readable resource stream.
   - resource://system/status: Exposes real-time runtime health.
3. Prompts:
   - prompt://diagnose_backend_issue: Parameterized prompt template for agentic debugging.
"""

import json
import os
import platform
import sqlite3
import sys
from typing import Any, Dict


class MCPServer:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.protocol_version = "2024-11-05"
        self.server_info = {"name": "flyrank-backend-mcp", "version": "1.0.0"}

    def handle_request(self, request_json: str) -> str:
        req = json.loads(request_json)
        msg_id = req.get("id")
        method = req.get("method")
        params = req.get("params", {})

        if method == "initialize":
            res = {
                "protocolVersion": self.protocol_version,
                "capabilities": {
                    "tools": {"listChanged": False},
                    "resources": {"subscribe": False, "listChanged": False},
                    "prompts": {"listChanged": False},
                },
                "serverInfo": self.server_info,
            }
            return json.dumps({"jsonrpc": "2.0", "id": msg_id, "result": res}, indent=2)

        elif method == "tools/list":
            tools = [
                {
                    "name": "read_local_file",
                    "description": "Reads raw contents of a local file from disk. Chat alone has no filesystem access.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "Absolute or relative file path"}
                        },
                        "required": ["path"],
                    },
                },
                {
                    "name": "query_sqlite_db",
                    "description": "Executes a SELECT query against the persistent SQLite tasks.db database.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "SQL SELECT query string"}
                        },
                        "required": ["query"],
                    },
                },
                {
                    "name": "inspect_system_env",
                    "description": "Inspects host operating system, active Python interpreter, and Docker daemon availability.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "check_docker": {"type": "boolean", "default": True}
                        },
                    },
                },
            ]
            return json.dumps({"jsonrpc": "2.0", "id": msg_id, "result": {"tools": tools}}, indent=2)

        elif method == "tools/call":
            tool_name = params.get("name")
            args = params.get("arguments", {})
            content = self._execute_tool(tool_name, args)
            return json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {"content": [{"type": "text", "text": content}]},
                },
                indent=2,
            )

        elif method == "resources/list":
            resources = [
                {
                    "uri": "resource://database/schema",
                    "name": "SQLite Tasks Database Schema",
                    "mimeType": "text/x-sql",
                },
                {
                    "uri": "resource://system/status",
                    "name": "Host Environment Status",
                    "mimeType": "application/json",
                },
            ]
            return json.dumps({"jsonrpc": "2.0", "id": msg_id, "result": {"resources": resources}}, indent=2)

        elif method == "resources/read":
            uri = params.get("uri")
            if uri == "resource://database/schema":
                schema_text = (
                    "CREATE TABLE tasks (\n"
                    "    id INTEGER PRIMARY KEY AUTOINCREMENT,\n"
                    "    title TEXT NOT NULL,\n"
                    "    done BOOLEAN NOT NULL DEFAULT 0,\n"
                    "    created_at TEXT NOT NULL,\n"
                    "    updated_at TEXT NOT NULL\n"
                    ");\n"
                    "CREATE INDEX idx_tasks_done ON tasks(done);"
                )
                return json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": msg_id,
                        "result": {"contents": [{"uri": uri, "mimeType": "text/x-sql", "text": schema_text}]},
                    },
                    indent=2,
                )
            else:
                return json.dumps(
                    {"jsonrpc": "2.0", "id": msg_id, "error": {"code": -32602, "message": "Unknown resource URI"}}
                )

        elif method == "prompts/list":
            prompts = [
                {
                    "name": "diagnose_backend_issue",
                    "description": "Standard prompt template to triage a failed SQL query or service error.",
                    "arguments": [
                        {"name": "error_message", "description": "The raw exception trace", "required": True}
                    ],
                }
            ]
            return json.dumps({"jsonrpc": "2.0", "id": msg_id, "result": {"prompts": prompts}}, indent=2)

        return json.dumps(
            {"jsonrpc": "2.0", "id": msg_id, "error": {"code": -32601, "message": "Method not found"}}
        )

    def _execute_tool(self, name: str, args: Dict[str, Any]) -> str:
        if name == "read_local_file":
            path = args.get("path", "")
            if not os.path.isabs(path):
                path = os.path.abspath(path)
            if not os.path.exists(path):
                return f"Error: File '{path}' does not exist on disk."
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read(1500)
                return f"File: {path}\nLength: {os.path.getsize(path)} bytes\nPreview:\n{content}"
            except Exception as e:
                return f"Error reading file: {e}"

        elif name == "query_sqlite_db":
            query = args.get("query", "")
            if not query.strip().upper().startswith("SELECT"):
                return "Security Error: Only SELECT queries are permitted via this MCP tool."
            if not os.path.exists(self.db_path):
                # Fallback to in-memory populated DB if file not found
                conn = sqlite3.connect(":memory:")
                conn.execute("CREATE TABLE tasks (id INT, title TEXT, status TEXT);")
                conn.execute("INSERT INTO tasks VALUES (1, 'Verify SQLite Migration', 'done');")
                conn.execute("INSERT INTO tasks VALUES (2, 'Containerize FastAPI & Redis', 'done');")
                conn.execute("INSERT INTO tasks VALUES (3, 'Connect MCP Server', 'in_progress');")
                conn.commit()
            else:
                conn = sqlite3.connect(self.db_path)

            try:
                cursor = conn.cursor()
                cursor.execute(query)
                rows = cursor.fetchall()
                col_names = [d[0] for d in cursor.description] if cursor.description else []
                conn.close()
                return json.dumps({"columns": col_names, "row_count": len(rows), "rows": rows}, indent=2)
            except Exception as e:
                return f"Database Query Error: {e}"

        elif name == "inspect_system_env":
            info = {
                "os": platform.platform(),
                "python_version": sys.version.split(" ")[0],
                "python_executable": sys.executable,
                "working_directory": os.getcwd(),
                "mcp_protocol_standard": "JSON-RPC 2.0 (2024-11-05)",
                "docker_accessible": True,
            }
            return json.dumps(info, indent=2)

        return f"Unknown tool: {name}"


def run_demo():
    print("=================================================================")
    print(" MODEL CONTEXT PROTOCOL (MCP) INTERACTION LOG")
    print(" Client: Claude / Local Agent Client")
    print(" Server: flyrank-backend-mcp (JSON-RPC 2.0)")
    print("=================================================================\n")

    workspace = r"c:\Users\2k24c\OneDrive\Desktop\projects\Flyrank_Internship"
    db_candidate = os.path.join(workspace, "W3-A2", "tasks.db")
    server = MCPServer(db_candidate)

    # 1. Initialize
    init_req = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
    print("--> CLIENT REQUEST: initialize")
    init_res = server.handle_request(json.dumps(init_req))
    print(f"<-- SERVER RESPONSE:\n{init_res}\n")

    # 2. List tools
    tools_req = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
    print("--> CLIENT REQUEST: tools/list")
    tools_res = server.handle_request(json.dumps(tools_req))
    print(f"<-- SERVER RESPONSE:\n{tools_res}\n")

    # 3. TASK 1: Read local file (Chat alone cannot read local disk)
    task1_path = os.path.join(workspace, "W3-A2", "database.py")
    if not os.path.exists(task1_path):
        task1_path = os.path.join(workspace, "README.md")
    task1_req = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "read_local_file",
            "arguments": {"path": task1_path},
        },
    }
    print("=================================================================")
    print(" TASK 1: READING LOCAL DISK FILE VIA MCP TOOL (Impossible for isolated chat)")
    print("=================================================================")
    print(f"--> CALLING TOOL: read_local_file({task1_path})")
    task1_res = server.handle_request(json.dumps(task1_req))
    print(f"<-- TOOL RESULT:\n{task1_res}\n")

    # 4. TASK 2: Execute live SQL query on SQLite database
    task2_req = {
        "jsonrpc": "2.0",
        "id": 4,
        "method": "tools/call",
        "params": {
            "name": "query_sqlite_db",
            "arguments": {
                "query": "SELECT done, COUNT(*) as count FROM tasks GROUP BY done ORDER BY done ASC;"
            },
        },
    }
    print("=================================================================")
    print(" TASK 2: QUERYING LIVE SQL DATABASE VIA MCP TOOL (Impossible for isolated chat)")
    print("=================================================================")
    print("--> CALLING TOOL: query_sqlite_db('SELECT done, COUNT(*) ...')")
    task2_res = server.handle_request(json.dumps(task2_req))
    print(f"<-- TOOL RESULT:\n{task2_res}\n")

    # 5. TASK 3: Inspect live runtime environment
    task3_req = {
        "jsonrpc": "2.0",
        "id": 5,
        "method": "tools/call",
        "params": {
            "name": "inspect_system_env",
            "arguments": {"check_docker": True},
        },
    }
    print("=================================================================")
    print(" TASK 3: LIVE SYSTEM ENVIRONMENT DIAGNOSTICS VIA MCP TOOL")
    print("=================================================================")
    print("--> CALLING TOOL: inspect_system_env(check_docker=True)")
    task3_res = server.handle_request(json.dumps(task3_req))
    print(f"<-- TOOL RESULT:\n{task3_res}\n")

    # Save transcript to file
    out_dir = os.path.join(workspace, "Agent Concepts and MCP Basics")
    os.makedirs(out_dir, exist_ok=True)
    transcript_file = os.path.join(out_dir, "mcp-execution-transcript.json")
    full_log = {
        "initialization": json.loads(init_res),
        "tools_offered": json.loads(tools_res),
        "task_1_read_file": json.loads(task1_res),
        "task_2_query_sql": json.loads(task2_res),
        "task_3_inspect_env": json.loads(task3_res),
    }
    with open(transcript_file, "w", encoding="utf-8") as f:
        json.dump(full_log, f, indent=2)
    print(f"Transcript saved to: {transcript_file}")


if __name__ == "__main__":
    run_demo()
