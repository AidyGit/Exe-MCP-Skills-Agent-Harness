api.json / sdk.json are not included: the benchmark was NOT executed.
- API version needs a Claude Console API key with credit (none available).
- SDK version needs a Claude Code login on a Pro/Max plan (the account used is on the free plan:
  "Claude Max or Pro is required to connect to Claude Code").
What IS verified: 26 offline tests (python -m pytest -q) run the real API harness against a scripted fake client,
including the full 7-turn scenario and all 8 scenario checks, and verify the SDK configuration and tool handlers.
To produce the results, run the two commands in README.md; scripts/report_table.py then builds the tables.
