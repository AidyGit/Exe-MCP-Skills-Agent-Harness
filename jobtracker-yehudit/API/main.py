"""python API/main.py --scenario scenario.json --out results/api.json"""
import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "API")]

from shared import checks, linecount  # noqa: E402
from shared.workspace import Workspace  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", default="scenario.json")
    ap.add_argument("--out", default="results/api.json")
    ap.add_argument("--workspace", default=str(ROOT / ".run" / "api"))
    args = ap.parse_args()
    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("ANTHROPIC_API_KEY is not set (export it in the terminal; never put it in code/git)")
    import anthropic
    from agent import Agent

    scenario = json.loads(Path(args.scenario).read_text(encoding="utf-8"))
    ws = Workspace.fresh(args.workspace)  # clean state for every run
    client = anthropic.Anthropic()
    turns, report = [], []
    for s in scenario["sessions"]:
        agent = Agent(client, ws)  # NEW agent instance; state comes from disk (memory.md, jobs.json)
        for text in s["turns"]:
            r = agent.turn(text)
            turns.append({"reply": r["reply"], "tools": r["tools"]})
            report.append({"session": s["name"], "user": text, **r})
    results = checks.run_checks(ws, scenario["checks"], turns)
    out = {"version": "API", "model": "claude-opus-5-5", "effort": "medium", "turns": report,
           "checks": results, "checks_passed": f"{sum(c['passed'] for c in results)}/{len(results)}",
           "harness_lines": linecount.count_api(ROOT / "API" / "harness")}
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"checks passed: {out['checks_passed']} -> {args.out}")


if __name__ == "__main__":
    main()
