"""python SDK/main.py --scenario scenario.json --out results/sdk.json"""
import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "SDK")]

from shared import checks, linecount  # noqa: E402
from shared.workspace import ENV_VAR, Workspace  # noqa: E402


async def run(args):
    if os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("ANTHROPIC_API_KEY is set - unset it, otherwise billing goes to the API key instead of the Claude Code login")
    from agent import Agent

    scenario = json.loads(Path(args.scenario).read_text(encoding="utf-8"))
    ws = Workspace.fresh(args.workspace, memory_filename="CLAUDE.md")  # replaces: memory.py (memory = CLAUDE.md)
    os.environ[ENV_VAR] = str(ws.root)
    turns, report = [], []
    for s in scenario["sessions"]:
        async with Agent(ws) as agent:  # NEW client per session; state comes from disk
            for text in s["turns"]:
                r = await agent.turn(text)
                turns.append({"reply": r["reply"], "tools": r["tools"]})
                report.append({"session": s["name"], "user": text, **r})
                print(f"[sdk] turn done: tools={r['tools']} cost=${r['cost_usd']}", file=sys.stderr)
    results = checks.run_checks(ws, scenario["checks"], turns)
    out = {"version": "SDK", "model": "claude-opus-5-5", "effort": "medium", "turns": report,
           "checks": results, "checks_passed": f"{sum(c['passed'] for c in results)}/{len(results)}",
           "harness_lines": linecount.count_sdk(ROOT / "SDK")}
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"checks passed: {out['checks_passed']} -> {args.out}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", default="scenario.json")
    ap.add_argument("--out", default="results/sdk.json")
    ap.add_argument("--workspace", default=str(ROOT / ".run" / "sdk"))
    asyncio.run(run(ap.parse_args()))


if __name__ == "__main__":
    main()
