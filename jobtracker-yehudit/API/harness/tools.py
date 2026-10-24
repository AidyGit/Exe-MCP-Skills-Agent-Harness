"""Tool schemas and dispatch. Errors go back to the model as is_error results."""
from shared.tools_core import TOOL_SPECS, run_tool

from .trace import log


def schemas():
    return [dict(t) for t in TOOL_SPECS]


def dispatch(ws, block, fetcher=None):
    """Run one tool_use block -> a tool_result block (always, even on failure)."""
    log("tools.py", f"dispatch {block['name']} {block['input']}")
    try:
        content, is_error = run_tool(ws, block["name"], block["input"], fetcher), False
    except Exception as e:  # noqa: BLE001 - the model should see every failure
        content, is_error = f"{type(e).__name__}: {e}", True
        log("tools.py", f"tool error -> model: {content}")
    result = {"type": "tool_result", "tool_use_id": block["id"], "content": content}
    if is_error:
        result["is_error"] = True
    return result
