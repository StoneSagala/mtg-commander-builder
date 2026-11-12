# Optimization Workspace

## Workflow contract
- **Inputs:** Existing deck or `../deckbuilding/brews/[slug]-review.md`; `skills/tune-deck.md`; shared provider contract `../_shared/data-sources.md`.
- **Process:** Diagnose, simulate, tune mana and cards, rerun checks, and record review decisions.
- **Outputs:** `sessions/[slug]-[YYYY-MM-DD].md`; after player review, `../deckbuilding/decklists/[slug]-final.md`.
- **Human check:** Player reviews changes and evidence before final promotion. Unknown data and failed combo checks must remain explicit.


## What This Workspace Is

Where good decks become great ones. Decks come in two ways:
- **From deckbuilding** — a completed brew file handed off for tuning
- **Directly from the player** — they already have a deck and want to work on it

Either way, get the deck into the system first, then ask what they want to do with it.

---

## Getting the Deck

A player can share their deck three ways:

**1. Pasted list** — plain text, one card per line (`1 Card Name` format) or our standard markdown format. Read it directly from the conversation.

**2. File path** — path to a `.md` brew file. Use the Read tool to load it.

**3. URL** — Moxfield or Archidekt link. Fetch it with:
```bash
python optimization/scripts/fetch-deck.py "https://www.moxfield.com/decks/[id]"
python optimization/scripts/fetch-deck.py "https://archidekt.com/decks/[id]/"
```
The script outputs the deck in standard format. Save it to `optimization/sessions/[slug]-[YYYY-MM-DD].md` before doing any work.

**Once you have the deck**, run the diagnostics immediately (see Step 1 in The Process below). Share what you found — package gaps, curve shape, keep rate, mana numbers — then let the player confirm which direction to take. Don't ask open-ended "what do you want to fix?" when the numbers already tell you. Common issues that come up:
- The deck is too slow / inconsistent
- Specific cards aren't pulling their weight
- Mana base feels wrong
- Want to upgrade within a budget
- Getting stomped by a specific matchup
- Just want a second set of eyes

---

## What to Load

| Task | Load These | Skip These |
|------|-----------|------------|
| Fix or build a mana base | `docs/mana-base-theory.md`, the decklist, skill `/mana-base` | `docs/sideboard-guide.md` |
| Tune card counts and curve | The decklist, skill `/tune-deck` | Both docs/ files |
| Build a sideboard | `docs/sideboard-guide.md`, the decklist | `docs/mana-base-theory.md` |
| Check meta positioning | Skill `/meta-check`, Web Search MCP | Both docs/ files |
| Full optimization pass | All of the above, loaded in sequence | — |

---

## Folder Structure

```
optimization/
├── CONTEXT.md                  ← You are here
├── docs/                       ← Reference docs
│   ├── mana-base-theory.md     ← Mana math, Frank Karsten methodology
│   └── sideboard-guide.md      ← Sideboard strategy by format and archetype
├── skills/
│   ├── tune-deck.md            ← Iterative deck optimization workflow
│   └── mana-base.md            ← Mana base calculation and building
├── sessions/                   ← Optimization session notes ([deck]-[YYYY-MM-DD].md)
└── scripts/
    ├── fetch-deck.py           ← Fetch deck from Moxfield or Archidekt URL
    ├── deck-health.py          ← Instant diagnostic: packages, curve, price, flagged issues
    ├── goldfish.py             ← Monte Carlo simulation: keep rate, mana, key piece consistency
    ├── validate-decklist.py    ← Validate format legality and card counts
    ├── mana-curve.py           ← Analyze mana curve distribution
    └── color-analysis.py       ← Color pip requirement analysis
```

---

## The Process

### Full Optimization Pass (recommended order)

**Step 1: Health Check + Baseline Simulation**
The moment the deck is in hand, run both diagnostics before asking the player anything:

```bash
python optimization/scripts/deck-health.py --file [deckfile] --commander "[name]" --bracket [1-5] --budget [N]
python optimization/scripts/goldfish.py --file [deckfile] --commander "[name]" --key-cards "[piece1],[piece2]" --games 1000
```

Read out what was found in plain language — package gaps, curve problems, keep rate, mana development. Then ask which issue they want to tackle first. Don't assume; let the numbers guide the conversation.

**Step 2: Mana Base (if flagged)**
Load `docs/mana-base-theory.md` and skill `/mana-base`. Run `optimization/scripts/color-analysis.py` on the decklist to get pip requirements. Build the land base before touching anything else — a bad mana base breaks every other optimization.

**Step 3: Curve + Card Tuning**
Use skill `/tune-deck`. The skill now integrates both diagnostics and re-simulation steps. Key framework:
- Is this card doing enough work?
- Is there a better card at this slot?
- Commander: 1x only — question is whether to include at all

**Step 4: Re-Simulate**
After changes, run `goldfish.py` again with the same `--key-cards`. Compare keep rate, T4 mana, and key piece consistency against the baseline. If a metric regressed, identify which swap caused it.

**Step 5: Sideboard (60-card formats)**
Load `docs/sideboard-guide.md`. Build a sideboard that covers your 3 worst matchups without diluting your main-deck identity.

