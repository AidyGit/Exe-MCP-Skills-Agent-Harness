"""Prints the REPORT.md comparison tables from results/api.json and results/sdk.json.
A missing results file is shown as "not run" instead of crashing."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
R = ROOT / "results"
sys_path = __import__("sys").path
sys_path.insert(0, str(ROOT))
from shared import linecount  # noqa: E402


def load(name):
    p = R / f"{name}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def totals(d):
    if not d:
        return None
    t = {k: sum(x[k] for x in d["turns"]) for k in
         ("input_tokens", "cache_read_tokens", "cache_write_tokens", "output_tokens", "model_calls", "cost_usd", "seconds")}
    all_in = t["input_tokens"] + t["cache_read_tokens"] + t["cache_write_tokens"]
    t["cache_pct"] = round(100 * t["cache_read_tokens"] / all_in, 1) if all_in else 0.0
    return t


api, sdk = load("api"), load("sdk")
a, s = totals(api), totals(sdk)
cell = lambda t, k: t[k] if t else "not run"
print("| | API | SDK |\n|---|---|---|")
for label, k in [("input (uncached)", "input_tokens"), ("cache read", "cache_read_tokens"),
                 ("cache write", "cache_write_tokens"), ("output", "output_tokens"),
                 ("cache hit %", "cache_pct"), ("model calls", "model_calls"),
                 ("cost USD", "cost_usd"), ("seconds", "seconds")]:
    print(f"| {label} | {cell(a, k)} | {cell(s, k)} |")
print(f"| checks passed | {api['checks_passed'] if api else 'not run'} | {sdk['checks_passed'] if sdk else 'not run'} |")

al = api["harness_lines"] if api else linecount.count_api(ROOT / "API" / "harness")
sl = sdk["harness_lines"] if sdk else linecount.count_sdk(ROOT / "SDK")
print("\n| harness part | API lines | SDK lines |\n|---|---|---|")
for p in sorted(set(al) | set(sl)):
    print(f"| {p} | {al.get(p, 0)} | {sl.get(p, 0)} |")
print(f"| **total** | {sum(al.values())} | {sum(sl.values())} |")
