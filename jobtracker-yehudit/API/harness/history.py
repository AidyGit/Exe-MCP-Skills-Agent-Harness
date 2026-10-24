"""Conversation persisted to disk: append-only JSONL, one file per session."""
import json
import uuid

from .trace import log


class History:
    def __init__(self, ws, session_id=None):
        self.session_id = session_id or uuid.uuid4().hex[:8]
        self.path = ws.sessions_dir / f"{self.session_id}.jsonl"

    def append(self, record):
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        log("history.py", f"append {record.get('role') or record.get('type')} -> {self.path.name}")

    def load(self):
        """Rebuild the live message list; a compaction record replaces everything before it."""
        if not self.path.exists():
            return []
        messages = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            rec = json.loads(line)
            if rec.get("type") == "compaction":
                messages = list(rec["messages"])
            else:
                messages.append(rec)
        log("history.py", f"loaded {len(messages)} messages for session {self.session_id}")
        return messages
