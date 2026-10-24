"""The same six tools as in the API version, exposed to Claude Code as an in-process MCP server."""
from claude_agent_sdk import create_sdk_mcp_server, tool

from shared.tools_core import TOOL_SPECS, run_tool
from shared.workspace import Workspace

SERVER_NAME = "jobs"


def make_handler(spec, ws, fetcher=None):
    async def handler(args):
        try:
            return {"content": [{"type": "text", "text": run_tool(ws, spec["name"], args, fetcher)}]}
        except Exception as e:  # noqa: BLE001
            return {"content": [{"type": "text", "text": f"{type(e).__name__}: {e}"}], "is_error": True}  # replaces: tools.py (is_error)
    return handler


def build_server(ws: Workspace, fetcher=None):
    sdk_tools = [tool(s["name"], s["description"], s["input_schema"])(make_handler(s, ws, fetcher))  # replaces: tools.py (schemas + dispatch)
                 for s in TOOL_SPECS]
    return create_sdk_mcp_server(SERVER_NAME, "1.0.0", sdk_tools)


ALLOWED = [f"mcp__{SERVER_NAME}__{s['name']}" for s in TOOL_SPECS]
