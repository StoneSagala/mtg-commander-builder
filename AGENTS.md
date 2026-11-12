# MTG Commander Builder

An agent workspace for building and tuning Commander decks.
Before a deck task, run `python3 _system/refresh-data.py`; stop rules-dependent work on expiry or unreviewed changes. Read only the contract for the current task. Player tone: `_shared/voice.md`.

| Task | Read |
|---|---|
| Understand workflow, artifact names and review gates | `CONTEXT.md` |
| Start a new deck / approve a brief | `Ideation/CONTEXT.md` |
| Build from an approved brief | `deckbuilding/CONTEXT.md`, then `deckbuilding/skills/brew-commander.md` |
| Tune an existing deck | `optimization/CONTEXT.md` |
| Diagnose providers / recover from data failure | `_shared/data-sources.md` |
| Review repairs and remaining limits | `_system/audits/2026-11-12-reliability-followup.md` (original incident: `2026-11-12-audit.md`) |
| Update current data / review expiry policy | `_system/refresh-data.py`, `_system/data-policy.json` |
| Run regression checks | `python3 -m unittest discover -s tests -v` |
| Recheck live connections | `python3 _system/audit-connections.py` |

Keep approved briefs intact. Generated drafts are separate edit surfaces.
A failed request is not proof that a commander or card does not exist.
