"""Prompt caching: places cache_control breakpoints (tools, system, last message)."""
import copy

from .trace import log

CC = {"type": "ephemeral"}


def apply(system, tools, messages):
    """Return (system_blocks, tools, messages) with breakpoints; inputs are not mutated."""
    system_blocks = [{"type": "text", "text": system, "cache_control": CC}]
    tools = [dict(t) for t in tools]
    if tools:
        tools[-1]["cache_control"] = CC
    messages = list(messages)
    if messages:
        last = copy.deepcopy(messages[-1])
        if isinstance(last["content"], str):
            last["content"] = [{"type": "text", "text": last["content"]}]
        last["content"][-1]["cache_control"] = CC
        messages[-1] = last
    log("caching.py", "breakpoints: tools[-1], system, last message block")
    return system_blocks, tools, messages
