# MTG Commander Builder

> Build, research, and optimize Magic: The Gathering Commander decks with an AI agent that knows the game — with verified card data and explicit review gates.

An agent-native workspace structured as an ICM (Interpretable Context Methodology) pipeline. Folder structure does the orchestration. Plain markdown files carry state. A human reviews at every handoff. Drop it into Claude Code and start building.

---

## Why This Exists

Most AI deck-building tools either hallucinate cards or give generic advice. This workspace gives an AI agent real data — EDHREC staples, Scryfall prices, Commander Spellbook combos, live reference decklists — and a structured pipeline so it knows exactly what to do at each step and when to hand off to you.

The workflow produces an editable draft, then guides a review of strategy, legality, mana and budget. Coverage depends on the available data; generated cards and heuristic roles still need review.

---

## Features

| | |
|---|---|
| **Consultant-style intake** | Discovers your commander, playstyle, and win condition through conversation — not a form |
| **Auto-generated starter deck** | Builds an editable draft from EDHREC + Scryfall; uses labelled Scryfall strategy searches when EDHREC fails |
| **Monte Carlo simulation** | Tests keep rate, mana development, and key piece consistency before you finalize |
| **Live data** | Pulls from EDHREC, Scryfall, Moxfield, Archidekt, and Commander Spellbook |
| **Full validation** | Legality, color identity and budget checks, with heuristic bracket checks and separate combo evidence |
| **Moxfield export** | One command copies the list to clipboard in import-ready format |
| **Three siloed phases** | Ideation → Deckbuilding → Optimization — each loads only what it needs |

---

## Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/StoneSagala/mtg-commander-builder.git
cd mtg-commander-builder

# 2. Check the data connections (standard library; no API keys)
python3 _system/audit-connections.py

# 3. Open in Claude Code
claude
```

Then just talk to it:

> *"I want to build a new Commander deck"*
> *"Here's a deck I want to tune: [paste list]"*

No slash commands needed. The agent reads `CLAUDE.md` and knows what to do.

---

## How It Works

Three workspaces, one direction of flow:

```
Ideation/ ──────────────────────────────────────────────────────────────────┐
  Intake conversation → commander + brief                                    │
  Output: deckbuilding/brews/[slug]-draft.md                                 │
                                                                             ▼
deckbuilding/ ──────────────────────────────────────────────────────────────┐
  Auto-generate starter → review and swap → validate                        │
  Output: deckbuilding/brews/[slug]-review.md → decklists/[slug]-final.md   │
                                                                             ▼
optimization/ ───────────────────────────────────────────────────────────────
  Diagnostics → mana base → card tuning → re-simulate → finalize
  Output: optimization/sessions/[deck]-[YYYY-MM-DD].md
```

Each workspace has its own `CONTEXT.md` that tells the agent exactly what to load, what to do, and what to hand off. Nothing bleeds between phases without your approval.

---

## Project Structure

```
mtg-commander-builder/
├── AGENTS.md                   ← Canonical agent router
├── CLAUDE.md                   ← Pointer to AGENTS.md
├── CONTEXT.md                  ← Pipeline overview and workspace map
├── _shared/
│   └── voice.md                ← Persona and tone
├── Ideation/
│   ├── docs/                   ← playstyles.md, brackets.md
│   ├── skills/                 ← ideate.md
│   └── scripts/                ← EDHREC fetchers, commander filter, playstyle quiz
├── deckbuilding/
│   ├── docs/                   ← formats, archetypes, card evaluation, game changers
│   ├── skills/                 ← brew-commander, card-search, 23 archetype files
│   ├── brews/                  ← WIP decklists
│   ├── decklists/              ← Finalized decklists
│   └── scripts/                ← Generator, validators, staples fetcher, Moxfield export
└── optimization/
    ├── docs/                   ← mana base theory, sideboard guide
    ├── skills/                 ← tune-deck, mana-base, meta-check
    ├── sessions/               ← Optimization session notes
    └── scripts/                ← Deck health, goldfish sim, curve/color analysis
```

---

## Prerequisites

- Python 3.9+
- [Claude Code](https://claude.ai/code)
- Internet connection (scripts pull live data from EDHREC, Scryfall, etc.)

No API keys required. Core tools use the Python standard library. Moxfield may restrict anonymous API access; provider status is always environment-specific.

---

## Contributing

Issues and pull requests welcome. If you're adding a new script, follow the pattern in the existing workspace `CONTEXT.md` — register it in the scripts table with its command and what it returns.

If you're adding a new archetype, engine, or win condition, add the file to `deckbuilding/skills/archetypes/` in the appropriate subfolder and reference it in `brew-commander.md`.

## Maintenance and recovery

```bash
python3 -m unittest discover -s tests -v
python3 _system/audit-connections.py --commander "Kotis, the Fangkeeper"
```

The GitHub Actions workflow runs offline regressions and offers a manual live
connection check with a downloadable report. EDHREC failures automatically use a
labelled generic legal-color Scryfall pool. If Scryfall cannot verify the commander,
generation stops with the actual error. See [_shared/data-sources.md](_shared/data-sources.md)
for recovery and script repair, and the [2026-11-12 audit](_system/audits/2026-11-12-audit.md)
for evidence and remaining limits.

Preserve the approved `[slug]-draft.md` brief. Generate into `[slug]-generated.md`.
The optional `--budget` is the player's total-deck limit, including commander(s) and lands. Omit it for no limit. Revalidate after manual swaps.

Current rules, bans and Game Changers expire after 24 hours; discovery caches after seven days. Tools refresh on use. A daily GitHub workflow proposes reference updates and reports failures once installed on the default branch. Changed rule wording requires source review. See [_system/data-policy.json](_system/data-policy.json).
