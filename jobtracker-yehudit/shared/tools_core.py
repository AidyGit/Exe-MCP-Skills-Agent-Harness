"""The agent's tools: JSON schemas + one dispatcher. Used by both harnesses.

Tool results are deliberately terse (token optimization): short JSON, no prose.
Errors are raised as ToolError / ValueError and turned into is_error results by the caller.
"""
import json

from . import postings
from .jobs import STATUSES, JobStore
from .memory_store import KINDS, MemoryStore


class ToolError(Exception):
    pass


def _obj(props, required):
    return {"type": "object", "properties": props, "required": required}


TOOL_SPECS = [
    {"name": "add_job", "description": "Add a job application to the tracker.",
     "input_schema": _obj({
         "company": {"type": "string"}, "title": {"type": "string"},
         "status": {"type": "string", "enum": list(STATUSES)},
         "notes": {"type": "string"}, "source": {"type": "string", "description": "posting url/path"}},
         ["company", "title"])},
    {"name": "list_jobs", "description": "List tracked jobs (compact). Optional status filter.",
     "input_schema": _obj({"status": {"type": "string", "enum": list(STATUSES)},
                           "limit": {"type": "integer"}}, [])},
    {"name": "update_job_status", "description": "Change the status of a job by id or company name.",
     "input_schema": _obj({"job": {"type": "string", "description": "id or company"},
                           "status": {"type": "string", "enum": list(STATUSES)}}, ["job", "status"])},
    {"name": "fetch_job_posting",
     "description": "EXTERNAL: read a job posting from a local file path or an http(s) URL. Returns title, company, location and a short text.",
     "input_schema": _obj({"source": {"type": "string"}}, ["source"])},
    {"name": "save_memory",
     "description": "Remember something across sessions (upsert by key). kind: preference (job-search criteria), decision, or fact.",
     "input_schema": _obj({"kind": {"type": "string", "enum": list(KINDS)},
                           "key": {"type": "string"}, "value": {"type": "string"}}, ["kind", "key", "value"])},
    {"name": "recall_memory", "description": "Search long-term memory by free text.",
     "input_schema": _obj({"query": {"type": "string"}}, ["query"])},
]


def _j(obj):
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def _short(job):
    return {k: job[k] for k in ("id", "company", "title", "status")}


def run_tool(ws, name, args, fetcher=None):
    """Execute a tool; returns a compact string. Raises on bad input."""
    jobs, mem = JobStore(ws), MemoryStore(ws.memory_path)
    if name == "add_job":
        return _j(_short(jobs.add(args["company"], args["title"], args.get("status", "applied"),
                                  args.get("notes", ""), args.get("source", ""))))
    if name == "list_jobs":
        return _j([_short(j) for j in jobs.list(args.get("status"), int(args.get("limit", 10)))])
    if name == "update_job_status":
        return _j(_short(jobs.update_status(args["job"], args["status"])))
    if name == "fetch_job_posting":
        return _j(postings.fetch(args["source"], fetcher))
    if name == "save_memory":
        return _j(mem.save(args["kind"], args["key"], args["value"]))
    if name == "recall_memory":
        return _j(mem.search(args["query"])) if mem.search(args["query"]) else "[]"
    raise ToolError(f"unknown tool: {name}")
