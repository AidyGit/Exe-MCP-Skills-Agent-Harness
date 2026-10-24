"""Job-search agent on the Claude Agent SDK: Claude Code runs the harness, we only configure it."""
import dataclasses
import time

from claude_agent_sdk import (AssistantMessage, ClaudeAgentOptions, ClaudeSDKClient,
                              ResultMessage, TextBlock, ToolUseBlock)

import tools as sdk_tools

MODEL = "claude-opus-5-5"
EFFORT = "medium"

SYSTEM_PROMPT = """You are a personal job-search assistant for a software engineer.
You keep her applications in a tracker and remember her search criteria between sessions.
Rules:
- Use tools for every change to the tracker; never claim a change you did not make.
- Save durable criteria with save_memory (kind=preference), decisions as kind=decision.
- Her saved criteria are in CLAUDE.md. If a request contradicts a saved preference, do NOT call add_job.
  Point out the conflict briefly and ask whether she wants to proceed or change her criteria.
- Be concise. Reply in the language the user writes in."""


def build_options(ws, resume=None, fetcher=None):
    fields = {f.name for f in dataclasses.fields(ClaudeAgentOptions)}
    kwargs = dict(
        model=MODEL,                                          # same model as the API version
        system_prompt=SYSTEM_PROMPT,                          # own system prompt, not the Claude Code preset
        mcp_servers={sdk_tools.SERVER_NAME: sdk_tools.build_server(ws, fetcher)},
        allowed_tools=sdk_tools.ALLOWED,                      # narrow tool list ...
        tools=[],                                             # ... and no built-in Claude Code tools
        strict_mcp_config=True,                               # ignore any other MCP config on the machine
        setting_sources=["project"],                          # replaces: memory.py (loads CLAUDE.md from cwd)
        cwd=str(ws.root),
        resume=resume,                                        # replaces: history.py (resume=session_id)
        permission_mode="bypassPermissions",
        max_turns=12,                                         # replaces: loop.py (MAX_STEPS guard)
    )
    if "effort" in fields:
        kwargs["effort"] = EFFORT
    return ClaudeAgentOptions(**kwargs)


class Agent:
    def __init__(self, ws, resume=None, fetcher=None, client=None):
        self.ws = ws
        self.session_id = None
        self.client = client or ClaudeSDKClient(build_options(ws, resume, fetcher))
        self._prev_cost = 0.0

    async def __aenter__(self):
        await self.client.connect()
        return self

    async def __aexit__(self, *exc):
        await self.client.disconnect()

    async def turn(self, user_text):
        started = time.time()
        await self.client.query(user_text)                    # replaces: loop.py (the whole loop)
        text, used, result = [], [], None
        async for msg in self.client.receive_response():      # replaces: loop.py (streams until the result)
            if isinstance(msg, AssistantMessage):
                for b in msg.content:
                    if isinstance(b, TextBlock):
                        text.append(b.text)
                    elif isinstance(b, ToolUseBlock):
                        used.append(b.name.split("__")[-1])
            elif isinstance(msg, ResultMessage):
                result = msg
        self.session_id = result.session_id
        u = result.usage or {}
        cost = result.total_cost_usd or 0.0
        delta = cost - self._prev_cost if cost >= self._prev_cost else cost  # replaces: tokens.py (cost per turn)
        self._prev_cost = cost
        inp, cr, cw = (u.get("input_tokens", 0), u.get("cache_read_input_tokens", 0),
                       u.get("cache_creation_input_tokens", 0))
        total_in = inp + cr + cw
        return {"reply": "".join(text), "input_tokens": inp, "cache_read_tokens": cr,
                "cache_write_tokens": cw, "output_tokens": u.get("output_tokens", 0),
                "model_calls": result.num_turns, "tools": used, "cost_usd": round(delta, 6),
                "total_cost_usd_raw": cost, "seconds": round(time.time() - started, 2),
                "cache_hit_pct": round(100 * cr / total_in, 1) if total_in else 0.0}
