"""Per-turn token usage, model-call count, latency and cost."""
import time

from .trace import log

# USD per million tokens. ASSUMPTION (Opus 4.5-class pricing) - verify against the pricing page.
PRICES = {"input": 5.0, "output": 25.0, "cache_read": 0.50, "cache_write": 6.25}


class TurnMeter:
    def __init__(self):
        self.input = self.cache_read = self.cache_write = self.output = self.calls = 0
        self.started = time.time()

    def record(self, usage):
        self.calls += 1
        self.input += getattr(usage, "input_tokens", 0) or 0
        self.cache_read += getattr(usage, "cache_read_input_tokens", 0) or 0
        self.cache_write += getattr(usage, "cache_creation_input_tokens", 0) or 0
        self.output += getattr(usage, "output_tokens", 0) or 0

    def cost(self):
        return (self.input * PRICES["input"] + self.output * PRICES["output"]
                + self.cache_read * PRICES["cache_read"] + self.cache_write * PRICES["cache_write"]) / 1e6

    def report(self, tools):
        total_in = self.input + self.cache_read + self.cache_write
        r = {"input_tokens": self.input, "cache_read_tokens": self.cache_read,
             "cache_write_tokens": self.cache_write, "output_tokens": self.output,
             "model_calls": self.calls, "tools": tools, "cost_usd": round(self.cost(), 6),
             "seconds": round(time.time() - self.started, 2),
             "cache_hit_pct": round(100 * self.cache_read / total_in, 1) if total_in else 0.0}
        log("tokens.py", f"turn usage {r}")
        return r
