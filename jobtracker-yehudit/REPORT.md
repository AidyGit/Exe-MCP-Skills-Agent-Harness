# REPORT — Job-search tracker: API harness vs Agent SDK

> **Status:** the code, offline tests (25 passing) and scenario are done. The numbers below must be
> filled in after running both versions on a real key / login (`python scripts/report_table.py`
> prints these tables from `results/api.json` and `results/sdk.json`). Sections 3–5 are my analysis
> from the design; confirm them against your measured numbers before submitting.

## The agent
Tracks job applications (`add_job`, `list_jobs`, `update_job_status`), reads a posting from a file or URL
(`fetch_job_posting` — the external tool), and remembers search criteria (`save_memory`, `recall_memory`).
Scenario: 2 sessions, 7 turns; session 2 is a brand-new agent instance that loads state from disk. It covers tool use,
saving to memory, recall in session 2, the external tool, and a request (Java job) that contradicts a saved preference.
8 pass/fail checks, almost all on persisted state (`jobs.json`, memory file), e.g. the Wix/Java job must **not** be in the tracker.

## 1. API vs SDK (fill from results)
| | API | SDK |
|---|---|---|
| input (uncached) | | |
| cache read | | |
| cache write | | |
| output | | |
| cache hit % | | |
| model calls | | |
| cost USD | | |
| checks passed | /8 | /8 |

## 2. Harness lines of code
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

(Counts come from `shared/linecount.py`; regenerate with `scripts/report_table.py`.)

## 3. Where the SDK used more / fewer tokens, and why (expectation — verify)
- **More:** Claude Code sends its own scaffolding on every call (tool/MCP wrappers, its framing around my system prompt),
  and the SDK's `ResultMessage.usage` may count several internal model calls per turn. Short agents feel this most.
- **Fewer / cheaper:** caching is automatic and tuned; the API version's breakpoints help only once the prefix passes
  the model's minimum cacheable length — my system prompt + 6 tool schemas are short, so API cache hits may be near 0%.
- **Context:** in the API version I inject only preferences + relevant memory + job counts per turn. In the SDK,
  `CLAUDE.md` is loaded whole every session, so it grows with memory (fine for a few lines, wasteful at scale).

## 4. What I controlled in the API and lost in the SDK
- Exactly what enters each turn (relevance-based memory selection vs. whole `CLAUDE.md`).
- Cache breakpoints, compaction threshold/prompt, and the max-steps guard.
- Error shape returned to the model, and per-call token/cost accounting (SDK gives per-turn totals only).
- Conversation storage format (mine is a plain append-only JSONL; the SDK's session store is internal).
- Deterministic offline testing: with the API I test the real loop with a fake client; with the SDK I can only test
  the config and my tool handlers, since the loop lives inside the Claude Code process.

## 5. Which one I would choose
For this personal agent: **the SDK**, if the measured cost difference is small. It removes ~170 lines of loop,
history, compaction and caching code that I would otherwise have to maintain, and the behaviour that matters
(tools, memory file, resume) is configuration. I would pick the **API** version if the numbers show the SDK's overhead is
large per turn, or if I needed per-turn control of context (relevance-based memory) as memory grows.
