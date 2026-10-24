"""Where one agent run keeps its state on disk (jobs, memory, session history)."""
import json
import os
import shutil
from pathlib import Path

ENV_VAR = "JOBAGENT_WORKSPACE"


class Workspace:
    def __init__(self, root, memory_filename="memory.md"):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.jobs_path = self.root / "jobs.json"
        self.memory_path = self.root / memory_filename
        self.sessions_dir = self.root / "sessions"
        self.sessions_dir.mkdir(exist_ok=True)

    @classmethod
    def fresh(cls, root, memory_filename="memory.md"):
        """Every benchmark run starts from a clean state."""
        if Path(root).exists():
            shutil.rmtree(root)
        return cls(root, memory_filename)

    @classmethod
    def from_env(cls, memory_filename="memory.md"):
        root = os.environ.get(ENV_VAR)
        if not root:
            raise RuntimeError(f"{ENV_VAR} is not set")
        return cls(root, memory_filename)

    def read_json(self, path, default):
        p = Path(path)
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default

    def write_json(self, path, data):
        Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
