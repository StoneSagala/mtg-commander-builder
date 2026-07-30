  # Skill: /brew-commander

## What This Skill Does

Builds a Commander deck from scratch using a completed build brief. Every phase uses data from the brief — do not re-ask for information already captured there.

**Trigger:** Use when a build brief exists in `deckbuilding/brews/` (as `[slug]-draft.md`) and the player is ready to build.
**Requires:** A completed brief from `/ideate`.

---

## Phase 0: Read the Brief + Run Setup Scripts

Before anything else, run these five scripts in parallel where possible — they front-load all data fetching so no searching or calculating happens during card selection.

**1. Verify color identity (ground truth from Scryfall):**
```bash
python deckbuilding/scripts/validate-color-identity.py --commander "[Commander Name]" --identity-only
```

**2. Auto-generate starter draft (replaces manual card selection phases):**
```bash
python deckbuilding/scripts/generate-starter-deck.py \
  --commander "[Commander Name]" \
  --bracket [1-5] \
  --engine [slug] \
  --game-plan [slug] \
  --win-con [slug] \
  --budget [amount] \
  --output deckbuilding/brews/[slug]-draft.md
```
This script fetches EDHREC staples, enriches prices from Scryfall, calculates targets, and auto-fills ~85-95% of the deck by synergy score. The output file is the working draft — you review and swap, not build from scratch. If the EDHREC pool is thin (niche commander), the summary will warn you how many slots are unfilled.

**Art/flavor themed deck?** Add `--art-theme "keyword1 keyword2"`. Theme slots are filled by Scryfall art search instead of EDHREC synergy — structural slots (ramp, draw, interaction) still come from EDHREC. First run `fetch-art-cards.py` to explore which keywords return good results:
```bash
python deckbuilding/scripts/fetch-art-cards.py --art "smile balloon" --color-identity WR
python deckbuilding/scripts/generate-starter-deck.py \
  --commander "Pinkie Pie" --bracket 3 --engine tokens --game-plan go-wide --win-con life-depletion \
  --art-theme "smile balloon party" --budget 200 \
  --output deckbuilding/brews/pinkie-pie-draft.md
```

**3. Fetch EDHREC's pre-categorized card pool (for review reference):**
```bash
python deckbuilding/scripts/fetch-commander-staples.py "[Commander Name]"
```
Use this during review to find better options for any slot the generator filled weakly.

**4. Pull reference decklists:**
```bash
python deckbuilding/scripts/fetch-reference-lists.py "[Commander Name]" --top 3
```
Omit `--theme` — Moxfield searches deck titles/descriptions, not card lists. Archidekt still accepts `--theme`.

**5. Calculate adjusted build targets (verify generator targets):**
```bash
python deckbuilding/scripts/calculate-target-ratios.py \
  --commander "[Commander Name]" \
  --bracket [1-5] \
  --engine [slug] \
  --game-plan [slug] \
  --win-con [slug]
```
Include `--partner "[Partner Name]"` if applicable. The generator uses the same bracket baseline + strategy overrides, but this script additionally detects commander-provided functions (draw, ramp, board control) and adjusts for them. **Compare its output to the generator's targets** — if they differ significantly, the commander provides a function the generator missed. Override those slots during review.

These five outputs replace all card searching and manual card selection. Do not run Scryfall searches during the brew.

Then load the brief and extract:

| Field | Used In |
|-------|---------|
| Commander name | All phases |
| Color identity | Phase 1, all card selection, legality checks |
| Theme / playstyle | Phase 2 (strategy requirements) |
| Bracket | Phase 2 (game changer limits), Phase 7 (interaction scale) |
| Commander dependency | Phase 1 (floor plan), Phase 8 (backup game plan) |
| Interaction style | Phase 7 (utility package size) |
| Budget | Phase 4 (ratios), all card selection |
| Cards to include | Phase 3 (locked in immediately) |
| Cards to avoid | All phases |
| House rules | Phase 2, legality checks |

State what you've loaded before proceeding:
> "Reading brief: [Commander], [Color Identity], Bracket [X], [Theme], [Interaction Style] interaction, [Commander Dependency] dependency. Cards to include: [list]. Budget: $[X]."

---

## Phase 1: Commander Analysis

Work through the card text line by line:

