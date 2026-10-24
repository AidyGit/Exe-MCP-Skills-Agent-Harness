"""Prints the REPORT.md comparison tables from results/api.json and results/sdk.json."""
import json
from pathlib import Path

R = Path(__file__).resolve().parent.parent / "results"


def totals(d):
    t = {k: sum(x[k] for x in d["turns"]) for k in
         ("input_tokens", "cache_read_tokens", "cache_write_tokens", "output_tokens", "model_calls", "cost_usd", "seconds")}
    all_in = t["input_tokens"] + t["cache_read_tokens"] + t["cache_write_tokens"]
    t["cache_pct"] = round(100 * t["cache_read_tokens"] / all_in, 1) if all_in else 0.0
    return t


api, sdk = (json.loads((R / f"{n}.json").read_text(encoding="utf-8")) for n in ("api", "sdk"))
a, s = totals(api), totals(sdk)
print("| | API | SDK |\n|---|---|---|")
rows = [("input (uncached)", "input_tokens"), ("cache read", "cache_read_tokens"), ("cache write", "cache_write_tokens"),
        ("output", "output_tokens"), ("cache hit %", "cache_pct"), ("model calls", "model_calls"),
        ("cost USD", "cost_usd"), ("seconds", "seconds")]
for label, k in rows:
    print(f"| {label} | {a[k]} | {s[k]} |")
print(f"| checks passed | {api['checks_passed']} | {sdk['checks_passed']} |")
print("\n| harness part | API lines | SDK lines |\n|---|---|---|")
parts = sorted(set(api["harness_lines"]) | set(sdk["harness_lines"]))
for p in parts:
    print(f"| {p} | {api['harness_lines'].get(p, 0)} | {sdk['harness_lines'].get(p, 0)} |")
print(f"| **total** | {sum(api['harness_lines'].values())} | {sum(sdk['harness_lines'].values())} |")
