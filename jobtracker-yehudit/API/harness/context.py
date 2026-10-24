"""Context engineering: what enters each turn. Not the whole state - only what matters now."""
from shared.jobs import JobStore

from . import memory
from .trace import log

SYSTEM_PROMPT = """You are a personal job-search assistant for a software engineer.
You keep her applications in a tracker and remember her search criteria between sessions.
Rules:
- Use tools for every change to the tracker; never claim a change you did not make.
- Save durable criteria with save_memory (kind=preference), decisions as kind=decision.
- If a request contradicts a saved preference, do NOT call add_job. Point out the conflict
  briefly and ask whether she wants to proceed or change her criteria.
- Be concise. Reply in the language the user writes in."""


def system_text():
    return SYSTEM_PROMPT


def enrich(ws, user_text):
    """Return the user message text with a compact <ctx> block (kept in history -> stable cache prefix)."""
    mem = memory.relevant(ws, user_text)
    counts = JobStore(ws).summary()
    parts = []
    if mem:
        parts.append("memory:\n" + "\n".join(f"- [{e['kind']}] {e['key']}: {e['value']}" for e in mem))
    if counts:
        parts.append("tracker counts: " + ", ".join(f"{k}={v}" for k, v in counts.items()))
    if not parts:
        log("context.py", "nothing relevant to inject this turn")
        return user_text
    log("context.py", f"injecting {sum(len(p) for p in parts)} chars of context")
    return "<ctx>\n" + "\n".join(parts) + "\n</ctx>\n" + user_text
