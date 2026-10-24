# REPORT — Job-search tracker: API harness vs Agent SDK

## Status — read first
**The benchmark was not executed.** The API version needs a Claude Console key with credit, and the SDK version needs a
Claude Code login on a Pro/Max plan; neither was available (Claude Code answered "Claude Max or Pro is required").
So **there are no measured tokens, costs or latencies below**, and sections 3–5 are analysis from the design, not measurements.
What is verified: 26 offline tests (`python -m pytest -q`) run the real API harness against a scripted fake client —
including the full 7-turn scenario and its 8 checks — and check the SDK options and tool handlers.
Everything is ready to run: see `README.md`, then `python scripts/report_table.py` prints the tables from the results files.

## The agent
A job-search tracker. Tools: `add_job`, `list_jobs`, `update_job_status`, `save_memory`, `recall_memory`, and the external tool
`fetch_job_posting` (local file or URL). Memory persists in a markdown file (`memory.md` in the API version, `CLAUDE.md` in the SDK version).
Scenario (`scenario.json`): 2 sessions, 7 turns; session 2 is a new agent instance that loads state from disk. It covers tool use,
saving to memory, recall in session 2, the external tool, and a Java job that contradicts a saved ".NET only" preference.
8 pass/fail checks, almost all on persisted state (`jobs.json`, memory file) — e.g. the Wix/Java job must not be in the tracker.

## Four required topics
- **Tools:** 6 tools, JSON schemas in `shared/tools_core.py`; errors return to the model as `is_error`.
- **Memory:** key/kind entries in a markdown file, upsert by key; survives a new agent instance.
- **Context engineering (API):** each turn injects only preferences, memory entries relevant to the message, and job counts — not the whole state.
- **Token optimization:** minified JSON tool output; per-turn token/cost/latency report; prompt caching breakpoints; compaction past a threshold.

## 1. API vs SDK — measured results
| | API | SDK |
|---|---|---|
| input / cache read / cache write / output tokens | not run | not run |
| cache hit % | not run | not run |
| model calls | not run | not run |
| cost USD | not run | not run |
| scenario checks passed (live model) | not run | not run |
| scenario checks passed (scripted fake model, offline) | 8/8 | n/a (loop runs inside Claude Code) |

## 2. Harness lines of code (counted from the code, `shared/linecount.py`)
| part | API | SDK |
|---|---|---|
| loop | 34 | 3 |
| tools | 15 | 2 |
| history | 23 | 1 |
| memory | 20 | 2 |
| context | 26 | 0 (what Claude Code adds + what the model pulls with tools) |
| compaction | 14 | 0 (automatic) |
| caching | 17 | 0 (automatic) |
| tokens | 25 | 1 |
| trace (helper) | 3 | 0 |
| **total** | **177** | **9** |

## 3. Where the SDK would use more / fewer tokens (expectation, NOT measured)
- **Likely more:** Claude Code adds its own scaffolding around my system prompt and tool wrappers on every call, and one SDK turn can include several internal model calls. In a short agent this overhead is a large share.
- **Likely fewer or cheaper:** caching is automatic. In my API version, breakpoints only pay off once the prefix passes the model's minimum cacheable length; my system prompt plus 6 tool schemas are short, so API cache hits may be near 0%.
- **Context:** the API version injects only relevant memory; the SDK loads the whole `CLAUDE.md` each session, which grows with memory.

## 4. What I controlled in the API and lose in the SDK
- Exactly what enters each turn (relevance-based memory selection vs whole `CLAUDE.md`).
- Cache breakpoints, compaction threshold and prompt, max-steps guard.
- The shape of errors returned to the model, and per-call token accounting (the SDK reports per-turn totals).
- Conversation storage format (append-only JSONL vs the SDK's internal session store).
- Deterministic offline testing of the loop: the API loop is tested with a fake client; the SDK loop lives inside the Claude Code process, so I can only test configuration and tool handlers.

## 5. Which version I would choose
Without measurements, my choice rests on the design: the **SDK**, because ~170 lines of loop, history, compaction and caching become configuration
(9 lines vs 177), and nothing in this agent needs per-call control. I would switch to the **API** version if measurements showed a large per-turn
overhead in the SDK, or once memory grows enough that relevance-based context selection matters. This should be confirmed by running both versions.
