"""Count code lines per harness part.

API: one file per part -> non-blank, non-comment, non-docstring-only lines.
SDK: a line (or the contiguous block right after a `# replaces: X` comment line,
     up to the next blank line) belongs to part X.
"""
import re
from pathlib import Path

MARK = re.compile(r"#\s*replaces:\s*([\w.]+)")


def _is_code(line):
    s = line.strip()
    return bool(s) and not s.startswith("#") and s not in ('"""', "'''")


def count_api(harness_dir):
    out = {}
    for p in sorted(Path(harness_dir).glob("*.py")):
        if p.name == "__init__.py":
            continue
        in_doc, n = False, 0
        for line in p.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if s.startswith(('"""', "'''")):
                if not (len(s) > 3 and s.endswith(s[:3])):
                    in_doc = not in_doc
                continue
            if in_doc:
                continue
            n += _is_code(line)
        out[p.name] = n
    return out


def count_sdk(sdk_dir):
    out = {}
    for p in sorted(Path(sdk_dir).glob("*.py")):
        current = None
        for line in p.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                current = None
                continue
            m = MARK.search(line)
            if m and line.strip().startswith("#"):
                current = m.group(1)
                continue
            part = m.group(1) if m else current
            if part and _is_code(line):
                out[part] = out.get(part, 0) + 1
    return out
