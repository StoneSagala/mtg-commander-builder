# Maintenance contract

Inputs: current scripts, failing command, `_shared/data-sources.md` at repo root.
Run `audit-connections.py` for live evidence and `inventory.py` for a generated
tracked-file inventory. Save reports in `audits/`; inspect failures, add regression
tests in `../tests/`, update shared integrations, then repeat the failing command.
Human check: review diagnosis, code diff, remaining provider limits and generated
draft before accepting a repair. Outputs are evidence, never approval to promote a deck.

Current-data maintenance: `data-policy.json` defines expiry; `refresh-data.py`
refreshes official rules/bans/Game Changers and optional discovery snapshots.
`rules-review.json` records the reviewed semantic hash. `.github/workflows/freshness.yml`
proposes daily updates after publication to the default branch; local runtime
refresh guards work independently. Review changed rule wording before accepting
a new hash. Generated references and snapshots are never hand-edited.
