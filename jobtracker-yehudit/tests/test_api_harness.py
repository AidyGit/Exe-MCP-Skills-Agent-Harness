import json

from conftest import ROOT, FakeClient, load_module, text_resp, tool_resp
from harness import caching, compaction, context, memory, tokens
from harness.history import History
from shared.jobs import JobStore
from shared.memory_store import MemoryStore
from shared.workspace import Workspace

Agent = load_module("api_agent", ROOT / "API" / "agent.py").Agent


def test_loop_batches_all_tool_results_in_one_message(ws):
    client = FakeClient([
        tool_resp(("add_job", {"company": "A", "title": "T"}), ("add_job", {"company": "B", "title": "T"})),
        text_resp("done")])
    agent = Agent(client, ws)
    r = agent.turn("add two")
    assert r["reply"] == "done" and r["model_calls"] == 2 and r["tools"] == ["add_job", "add_job"]
    results_msg = agent.messages[2]
    assert results_msg["role"] == "user" and len(results_msg["content"]) == 2  # one message, two results
    assert len(JobStore(ws).all()) == 2


def test_tool_error_returns_is_error_and_loop_continues(ws):
    client = FakeClient([tool_resp(("update_job_status", {"job": "x", "status": "offer"})), text_resp("not found")])
    agent = Agent(client, ws)
    agent.turn("update x")
    result = agent.messages[2]["content"][0]
    assert result["is_error"] is True and "LookupError" in result["content"]


def test_unknown_tool_is_error(ws):
    client = FakeClient([tool_resp(("nope", {})), text_resp("ok")])
    agent = Agent(client, ws)
    agent.turn("x")
    assert agent.messages[2]["content"][0]["is_error"]


def test_history_is_append_only_and_resumable(ws):
    h = History(ws, "s1")
    h.append({"role": "user", "content": "a"})
    h.append({"role": "assistant", "content": [{"type": "text", "text": "b"}]})
    before = h.path.read_text()
    h.append({"role": "user", "content": "c"})
    assert h.path.read_text().startswith(before)
    client = FakeClient([text_resp("hi again")])
    agent = Agent(client, ws, session_id="s1", resume=True)
    assert len(agent.messages) == 3
    agent.turn("d")
    assert len(client.calls[0]["messages"]) == 4  # resumed context was sent


def test_new_session_has_memory_but_not_history(ws):
    MemoryStore(ws.memory_path).save("preference", "stack", "only C#/.NET")
    client = FakeClient([text_resp("ok")])
    agent = Agent(client, ws)  # fresh session id, no resume
    agent.turn("what do I want?")
    first = client.calls[0]["messages"][0]["content"][0]["text"]
    assert "only C#/.NET" in first and len(client.calls[0]["messages"]) == 1


def test_memory_selection_preferences_always_facts_only_if_relevant(ws):
    m = MemoryStore(ws.memory_path)
    m.save("preference", "stack", "only .NET")
    m.save("fact", "recruiter", "Dana from Wix called")
    m.save("fact", "cat", "named Mitzi")
    picked = {e["key"] for e in memory.relevant(ws, "did the recruiter call?")}
    assert picked == {"stack", "recruiter"}


def test_context_is_compact_and_counts_only(ws):
    JobStore(ws).add("A", "T", "interview")
    txt = context.enrich(ws, "hello")
    assert "interview=1" in txt and "company" not in txt


def test_caching_breakpoints_and_no_mutation():
    msgs = [{"role": "user", "content": "hi"}]
    system, tools_, out = caching.apply("sys", [{"name": "a"}, {"name": "b"}], msgs)
    assert system[0]["cache_control"] and "cache_control" in tools_[-1] and "cache_control" not in tools_[0]
    assert out[-1]["content"][-1]["cache_control"]
    assert msgs == [{"role": "user", "content": "hi"}]  # history untouched


def test_caching_is_sent_to_model(ws):
    client = FakeClient([text_resp("ok")])
    Agent(client, ws).turn("x")
    call = client.calls[0]
    assert call["system"][0]["cache_control"] and call["tools"][-1]["cache_control"]
    assert call["extra_body"] == {"output_config": {"effort": "medium"}}


def test_compaction_replaces_history_past_threshold(ws):
    client = FakeClient([text_resp("answer", i=5000), text_resp("SUMMARY TEXT")])
    agent = Agent(client, ws, compact_threshold=1000)
    r = agent.turn("long")
    assert r["model_calls"] == 2
    assert len(agent.messages) == 2 and "SUMMARY TEXT" in agent.messages[0]["content"]
    resumed = Agent(FakeClient([]), ws, session_id=agent.history.session_id, resume=True)
    assert resumed.messages == agent.messages  # compaction survives a reload


def test_no_compaction_below_threshold():
    assert not compaction.needs_compaction(500, 1000)


def test_token_meter_cost_and_report():
    m = tokens.TurnMeter()
    m.record(type("U", (), dict(input_tokens=1_000_000, output_tokens=0,
                                 cache_read_input_tokens=0, cache_creation_input_tokens=0)))
    assert round(m.cost(), 2) == 5.0
    assert m.report([])["model_calls"] == 1


def test_runtime_trace_names_the_file(ws, capsys):
    Agent(FakeClient([text_resp("ok")]), ws).turn("x")
    err = capsys.readouterr().err
    for f in ("agent.py", "loop.py", "caching.py", "history.py", "memory.py", "context.py", "tokens.py"):
        assert f"[{f}]" in err


def test_full_scenario_with_scripted_model(tmp_path):
    from shared import checks
    sc = json.loads((ROOT / "scenario.json").read_text())
    ws = Workspace.fresh(tmp_path / "w")
    posting = str(ROOT / "shared/data/postings/nice_dotnet.txt")
    script = [
        tool_resp(("add_job", {"company": "Elbit Systems", "title": "C#/.NET Backend Developer"})), text_resp("added"),
        tool_resp(("save_memory", {"kind": "preference", "key": "stack", "value": "only C#/.NET, no Java"})), text_resp("saved"),
        tool_resp(("fetch_job_posting", {"source": posting})),
        tool_resp(("add_job", {"company": "NICE", "title": "Backend Developer (C#/.NET Core)", "source": posting})), text_resp("added NICE"),
        tool_resp(("update_job_status", {"job": "Elbit Systems", "status": "interview"})), text_resp("updated"),
        text_resp("You want C#/.NET roles only."),
        text_resp("That is a Java role and conflicts with your .NET criteria. Add anyway?"),
        tool_resp(("list_jobs", {})), text_resp("2 jobs: 1 applied, 1 interview"),
    ]
    client = FakeClient(script)
    turns = []
    for s in sc["sessions"]:
        agent = Agent(client, ws)
        for t in s["turns"]:
            r = agent.turn(t)
            turns.append({"reply": r["reply"], "tools": r["tools"]})
    assert client.script == []
    res = checks.run_checks(ws, sc["checks"], turns)
    assert all(r["passed"] for r in res), res
    assert len(res) >= 5
