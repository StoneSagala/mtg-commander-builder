# Deckbuilding Workspace

## Workflow contract
- **Inputs:** Approved `brews/[slug]-draft.md`; `skills/brew-commander.md`; `_shared/data-sources.md` at repository root.
- **Process:** Generate a separate draft, review cards against the brief, fill gaps with verified searches, then validate.
- **Outputs:** `brews/[slug]-generated.md` → `brews/[slug]-review.md`. Preserve the approved brief.
- **Human check:** Review missing slots, provenance, total budget, bracket and win conditions before optimization. Do not assume automatic coverage or validation.


## What This Workspace Is

Where concepts become decklists. Input is either a brew starter file created by Ideation (containing the approved brief header) or a direct commander/format idea. The agent researches, structures, and drafts a complete, coherent deck. Output goes to `brews/` and eventually `decklists/`, feeding into the optimization pipeline.

---

## What to Load

| Task                                  | Load These                                                | Skip These                                      |
| ------------------------------------- | --------------------------------------------------------- | ----------------------------------------------- |
| Choose an archetype                   | `docs/archetypes.md`                                      | `docs/formats.md` (skip until format is chosen) |
| Evaluate whether a card makes the cut | `docs/card-evaluation.md`                                 | `docs/archetypes.md`                            |
| Review/refine an existing brew        | The brew itself, `docs/card-evaluation.md`                | `docs/archetypes.md`                            |

---

## Folder Structure

```
deckbuilding/
├── CONTEXT.md          ← You are here
├── docs/               ← Reference docs (load per-task)
│   ├── formats.md      ← Format rules, deck sizes, current ban lists
│   ├── archetypes.md   ← Aggro, control, combo, midrange, tempo patterns
│   ├── card-evaluation.md ← How to evaluate a card for inclusion
│   └── game-changers.md   ← High-impact cards that warp game states
├── skills/
│   ├── brew-commander.md  ← Commander/EDH deck brewing workflow
│   ├── card-search.md     ← Structured card search by function/synergy
│   └── archetypes/
│       ├── engines/       ← 11 engine files (enchantress, artifacts, graveyard, etc.)
│       ├── game-plans/    ← 7 game plan files (go-wide, combo, stax, control, etc.)
│       └── win-cons/      ← 5 win condition files (life-depletion, mill, poison, etc.)
├── brews/              ← Work-in-progress decklists ([slug]-[status].md)
├── decklists/          ← Finalized, battle-ready decklists ([slug]-final.md)
└── scripts/
    ├── fetch-commander-staples.py      ← EDHREC card pool pre-sorted by category (run at Phase 0)
    ├── fetch-reference-lists.py        ← Top public reference decklists from Moxfield + Archidekt (run at Phase 0)
    ├── calculate-target-ratios.py      ← Dynamic Phase 4 targets: bracket baseline + commander substitution + strategy overrides (run at Phase 0)
    ├── validate-deck.py                ← Comprehensive validator: rules + bracket + ban list (Phase 11)
    ├── validate-color-identity.py      ← Targeted color identity check (quick spot-check during building)
    ├── validate-combos.py              ← Commander Spellbook combo validation with rules notes
    └── fetch-card-data.py              ← Individual card lookup (text, mana cost, stats)
```

---

## The Process

### For Commander Decks
Use skill `/brew-commander` — it handles the structured workflow:
1. Identify commander and primary strategy
2. Define the "engine" (card draw, ramp, win conditions)
3. Build synergy package (cards that support the strategy)
4. Fill utility slots (interaction, protection, removal)
5. Build the mana base (basic + non-basic balance)
6. Cut to 100 — every card must earn its slot

### For 60-Card Formats
1. **Lock the archetype** — is this aggro, control, combo, midrange?
2. **Define the game plan** — what does turn-1 through turn-5 look like?
3. **Select the core** — the 8-12 cards the deck cannot function without
4. **Fill supporting roles** — interaction, card advantage, threats
5. **Build the mana base** — use `optimization/docs/mana-base-theory.md` and script `optimization/scripts/color-analysis.py`
6. **Move to optimization** when the 60 are slotted

A brew becomes `review` when every slot is filled. It becomes `final` when the mana base is solved and the list has been through at least one optimization pass.

---

