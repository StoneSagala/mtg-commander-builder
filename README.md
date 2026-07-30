# MTG Commander Builder

An agent-native workspace for building, researching, and optimizing Magic: The Gathering Commander decks. Structured as an ICM (Interpretable Context Methodology) pipeline — folder structure does the orchestration, plain markdown files carry state, and a human reviews at every handoff.

---

## How It Works

Three siloed workspaces, each handling one phase of the deck-building lifecycle:

```
Ideation/ → deckbuilding/ → optimization/
```

An agent drops into a workspace, reads its `CONTEXT.md`, does its work, and exits. Nothing bleeds between phases until a human approves the handoff.

---

## Workspaces

### Ideation/
Consultant-style intake conversation to discover what to build. Extracts commander, playstyle, theme, win condition, and bracket from dialogue — never from a form. Output is a brew starter file in `deckbuilding/brews/`.

**Scripts:** EDHREC theme matching, commander filtering by bracket + budget, playstyle discovery quiz, combo-first reverse lookup.

### deckbuilding/
Turns an approved brief into a complete first-draft decklist. Auto-generates ~85–95% of the deck from EDHREC staples by synergy score, then surfaces the remaining decisions to the human.

**Scripts:** Starter deck generator, staples fetcher, reference list fetcher, target ratio calculator, color identity validator, combo validator, Moxfield exporter.

**Skills:** 11 engine archetypes, 7 game plans, 5 win conditions — each as a loadable skill file.

### optimization/
Takes a working draft and makes it better. Runs diagnostics first (package gaps, curve shape, keep rate, mana development), proposes changes, re-simulates after.

**Scripts:** Deck health diagnostic, Monte Carlo goldfish simulator, mana curve analyzer, color pip analyzer, format legality validator, Moxfield/Archidekt deck fetcher.

---

## Prerequisites

```bash
pip install requests playwright
playwright install chromium
```

Scripts run against the Scryfall API, EDHREC, Moxfield, and Archidekt. No API keys required.

---

## Getting Started

1. Open the workspace in Claude Code (`claude` in the project root)
2. Start a conversation — the agent reads `CLAUDE.md` automatically
3. Say what you want: *"I want to build a new deck"* or *"here's a deck I want to tune"*

The agent handles the rest. No slash commands needed to begin.

---

## File Conventions

| Content | Pattern | Location |
|---------|---------|----------|
| Brew (WIP) | `[slug]-[status].md` | `deckbuilding/brews/` |
| Finalized deck | `[slug]-final.md` | `deckbuilding/decklists/` |
| Optimization session | `[deck]-[YYYY-MM-DD].md` | `optimization/sessions/` |

**Statuses:** `draft` → `review` → `final`

---

## Structure

```
MTG Commander Builder/
├── CLAUDE.md               ← Agent entry point (always loaded)
├── CONTEXT.md              ← Workspace map and pipeline overview
├── _shared/
│   └── voice.md            ← Persona and tone instructions
├── Ideation/               ← Phase 1: discover what to build
│   ├── CONTEXT.md
│   ├── docs/               ← playstyles.md, brackets.md
│   ├── skills/             ← ideate.md
│   └── scripts/            ← EDHREC + Scryfall fetchers
├── deckbuilding/           ← Phase 2: build the deck
│   ├── CONTEXT.md
│   ├── docs/               ← formats, archetypes, card evaluation
│   ├── skills/             ← brew-commander, card-search, archetype files
│   ├── brews/              ← WIP decklists
│   ├── decklists/          ← Finalized decklists
│   └── scripts/            ← Generation, validation, export
└── optimization/           ← Phase 3: tune and finalize
    ├── CONTEXT.md
    ├── docs/               ← mana base theory, sideboard guide
    ├── skills/             ← tune-deck, mana-base, meta-check
    ├── sessions/           ← Optimization session notes
    └── scripts/            ← Diagnostics, simulation, analysis
```