**Step 6: Meta Check**
Run `/meta-check` and Web Search MCP. Does the deck compete in the current meta? Are there meta predators that invalidate the strategy?

---

## Skills & Tools for This Workspace

| Skill / Tool | When to Use | How |
|-------------|-------------|-----|
| `scripts/fetch-deck.py` | **Deck intake from URL.** Player shares a Moxfield or Archidekt link. | `python optimization/scripts/fetch-deck.py "https://www.moxfield.com/decks/[id]"` |
| `scripts/deck-health.py` | **First thing, every session.** Package counts, curve, price, flagged issues, optimization menu. | `python optimization/scripts/deck-health.py --file [f] --commander "[n]" --bracket [1-5] --budget [N]` |
| `scripts/goldfish.py` | **Baseline + post-change validation.** Keep rate, mana development, key piece consistency. | `python optimization/scripts/goldfish.py --file [f] --key-cards "[c1],[c2]" --games 1000` |
| `skills/tune-deck.md` | **Card count and slot optimization.** Use after diagnostics. Includes re-simulation step. | Provide the decklist and the deck's intended game plan. Skill evaluates each card's contribution. |
| `skills/mana-base.md` | **Any time the mana base is being built or rebuilt.** Required before finalizing any deck. | Provide the decklist and format. Skill calculates pip requirements and recommends land distribution. |
| Web Search MCP | **Current meta data.** Tier lists, tournament results, top-performing lists. | Search "[format] meta [current month/year]" or "top [format] decks MTGGoldfish" |
| `scripts/mana-curve.py` | **Visual curve analysis.** Supplemental to deck-health if more curve detail needed. | `python optimization/scripts/mana-curve.py deckfile.md` — outputs CMC distribution |
| `scripts/color-analysis.py` | **Pip requirement analysis.** Input for mana base work. | `python optimization/scripts/color-analysis.py deckfile.md` — outputs color symbol counts |
| `../deckbuilding/scripts/validate-deck.py` | **Commander final screening.** Checks current rules, total budget and paired commanders. | From repo root: `python3 deckbuilding/scripts/validate-deck.py --file deckfile.md --commander "Name" --bracket [player bracket]`; add `--partner "Name"` and `--budget [player total]` when supplied. |
| `scripts/validate-decklist.py` | **Legacy non-Commander format check.** Does not certify current Commander bracket or pairing rules. | `python3 optimization/scripts/validate-decklist.py deckfile.md [format]` |

---

## Optimization Targets by Format

| Format | Key Focus | Common Pitfalls |
|--------|-----------|-----------------|
| Commander | Mana ramp density, card draw engine, answer package | Too many win-cons, not enough interaction |
| Standard | Mana consistency, curve vs meta speed | Mana base too slow, over-reliance on 4-ofs |
| Modern | Speed vs resilience, hate card density | Sideboard too narrow, mana base pain |
| Pioneer | Fetchless mana base, format-specific threats | Assuming Modern card quality exists |
| Pauper | Budget mana, common-only synergies | Underestimating format speed |

---

## Saving Sessions

After each optimization pass, save a session note:

```markdown
# [Deck Name] — Optimization Session [YYYY-MM-DD]

## Simulation Baseline
- Keep rate: X%  |  Avg mulligans: X.X  |  T4 mana: X.X
- Key piece ([card name]) by T7: X%  |  Avg assembly turn: TX

## Starting List
[paste the decklist]

## Changes Made
- **Out:** [card] — [reason]
- **In:** [card] — [reason]

## Mana Base Changes
[describe adjustments]

## Simulation After
- Keep rate: X%  |  Avg mulligans: X.X  |  T4 mana: X.X
- Key piece ([card name]) by T7: X%  |  Avg assembly turn: TX

## Net Improvement
[brief summary of what improved and by how much]

## Sideboard Changes
[describe adjustments — 60-card formats only]

## Meta Assessment
[how the deck positions against the current meta]

## Next Steps
[what still needs work]
```

---

## What NOT to Do

- **Don't skip the diagnostics** — run `deck-health.py` and `goldfish.py` first, every time. The numbers tell you what to fix; skipping them means guessing.
- **Don't skip the mana base** — a bad mana base breaks every other optimization. It's always fixed before tuning card slots.
- **Don't optimize without re-simulating** — gut feel is not enough. Run `goldfish.py` before and after to confirm changes actually helped.
- **Don't run `/meta-check` on a casual Commander deck** — meta analysis is for competitive and cEDH contexts.
- **Don't load deckbuilding docs** — you're refining, not reinventing.
- **Before marking a Commander deck final**, run `deckbuilding/scripts/validate-deck.py` from the repo root with the player's bracket, optional total budget and optional second commander, plus `deckbuilding/scripts/validate-combos.py --file [deckfile]`. Complete any required human strategy/bracket review. Use the legacy optimization validator only for its explicitly reviewed non-Commander format scope.
- **Don't optimize without a clear game plan** — if you don't know what the deck is trying to do on turns 1-5, you can't evaluate whether a card earns its slot.
