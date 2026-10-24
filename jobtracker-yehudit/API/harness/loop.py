"""The agent loop: call the model while stop_reason == "tool_use"."""
from . import caching, tools
from .trace import log

MAX_STEPS = 12


def _blocks(response):
    out = []
    for b in response.content:
        if b.type == "text":
            out.append({"type": "text", "text": b.text})
        elif b.type == "tool_use":
            out.append({"type": "tool_use", "id": b.id, "name": b.name, "input": b.input})
    return out


def run(client, model, system, messages, history, meter, ws, create_kwargs, fetcher=None):
    """Mutates `messages`, appends every new message to `history`. Returns (final_text, tools_used, last_input)."""
    used, last_input = [], 0
    for step in range(MAX_STEPS):
        sys_blocks, tool_defs, msgs = caching.apply(system, tools.schemas(), messages)
        log("loop.py", f"model call #{step + 1} ({len(msgs)} messages)")
        resp = client.messages.create(model=model, max_tokens=2000, system=sys_blocks,
                                      tools=tool_defs, messages=msgs, **create_kwargs)
        meter.record(resp.usage)
        u = resp.usage
        last_input = (u.input_tokens or 0) + (u.cache_read_input_tokens or 0) + (u.cache_creation_input_tokens or 0)
        assistant = {"role": "assistant", "content": _blocks(resp)}
        messages.append(assistant)
        history.append(assistant)
        if resp.stop_reason != "tool_use":
            text = "".join(b["text"] for b in assistant["content"] if b["type"] == "text")
            return text, used, last_input
        calls = [b for b in assistant["content"] if b["type"] == "tool_use"]
        used += [c["name"] for c in calls]
        results = [tools.dispatch(ws, c, fetcher) for c in calls]
        user = {"role": "user", "content": results}  # ALL results in ONE message
        messages.append(user)
        history.append(user)
    raise RuntimeError(f"agent did not finish within {MAX_STEPS} model calls")
