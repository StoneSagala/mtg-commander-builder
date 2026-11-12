# Shared reference contract

Inputs: task routed by `../AGENTS.md`. Read `voice.md` for player conversations;
read `data-sources.md` and `data_sources.py` for network maintenance.
Process: reuse these rules and integrations across all stages; keep one home per
provider contract. Outputs: verified records or explicit errors, not deck artifacts.
Human check: provider repairs require regression tests and a live probe review.

`current/commander.json` is generated current source data, governed by
`../_system/data-policy.json`. `freshness.py` refreshes/checks it, `deck_budget.py`
handles the player's optional total, `combos.py` reports bounded query completeness,
and `ratios.py` holds shared heuristic ratios. These are the canonical implementations.