## Skills & Tools for This Workspace

| Skill / Tool | When to Use | How |
|-------------|-------------|-----|
| `skills/brew-commander.md` | **Commander decks only.** Activates the structured EDH brew workflow. | Provide commander name and theme. Skill guides through engine → synergy → utility → mana base. |
| `skills/card-search.md` | **Finding cards not in the staples pool.** Use inline when a specific card type isn't covered by EDHREC data. | Describe the need in plain language; skill translates to Scryfall query. |
| `scripts/generate-starter-deck.py` | **Phase 0 — run first.** Builds a provisional draft from EDHREC + Scryfall, with a labelled Scryfall fallback. Coverage varies; win conditions need review. Add `--art-theme "keywords"` for art/flavor themed decks — theme slots filled by Scryfall art search instead of EDHREC. | `python deckbuilding/scripts/generate-starter-deck.py --commander "Name" --bracket 3 --engine graveyard --game-plan combo --win-con life-depletion --budget 200 --output deckbuilding/brews/slug-generated.md` |
| `scripts/fetch-art-cards.py` | **Art/flavor themed decks.** Searches Scryfall illustration tags to build an art-themed card pool. Run this first to explore which keywords return good results before passing `--art-theme` to generate-starter-deck. | `python deckbuilding/scripts/fetch-art-cards.py --art "smile balloon" --color-identity WR --budget 5` |
| `scripts/fetch-commander-staples.py` | **Phase 0 — reference pool.** Shows full EDHREC card pool by category for review during Phase 5. | `python deckbuilding/scripts/fetch-commander-staples.py "Commander Name"` |
| `scripts/fetch-reference-lists.py` | **Phase 0 — run first.** Fetches top reference decklists from Moxfield + Archidekt. | `python deckbuilding/scripts/fetch-reference-lists.py "Commander Name" --top 3` |
| `scripts/calculate-target-ratios.py` | **Phase 0 — run first.** Calculates adjusted build targets from bracket baseline, commander functions, and strategy overrides. AI reviews output and overrides where judgment differs. | `python deckbuilding/scripts/calculate-target-ratios.py --commander "Name" --bracket 3 --engine graveyard --game-plan combo --win-con life-depletion` |
| `scripts/validate-deck.py` | **Phase 11 — run this first.** All-in-one: rules + bracket + ban list + budget in one pass. | `python deckbuilding/scripts/validate-deck.py --file brew.md --commander "Name" --bracket 3 --budget 150` |
| `scripts/export-to-moxfield.py` | **Final step — optional.** Copies the decklist to clipboard in Moxfield import format (no headers, quantity + card name per line). Ask the user before running. | `python deckbuilding/scripts/export-to-moxfield.py --file brew.md --commander "Name"` |
| `scripts/validate-combos.py` | **Phase 11 — combo check.** Validates combos against Commander Spellbook, returns rules notes. | `python deckbuilding/scripts/validate-combos.py --cards "Card 1" "Card 2"` |
| `scripts/validate-color-identity.py` | **Mid-build spot check.** Quick color identity check on specific cards during building. | `python deckbuilding/scripts/validate-color-identity.py --commander "Name" --cards "Card 1"` |
| `scripts/fetch-card-data.py` | **Card lookup.** When you need exact card text, mana cost, or power/toughness for a specific card. | `python deckbuilding/scripts/fetch-card-data.py "Card Name"` |

---

## Deck List Format

Always write decklists in this standard format:

```
# [Deck Name] — [Format]
# [Date]

Commander:
1 [Card Name]

Lands (XX):
4 [Land Name]
...

Creatures (XX):
4 [Creature Name]
...

Spells (XX):
4 [Spell Name]
...

Sideboard (if applicable):
4 [Card Name]
...
```

---

## What NOT to Do

- **Don't skip `docs/formats.md`** when legality matters — putting a banned card in a brew wastes the whole session
- **Don't over-fill** — a list over 100 cards needs cutting to reach 100; start tight
- **Don't solve the mana base here** — that's `optimization/`'s job. Rough in basics and a skeleton of non-basics, then hand off
- **Don't load optimization docs** during the brew phase — you're generating cards, not analyzing them yet
- **Don't create files outside this workspace** — when ready for optimization, copy the brew to `optimization/sessions/`
