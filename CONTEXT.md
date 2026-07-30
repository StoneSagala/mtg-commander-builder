# MTG Deck Builder — Task Router

## What This Is

An agent workspace for Magic: The Gathering deck building, card research, and deck optimization. Three siloed workspaces, each handling one phase of the work.

**CLAUDE.md** (always loaded) has the full folder map and naming rules. This file routes you to work.

---

## Folder Structure

```
MTG Deck Builder/
├── Ideation/       ← docs/  skills/  scripts/
├── deckbuilding/   ← docs/  skills/  brews/  decklists/  scripts/
├── optimization/   ← docs/  skills/  sessions/  scripts/
├── frontend/       ← Web app frontend — DO NOT ENTER. No deck-building work happens here.
└── backend/        ← Web app backend — DO NOT ENTER. No deck-building work happens here.
```

---

## Workspace Summary

| Workspace       | Purpose                                                                              | Skills & Tools                                    |
| --------------- | ------------------------------------------------------------------------------------ | ------------------------------------------------- |
| `Ideation/`     | Consultant-style intake to discover commander, playstyle, theme, and power level. On approval, creates a brew starter file in `deckbuilding/brews/`. | `skills/ideate.md`, `scripts/intake.py` |
| `deckbuilding/` | Turn a brief into a complete first-draft decklist. Format rules + archetype patterns. | `skills/brew-commander.md`, `skills/card-search.md` |
| `optimization/` | Take a working draft and make it competitive. Mana, curve, card quality.             | `skills/tune-deck.md`, `skills/mana-base.md`        |

Each workspace has its own CONTEXT.md with full details. Read that when working in a workspace, not this file.

---

## Cross-Workspace Flow

```
[New deck]
Ideation/ (intake conversation → creates deckbuilding/brews/[slug]-draft.md)
    ↓
deckbuilding/ (brew deck from starter file → deckbuilding/brews/[slug]-draft.md)
    ↓
optimization/ (tune, finalize → deckbuilding/decklists/[slug]-final.md)

[Existing deck]
optimization/ ← deck comes in as paste / .md file / Moxfield or Archidekt URL
    ↓
deckbuilding/decklists/[slug]-final.md (when done)
```

Optimization is both downstream from deckbuilding *and* a direct entry point when the player already has a deck.

---

## Quick Format Reference

| Format          | Deck Size   | Sideboard | Commander?        |
| --------------- | ----------- | --------- | ----------------- |
| Commander / EDH | 100 exactly | None      | Yes (1 commander) |

Full rules and current ban lists → `deckbuilding/docs/formats.md`
