"""External tool: read a job posting from a local file or an http(s) URL."""
import html
import re
import urllib.request
from pathlib import Path

MAX_CHARS = 1200


def _strip_html(raw):
    raw = re.sub(r"(?is)<(script|style).*?</\1>", " ", raw)
    return html.unescape(re.sub(r"<[^>]+>", " ", raw))


def fetch(source, fetcher=None):
    """Return a compact dict. `fetcher(url)->str` can be injected (tests, offline)."""
    if source.startswith(("http://", "https://")):
        raw = (fetcher or _http_get)(source)
        title = re.search(r"(?is)<title>(.*?)</title>", raw)
        text = _strip_html(raw)
    else:
        p = Path(source)
        if not p.exists():
            raise FileNotFoundError(f"posting not found: {source}")
        raw = text = p.read_text(encoding="utf-8")
        title = None
    text = re.sub(r"[ \t]+", " ", re.sub(r"\n\s*\n+", "\n", text)).strip()
    field = lambda name: (re.search(rf"(?im)^{name}:\s*(.+)$", text) or [None, ""])[1].strip()
    return {"source": source,
            "title": field("Title") or (html.unescape(title.group(1)).strip() if title else ""),
            "company": field("Company"), "location": field("Location"),
            "text": text[:MAX_CHARS]}


def _http_get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "jobtracker-agent/1.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return r.read(300_000).decode("utf-8", errors="replace")
