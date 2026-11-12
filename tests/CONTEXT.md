# Regression test contract

Inputs: shared provider contracts and scripts. Run
`python3 -m unittest discover -s tests -v` from the repo root.
Tests mock network responses; they verify failure recovery and workflow safety
without depending on live provider availability. Live checks are separate:
`python3 _system/audit-connections.py`. Output: test results and optional dated
connection evidence. Human check: both regression results and unresolved live
provider statuses must be reviewed before accepting a repair.
