"""Pass/fail checks, mostly on persisted state (jobs.json / memory file), not only reply text."""
from .jobs import JobStore
from .memory_store import MemoryStore


def run_checks(ws, checks, turns):
    """`turns` = list of {"reply": str, "tools": [names]} in scenario order."""
    jobs, mem = JobStore(ws).all(), MemoryStore(ws.memory_path).entries()
    results = []
    for c in checks:
        t = c["type"]
        if t == "job_exists":
            ok = any(j["company"].lower() == c["company"].lower()
                     and (not c.get("status") or j["status"] == c["status"]) for j in jobs)
        elif t == "job_absent":
            ok = not any(j["company"].lower() == c["company"].lower() for j in jobs)
        elif t == "job_count_at_least":
            ok = len(jobs) >= c["n"]
        elif t == "job_source_contains":
            ok = any(c["text"] in j.get("source", "") for j in jobs)
        elif t == "memory_contains":
            ok = any(c["text"].lower() in (e["key"] + " " + e["value"]).lower() for e in mem)
        elif t == "tool_used":
            ok = c["tool"] in turns[c["turn"]]["tools"]
        elif t == "reply_contains":
            reply = turns[c["turn"]]["reply"].lower()
            ok = any(s.lower() in reply for s in c["any"])
        else:
            raise ValueError(f"unknown check type {t}")
        results.append({"name": c["name"], "type": t, "passed": bool(ok)})
    return results
