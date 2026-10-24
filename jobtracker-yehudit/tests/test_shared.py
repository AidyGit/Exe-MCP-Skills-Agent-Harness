import json

from shared import checks, linecount
from shared.jobs import JobStore
from shared.memory_store import MemoryStore
from shared.tools_core import run_tool
import pytest


def test_add_list_update_and_compact_output(ws):
    run_tool(ws, "add_job", {"company": "Elbit", "title": "Dev"})
    out = run_tool(ws, "list_jobs", {})
    assert json.loads(out) == [{"id": 1, "company": "Elbit", "title": "Dev", "status": "applied"}]
    assert " " not in out.replace("Elbit", "").replace("Dev", "")  # minified JSON
    run_tool(ws, "update_job_status", {"job": "elbit", "status": "interview"})
    assert JobStore(ws).all()[0]["status"] == "interview"


def test_errors_raise(ws):
    with pytest.raises(LookupError):
        run_tool(ws, "update_job_status", {"job": "nobody", "status": "offer"})
    with pytest.raises(ValueError):
        run_tool(ws, "add_job", {"company": "A", "title": "B", "status": "bogus"})


def test_memory_upsert_and_search(ws):
    m = MemoryStore(ws.memory_path)
    m.save("preference", "stack", "only C#/.NET")
    m.save("preference", "stack", "C#/.NET and Python")
    assert len(m.entries()) == 1 and "Python" in m.entries()[0]["value"]
    assert m.search("python")[0]["key"] == "stack"


def test_posting_file_and_html(ws, tmp_path):
    from shared import postings
    p = postings.fetch(str(__import__("pathlib").Path(__file__).parent.parent / "shared/data/postings/nice_dotnet.txt"))
    assert p["company"] == "NICE" and "C#" in p["title"]
    h = postings.fetch("https://x.test/job", fetcher=lambda u: "<html><title>Dev @ Acme</title><script>x()</script><body>Hi</body></html>")
    assert h["title"] == "Dev @ Acme" and "x()" not in h["text"]
    with pytest.raises(FileNotFoundError):
        postings.fetch("/nope.txt")


def test_checks_are_state_based(ws):
    run_tool(ws, "add_job", {"company": "NICE", "title": "Dev", "source": "a/nice_dotnet.txt"})
    run_tool(ws, "save_memory", {"kind": "preference", "key": "stack", "value": ".NET only"})
    res = checks.run_checks(ws, [
        {"name": "a", "type": "job_exists", "company": "nice"},
        {"name": "b", "type": "job_absent", "company": "Wix"},
        {"name": "c", "type": "memory_contains", "text": ".net"},
        {"name": "d", "type": "job_source_contains", "text": "nice_dotnet"},
        {"name": "e", "type": "tool_used", "turn": 0, "tool": "x"}],
        [{"reply": "", "tools": []}])
    assert [r["passed"] for r in res] == [True, True, True, True, False]


def test_linecount_sdk_marks(tmp_path):
    (tmp_path / "a.py").write_text("# replaces: loop.py\nx = 1\ny = 2\n\nz = 3\nw = 4  # replaces: tokens.py\n")
    assert linecount.count_sdk(tmp_path) == {"loop.py": 2, "tokens.py": 1}
