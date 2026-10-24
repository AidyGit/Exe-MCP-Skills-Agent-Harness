import asyncio
import json

import pytest

pytest.importorskip("claude_agent_sdk")
from conftest import ROOT, load_module  # noqa: E402
from shared.workspace import Workspace  # noqa: E402

import sys  # noqa: E402
sys.path.insert(0, str(ROOT / "SDK"))
sdk_tools = load_module("sdk_tools", ROOT / "SDK" / "tools.py")
sdk_agent = load_module("sdk_agent_mod", ROOT / "SDK" / "agent.py")


def test_options_follow_the_assignment(tmp_path):
    ws = Workspace.fresh(tmp_path / "w", memory_filename="CLAUDE.md")
    o = sdk_agent.build_options(ws)
    assert o.strict_mcp_config is True
    assert o.setting_sources == ["project"]
    assert o.system_prompt == sdk_agent.SYSTEM_PROMPT
    assert o.model == "claude-opus-5-5" and o.effort == "medium"
    assert o.allowed_tools == sdk_tools.ALLOWED and len(o.allowed_tools) >= 3
    assert o.tools == []  # no built-in tools


def test_tool_handler_ok_and_is_error(tmp_path):
    ws = Workspace.fresh(tmp_path / "w", memory_filename="CLAUDE.md")
    spec = next(s for s in sdk_tools.TOOL_SPECS if s["name"] == "update_job_status")
    handler = sdk_tools.make_handler(spec, ws)
    bad = asyncio.run(handler({"job": "ghost", "status": "offer"}))
    assert bad["is_error"] is True
    add = sdk_tools.make_handler(next(s for s in sdk_tools.TOOL_SPECS if s["name"] == "add_job"), ws)
    ok = asyncio.run(add({"company": "A", "title": "T"}))
    assert "is_error" not in ok and json.loads(ok["content"][0]["text"])["company"] == "A"


def test_memory_file_is_claude_md(tmp_path):
    ws = Workspace.fresh(tmp_path / "w", memory_filename="CLAUDE.md")
    h = sdk_tools.make_handler(next(s for s in sdk_tools.TOOL_SPECS if s["name"] == "save_memory"), ws)
    asyncio.run(h({"kind": "preference", "key": "stack", "value": ".NET"}))
    assert (ws.root / "CLAUDE.md").read_text().startswith("# Agent memory")


def test_replaces_markers_count_lines():
    from shared import linecount
    counts = linecount.count_sdk(ROOT / "SDK")
    for part in ("loop.py", "memory.py", "history.py", "tokens.py", "tools.py"):
        assert counts.get(part, 0) > 0, part


def test_turn_parses_result_message(tmp_path):
    from types import SimpleNamespace as NS
    from claude_agent_sdk import AssistantMessage, ResultMessage, TextBlock, ToolUseBlock

    class FakeSDKClient:
        async def query(self, text): pass

        async def receive_response(self):
            yield AssistantMessage(content=[ToolUseBlock(id="1", name="mcp__jobs__add_job", input={}),
                                            TextBlock(text="done")], model="m")
            yield ResultMessage(subtype="success", duration_ms=1, duration_api_ms=1, is_error=False,
                                num_turns=2, session_id="sid", total_cost_usd=0.5,
                                usage={"input_tokens": 10, "cache_read_input_tokens": 90,
                                       "cache_creation_input_tokens": 0, "output_tokens": 5})

    ws = Workspace.fresh(tmp_path / "w", memory_filename="CLAUDE.md")
    agent = sdk_agent.Agent(ws, client=FakeSDKClient())
    r = asyncio.run(agent.turn("x"))
    assert r["tools"] == ["add_job"] and r["reply"] == "done" and r["cache_hit_pct"] == 90.0
    assert r["model_calls"] == 2 and r["cost_usd"] == 0.5
