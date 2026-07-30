# MTG Commander Builder

> Build, research, and optimize Magic: The Gathering Commander decks with an AI agent that knows the game — not a chatbot that guesses.

An agent-native workspace structured as an ICM (Interpretable Context Methodology) pipeline. Folder structure does the orchestration. Plain markdown files carry state. A human reviews at every handoff. Drop it into Claude Code and start building.

---

## Why This Exists

Most AI deck-building tools either hallucinate cards or give generic advice. This workspace gives an AI agent real data — EDHREC staples, Scryfall prices, Commander Spellbook combos, live reference decklists — and a structured pipeline so it knows exactly what to do at each step and when to hand off to you.

The result: a complete Commander deck from a brief in one session, with real card data, validated legality, and a mana base that actually works.

---

## Features

| | |
|---|---|
| **Consultant-style intake** | Discovers your commander, playstyle, and win condition through conversation — not a form |
| **Auto-generated starter deck** | Fills 85–95% of the deck from EDHREC staples by synergy score |
| **Monte Carlo simulation** | Tests keep rate, mana development, and key piece consistency before you finalize |
| **Live data** | Pulls from EDHREC, Scryfall, Moxfield, Archidekt, and Commander Spellbook |
| **Full validation** | Rules legality, bracket compliance, ban list, color identity, and combo checks |
| **Moxfield export** | One command copies the list to clipboard in import-ready format |
| **Three siloed phases** | Ideation → Deckbuilding → Optimization — each loads only what it needs |

---

## Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/StoneSagala/mtg-commander-builder.git
cd mtg-commander-builder

# 2. Install Python dependencies
pip install requests playwright
playwright install chromium

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
├── CLAUDE.md                   ← Agent entry point
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

No API keys required.

---

## Contributing

Issues and pull requests welcome. If you're adding a new script, follow the pattern in the existing workspace `CONTEXT.md` — register it in the scripts table with its command and what it returns.

If you're adding a new archetype, engine, or win condition, add the file to `deckbuilding/skills/archetypes/` in the appropriate subfolder and reference it in `brew-commander.md`.