1. **What does it cost?** High CMC commanders are vulnerable early and costly to recast. Low CMC commanders can be recast aggressively.
2. **What does it do when in play?** Does it generate value passively, or does it need to attack / tap / connect?
3. **What does it need to be active?** Creatures on board? A full hand? Combat damage? Specific card types?
4. **What is the primary win condition?** How does this commander help close the game?
5. **What shuts it down?** Removal, tuck effects, stax pieces, specific hate cards?
6. **What's the floor?** Based on the brief's commander dependency setting:
   - *Fight through it* → the deck is built to keep recasting; prioritize cost reduction and protection
   - *Have a backup* → identify a secondary game plan that functions without the commander
   - *Not a concern* → commander is a bonus; the 99 wins on its own

**Anti-synergy check:** List 3–5 card types or effects that would actively work against this commander's strategy. These are auto-excludes during card selection.

**Commander function inventory — fill this out before Phase 4:**

| Function | Does the commander provide it? | Notes |
|----------|-------------------------------|-------|
| Board control / sweeping | Yes / No / Partial | e.g. Toxrill passively removes creatures and doesn't need wipes |
| Card draw / hand refill | Yes / No / Partial | e.g. commander draws on ETB, combat, trigger |
| Ramp | Yes / No / Partial | e.g. Selvala taps for mana |
| Win condition | Yes / No / Partial | e.g. commander IS the win con (Voltron, combo piece) |
| Protection | Yes / No / Partial | e.g. built-in hexproof, regenerate, indestructible |
| Mana curve anchor | Yes / No | e.g. Rograkh costs 0 — deck can run 32 lands |

This inventory directly adjusts Phase 4 targets. If the commander provides a function, the 99 needs fewer dedicated slots for it.

**Output:** A 2-paragraph identity statement + the commander function inventory:
- Paragraph 1: What the commander does and what it needs
- Paragraph 2: How the deck wins, what shuts it down, and what the floor plan is
- Table: Commander function inventory (carries into Phase 4)

---

## Phase 2: Strategy Requirements

Before selecting any cards, load the three archetype files that define this deck's structure. They replace all inline archetype content.

```
Load: deckbuilding/skills/archetypes/engines/[brief engine].md
Load: deckbuilding/skills/archetypes/game-plans/[brief game plan].md
Load: deckbuilding/skills/archetypes/win-cons/[brief win condition].md
```

**Engine slug** → file mapping:
`enchantress` `artifacts` `graveyard` `aristocrats` `tribal` `tokens` `counters` `spellslinger` `lands` `blink-etb` `theft-chaos`

**Game plan slug** → file mapping:
`go-wide` `go-tall` `combo` `burn` `stax` `control` `politics`

**Win condition slug** → file mapping:
`life-depletion` `commander-damage` `mill` `poison` `alternate-win-cons`

From the three loaded files, extract:
1. **Non-negotiable card types** for each layer
2. **Anti-synergy cards** to exclude across all three
3. **Common pairings** that suggest additional synergy pieces
4. **Bracket restrictions** relevant to this combination

If the brief has "Not sure yet" for engine or game plan, derive it from the commander analysis in Phase 1 before loading files.

---

## Phase 3: Non-Negotiables

Lock in the following before filling any other slot. **Win conditions go first** — not last. A common deckbuilding mistake is filling synergy and goodstuff slots, then cramming win cons in at the end. Start with how you win; everything else supports that goal.

1. **Win conditions** — lock in win cons before touching any other slot. How many depends on bracket and strategy (set in Phase 4 Step 1–3) — not a fixed number. cEDH runs 1–2 lines + tutors. Bracket 3 runs 5–7 paths. Voltron runs the commander as the primary win con.
2. **Cards from the brief** (player's must-includes) — slot these and note which package they belong to
3. **Strategy non-negotiables** — the cards this archetype literally cannot function without (from Phase 2)
4. **Commander-specific requirements** — cards that make this specific commander's ability work

Format:
```
NON-NEGOTIABLES ([Commander]):
- [Card]: [Why required — not just "it's good"]
- [Card]: [Why required]
```

This list is locked. Do not cut these during Phase 10 unless a legality issue forces it.

---

## Phase 4: Target Ratios

**The `calculate-target-ratios.py` script from Phase 0 has already done this calculation.** Use its output as the starting point. This phase is a review, not a calculation from scratch.

Review the script output for:
1. **Review flags** — any indirect functions the script couldn't confidently detect (e.g. Toxrill's slugs as board control). Apply your judgment and override the target if needed.
2. **Anything the brief changes** — house rules, unusual constraints, or a card in the include list that acts as an extra win con or sweeper.
3. **Avg deck CMC** — if the 99 is trending high after Phase 3, adjust lands and ramp up from the script's targets.

