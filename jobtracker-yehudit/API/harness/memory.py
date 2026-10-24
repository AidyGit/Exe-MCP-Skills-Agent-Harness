"""Long-term memory: where it lives (memory.md) and how entries are pulled into a turn."""
import re

from shared.memory_store import MemoryStore

from .trace import log


def _stem(w):
    return w[1:] if len(w) > 3 and w[0] in "בלהומש" else w  # strip common Hebrew prefixes


def relevant(ws, user_text, limit=4):
    """Preferences are always included (short, decide behaviour); the rest only if related."""
    store = MemoryStore(ws.memory_path)
    entries = store.entries()
    prefs = [e for e in entries if e["kind"] == "preference"]
    words = {_stem(w) for w in re.findall(r"\w+", user_text.lower()) if len(w) > 1}
    scored = []
    for e in entries:
        if e["kind"] == "preference":
            continue
        hay = {_stem(w) for w in re.findall(r"\w+", (e["key"] + " " + e["value"]).lower())}
        if words & hay:
            scored.append((len(words & hay), e))
    picked = prefs + [e for _, e in sorted(scored, key=lambda t: -t[0])][:limit]
    log("memory.py", f"{len(picked)}/{len(entries)} memory entries selected for this turn")
    return picked
