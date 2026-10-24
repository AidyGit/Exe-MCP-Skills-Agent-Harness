# Job-search tracker agent — built twice (raw API vs Claude Agent SDK)

An agent that tracks job applications, remembers search criteria between sessions,
reads postings (local file or URL) and warns when a request contradicts a saved preference.

```
shared/   tools + data used by both versions (jobs.json, memory file, posting reader, checks)
API/      hand-written harness: loop, tools, history, memory, context, compaction, caching, tokens
SDK/      the same agent configured on Claude Agent SDK (lines marked "# replaces: <part>")
tests/    offline tests with a scripted fake client (no key, no network)
```

## Setup
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m pytest -q                      # offline, no key needed
```

## Run the benchmark (clean state each run)
```bash
# API version: key from Claude Console, ONLY as an environment variable
export ANTHROPIC_API_KEY=...            # never in code, never in git
python API/main.py --scenario scenario.json --out results/api.json
unset ANTHROPIC_API_KEY

# SDK version: uses your Claude Code login; ANTHROPIC_API_KEY must NOT be set
python SDK/main.py --scenario scenario.json --out results/sdk.json

python scripts/report_table.py          # tables for REPORT.md
```
Both versions use `claude-opus-5-5`, effort `medium`, and pinned library versions (`requirements.txt`).