Once reviewed, write out the final targets explicitly before building:

```
FINAL TARGETS ([Commander], Bracket [X]):
- Lands: [X] ([reason if different from script output])
- Ramp: [X]
- Card draw: [X]
- Interaction: [X] ([X] removal, [X] protection, [X] sweepers)
- Win conditions: [X] ([list the paths])
- Tutors: [X]
- Theme / synergy: ~[X] remaining slots
```

If the script could not run, use the manual calculation below.

---

### Manual Calculation (if script unavailable)

Targets are not fixed. Calculate in three steps: start with the bracket baseline, subtract what the commander already provides, then check for strategy overrides.

---

### Step 1: Bracket Baseline

Different brackets play completely different games. Start here.

| Package | Bracket 1–2 | Bracket 3 (baseline) | Bracket 4 | Bracket 5 (cEDH) |
|---------|------------|----------------------|-----------|------------------|
| Lands | 37–38 | 36–38 | 32–36 | 28–33 |
| Ramp | 10–12 | 8–12 | 8–10 (fast mana prioritized) | 5–8 + fast mana (Mox, Crypt, Vault) |
| Card draw | 8–10 | 8–10 | 8–10 | 6–8 (cantrips count) |
| Interaction | 10–12 | 8–10 | 8–12 | 8–12 (counterspells primary) |
| Win conditions | 5–7 paths | 5–7 paths | 2–4 paths + tutors | 1–2 lines + 8–10 tutors |
| Board wipes | 2–3 | 2 minimum | 1–2 | 0–1 (speed beats sweepers) |
| Tutors | 0–2 | 0–4 | 4–8 | 8–12 |

**cEDH (Bracket 5) philosophy is fundamentally different:** the goal is to find and execute 1 win line as fast as possible. More win cons = more dead draws. Tutors replace redundancy. Don't apply Bracket 3 logic to Bracket 4-5 decks.

**Bracket 1–2 philosophy:** slower games, more unknowns, more redundancy needed. Players see more of their deck over longer games, so efficiency matters less than resilience.

---

### Step 2: Commander Substitution

Using the function inventory from Phase 1 — reduce the Phase 4 targets for any function the commander already provides:

| Commander provides | Reduce this target |
|--------------------|-------------------|
| Passive board control (removes creatures without spells) | Board wipes: –1 to –2 (can reach 0 if commander is a continuous sweeper) |
| Card draw on trigger / passive | Card draw: –2 to –4 |
| Ramp ability | Ramp: –2 to –3 |
| Commander IS the win condition | Win conditions: count the commander itself, adjust down |
| Very low CMC anchor (0–1 mana) | Lands: can drop 3–5 below baseline |
| Built-in protection | Protection pieces: –1 to –2 |

**Examples:**
- Toxrill, the Corrosive: passive creature removal → board wipes drop to 0–1. His slug tokens + drain is the win condition → reduces separate win con count.
- Rograkh and Kediss: 0-mana commander anchor → land count drops to 30–33. Voltron win con built in → fewer separate win cons needed.
- Selvala, Heart of the Wilds: taps for mana → reduces dedicated ramp slots by 2–3.
- Thrasios and Tymna (cEDH): Thrasios draws and ramps, Tymna draws → card draw baseline drops significantly.

---

### Step 3: Strategy Overrides

Some game plans change the math regardless of commander or bracket:

