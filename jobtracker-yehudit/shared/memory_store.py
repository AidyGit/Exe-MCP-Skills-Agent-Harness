"""Long-term memory as a small markdown file: one line per entry, upsert by key.

Format:  - [kind] key: value        kind is preference | decision | fact
The same file is read by API/harness/memory.py and (as CLAUDE.md) by Claude Code.
"""
import re

KINDS = ("preference", "decision", "fact")
HEADER = "# Agent memory (job search)\n\n"
LINE = re.compile(r"^- \[(\w+)\] ([^:]+): (.*)$")


class MemoryStore:
    def __init__(self, path):
        self.path = path

    def entries(self):
        if not self.path.exists():
            return []
        out = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            m = LINE.match(line)
            if m:
                out.append({"kind": m.group(1), "key": m.group(2), "value": m.group(3)})
        return out

    def save(self, kind, key, value):
        if kind not in KINDS:
            raise ValueError(f"kind must be one of {KINDS}")
        key, value = key.strip().replace(":", "-"), value.strip().replace("\n", " ")
        entries = [e for e in self.entries() if e["key"] != key] + [{"kind": kind, "key": key, "value": value}]
        text = HEADER + "".join(f"- [{e['kind']}] {e['key']}: {e['value']}\n" for e in entries)
        self.path.write_text(text, encoding="utf-8")
        return {"kind": kind, "key": key, "value": value}

    def search(self, query, limit=5):
        words = {w for w in re.findall(r"\w+", query.lower()) if len(w) > 1}
        scored = []
        for e in self.entries():
            hay = set(re.findall(r"\w+", (e["key"] + " " + e["value"]).lower()))
            score = len(words & hay)
            if score:
                scored.append((score, e))
        return [e for _, e in sorted(scored, key=lambda t: -t[0])][:limit]
