"""Runtime trace: every harness action prints the file that performed it."""
import sys


def log(file, message):
    print(f"[{file}] {message}", file=sys.stderr, flush=True)