| Strategy | Override |
|----------|----------|
| Voltron (commander damage) | Win con count drops — commander IS the win con; add protection instead |
| Stax | Interaction goes up (8–12), board wipes may drop (your board survives; theirs doesn't) |
| Combo (deterministic) | Win con count drops to 1–3 lines; tutors and redundancy go up |
| Control | Interaction goes up (10–14), win cons can be fewer (win from inevitability) |
| Go-wide tokens | Board wipes become dangerous to your own board — pick asymmetrical sweepers only |
| Graveyard (self-mill) | Lands can run lower (lands in yard = more resources); shuffle effects become anti-synergy |

---

### Step 4: Final Targets

After applying Steps 1–3, write out the adjusted targets before building:

```
ADJUSTED TARGETS ([Commander], Bracket [X]):
- Lands: [X] (baseline [X] – [reason for adjustment])
- Ramp: [X] (baseline [X] – commander provides ramp)
- Card draw: [X]
- Interaction: [X] (breakdown: [X] removal, [X] protection, [X] sweepers)
- Win conditions: [X] paths (breakdown: [list])
- Tutors: [X]
- Theme / synergy: remaining ~[X] slots
```

This becomes the budget for Phases 5–7.

---

### Turn Mapping

Assign every card a primary turn window. Cards without a clear window are often wrong for the deck.

- **Turns 1–2:** ramp, fast mana, cantrips
- **Turns 2–4:** core engine pieces, cheap interaction, commander (if low CMC)
- **Turns 4–6:** commander (if mid CMC), value engines, win condition setup
- **Turns 6+:** finishers, high-impact plays, alternate win cons

Each card should have a primary role. A card can ramp AND interact — but you should know which category you're counting it toward in your targets.

---

### Budget Distribution

- 30–40% on the mana base (lands matter most for consistency)
- 30–40% on key non-negotiable and win condition pieces
- Remaining on synergy and utility slots
- Use budget alternatives for anything outside the top priority

---

## Phase 5: Draft Review + Non-Negotiables

The `generate-starter-deck.py` output from Phase 0 is the working draft. This phase reviews and refines it — not builds from scratch.

**Step 1: Open the draft file and read the AI Review Checklist at the bottom.**

**Step 2: Slot non-negotiables (Phase 3 cards) into the draft.**
Non-negotiables belong in the deck regardless of synergy score. For each:
- Find the weakest card in the relevant section (lowest synergy, doesn't advance the win condition)
- Replace it with the non-negotiable
- If no weak card exists, expand that section by 1 and cut from Theme/Synergy instead

**Step 3: Verify each slot — is the best card in place?**
Using the EDHREC staples pool output (Phase 0 script 3) as reference:
- **Ramp:** Does the ramp match the deck's strategy type? (Artifacts → rocks; Green → land ramp; rituals for combo)
- **Card Draw:** Is draw triggering off what the deck does naturally (ETBs, sacrifices, spell casts)?
- **Interaction:** Right ratio of removal vs. sweepers vs. counterspells for the interaction style?
- **Win Conditions:** At least 2 distinct paths to winning?
- **Theme/Synergy (standard):** At least 60% of theme slots directly support the combo/strategy?
- **Theme/Synergy (art theme):** Do the cards fit the art/flavor concept AND contribute mechanically? Dead weight (bad ETB, no board impact, no synergy) should be swapped for art cards that at least do *something*.

Use `/card-search` only when a slot is clearly wrong and the staples pool has nothing better.

**Step 4: Cross-reference reference decklists (Phase 0 script 4).**
Experienced pilots often include 2–4 non-obvious cards. If a card appears in 2+ reference lists but is missing from the draft, consider adding it.

**Step 5: Backup game plan (only if brief's dependency = "Have a backup").**
Verify 2–4 cards carry the strategy without the commander. If none do, flag to the player.

**Step 6: Mana base sanity check.**
The generator splits basics evenly by color count. Verify:
- Does the color split match pip requirements? (e.g., 3 black pips in key cards → more Swamps than Islands)
- Are there 2–4 utility lands relevant to the strategy?
- Budget mana base: Command Tower + signets + check lands + basics is sufficient for brackets 2–3

---

## Phase 11: Legality Checks

Run the comprehensive validator — it covers all rules, bracket compliance, and ban list in one pass:

```bash
python deckbuilding/scripts/validate-deck.py \
  --file deckbuilding/brews/[slug]-draft.md \
  --commander "[Commander Name]" \
  --bracket [1-5] \
  --budget [budget limit] \
  --exclude "[house rule card 1]" "[house rule card 2]"
```

This checks:
- Card count (exactly 100)
- Singleton (no duplicates)
- Commander legality
- Color identity (every card)
- Ban list (every card via Scryfall)
- Game Changer count vs bracket cap
- Extra turn cards vs bracket policy
- Mass land denial vs bracket
- House rule exclusions

Fix every `✗ FAIL` before proceeding. The script exits with a non-zero code on any violation.

**Combo Validation (run separately if the deck has intended combos):**
```bash
python deckbuilding/scripts/validate-combos.py --cards "[Card 1]" "[Card 2]" "[Card 3]"
```
Read the **Rules Notes** on every result — these explain exactly why a combo does or doesn't work. Do not include a combo the script flags as broken or illegal.

---

## Phase 12: Final Validation

A quick-pass check before writing the output. Flag any that fail.

Validate against the **adjusted targets from Phase 4 Step 4** — not the baseline. Flag deviations from the targets you actually set, not generic numbers.

| Check | Target | Flag If |
|-------|--------|---------|
| Avg CMC | < 3.5 most decks; < 2.0 for low-curve builds | > 4.0 without heavy ramp to support it |
| Lands | Per Phase 4 adjusted target | More than 2 below or above adjusted target |
| Ramp count | Per Phase 4 adjusted target | Below adjusted minimum |
| Card draw | Per Phase 4 adjusted target | Below adjusted minimum with no passive engine |
| Win conditions | Per Phase 4 adjusted target | Below adjusted target |
| Win con diversity | Per strategy: 2+ paths (Bracket 1–3); 1 line is fine (Bracket 4–5 with tutors) | 0 clear win lines |
| Board wipes | Per Phase 4 adjusted target (can be 0 if commander replaces this) | Below adjusted target |
| Interaction | Per Phase 4 adjusted target | Below adjusted target |
| Synergy density | 60%+ on-theme | Below 50% |
| Game Changer count | Within bracket | Over bracket cap |
| Budget | Within brief ceiling | Over by >10% |

---

## Output Format

```
# [Commander Name] — Commander
# Theme: [1-line description]
# Bracket: [1–4] | Avg CMC: [X.X] | Budget: ~$[X]
# Date: [YYYY-MM-DD]

## Non-Negotiables
- [Card]: [Why]

## Deck

Commander:
1 [Commander Name]

Lands ([XX]):
...

Ramp ([XX]):
...

Card Draw ([XX]):
...

[Theme Package] ([XX]):
...

Utility ([XX]):
...

Win Conditions ([XX]):
...

## Validation Summary
- Ramp: [X] pieces (target: [X]) ✓/✗
- Card draw: [X] sources ✓/✗
- Win conditions: [X] paths ✓/✗
- Game Changers: [X] / [bracket max] ✓/✗
- Avg CMC: [X.X] ✓/✗
- Budget: ~$[X] ✓/✗
- Legality: ✓/✗
```

Save to `deckbuilding/brews/[slug]-draft.md`.

---

## Auto-Optimization Pass

After saving the draft, immediately run the full optimization pipeline. Do not ask — just run it.

**Step 1: Diagnostics**
```bash
python optimization/scripts/deck-health.py \
  --file deckbuilding/brews/[slug]-draft.md \
  --commander "[Commander Name]" \
  --bracket [1-5] \
  --budget [budget]
```

**Step 2: Goldfish simulation**
```bash
python optimization/scripts/goldfish.py \
  --file deckbuilding/brews/[slug]-draft.md \
  --commander "[Commander Name]" \
  --key-cards "[win con pieces from Phase 3]" \
  --games 1000 \
  --turns 8
```

**Step 3: Apply changes**
Work through Steps 2–6 of `/tune-deck` using the diagnostic output. Apply all changes directly to `deckbuilding/brews/[slug]-draft.md` — no approval needed. This is auto-apply mode: changes go in, the file is updated, then the player is told what happened.

**Step 4: Save session notes**
Save to `optimization/sessions/[slug]-[YYYY-MM-DD].md` using the standard session note format.

**Step 5: Report**
After applying changes, tell the player in plain language:
- What the diagnostics flagged (keep it short — 2–4 bullets)
- What was swapped in/out and why (brief summary, not the full change list)
- Before/after simulation numbers (keep rate, T4 mana, key piece %)

---

## Final Step: Moxfield Export

After saving the file, ask the user:

*"Would you like me to copy the decklist to your clipboard so you can paste it into Moxfield?"*

If yes, run:

```bash
python deckbuilding/scripts/export-to-moxfield.py \
  --file deckbuilding/brews/[slug]-draft.md \
  --commander "[Commander Name]"
```

This copies the full 100-card list — no headers, just `quantity CardName` per line — directly to the clipboard. The user can paste it straight into Moxfield's deck import.
