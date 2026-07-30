# Skill: /tune-deck

## What This Skill Does

Takes an existing decklist and systematically evaluates each card, slot, and count to produce a tighter, more consistent version of the deck. Works for any format.

**Trigger:** Use when a draft deck exists and needs to be refined, not rebuilt.

---

## Before Starting

**Auto-apply mode (called from brew pipeline):** Skip this section entirely. All context comes from the just-completed brew. Apply all changes directly to the file without asking. Report what changed after.

**Manual mode (player brings an existing deck):** Gather:
1. The current decklist (full list, with counts)
2. The deck's intended game plan (1-2 sentence description)
3. Format and bracket (Commander)
4. Any specific problems the user has noticed ("the deck floods", "can't close games", "loses to creature decks")
5. Win condition cards / key combo pieces (for simulation tracking)

If the game plan isn't clear, ask before proceeding. You can't evaluate whether a card earns its slot without knowing what the deck is trying to do.

---

## The Tuning Workflow

### Step 1: Run the Diagnostics

Before touching individual cards, get the full picture in one pass:

```bash
python optimization/scripts/deck-health.py --file [deckfile] --commander "[name]" --bracket [1-5] --budget [N]
```

This produces:
- Package counts vs. bracket baselines (ramp, card draw, interaction, win conditions)
- CMC curve chart
- Total price
- Flagged issues (✗ error / ⚠ warning / ℹ info)
- Prioritized optimization menu

**Then run the goldfish simulation:**

```bash
python optimization/scripts/goldfish.py --file [deckfile] --commander "[name]" --key-cards "[piece1],[piece2]" --games 1000 --turns 8
```

This shows:
- Opening hand keep rate (target: ≥85% natural keeps)
- Mana development per turn (target: ≥4.5 mana by T4)
- How often key pieces arrive and when
- Average turn to assemble win condition

**Look for:**
- Keep rate below 75% → land count problem
- Mana by T4 below 4.0 → ramp is insufficient
- Key piece seen in <30% of games → needs tutors or more card draw
- Curve spike above CMC 4 → deck is too top-heavy

Note the findings. These drive the tuning session.

---

### Step 2: Categorize Every Card

For each card in the deck, assign it a role:

| Role | Description |
|------|-------------|
| Core | The deck cannot function without this card |
| Engine | Generates card advantage or enables the core |
| Threat | Wins the game or advances the board |
| Removal | Answers opponent's threats |
| Interaction | Disrupts opponent's game plan |
| Filler | Fills a slot but could be improved |
| Flex | Situationally powerful but inconsistent |

Any card that doesn't fit a clear role is a **cut candidate**.

---

### Step 3: Apply the Seven Questions

For each card (especially Filler and Flex), ask:

1. **Does this advance the game plan?** If the deck is trying to win on turn 4 with a combo and this card doesn't help assemble or protect the combo, it's wrong.

2. **Is this the best card at this function?** If there's a strictly better card at the same CMC that does the same thing, swap it.

3. **Is this the right count?** 
   - 4-of: Critical to the strategy, want to see every game
   - 3-of: Important but not critical, or 4 copies flood the hand
   - 2-of: Situational, silver bullet, or you only need one in play
   - 1-of: Tutor target (Commander), singleton effect, or extreme flex
   - (Commander: always 1-of — question is whether to include at all)

4. **Does this card do something when answered?** A 3-mana 3/3 that dies to removal and replaces itself with nothing is often wrong. Prefer cards with ETB effects, flash, or resilience.

5. **How many matchups is this good in?** Cards that are good in 80%+ of matchups are core. Cards good in <30% belong in the sideboard.

6. **Does this card require other cards to be good?** Combo-reliant cards need enough support to find them consistently. Evaluate the whole package, not the card in isolation.

7. **Is this a win-more card?** If the card is only good when you're already winning, it's the wrong call. Prefer cards that help you get ahead, not stay ahead.

---

### Step 4: Curve Tuning

After individual card review, look at the curve as a whole.

**Aggro target:**
```
CMC 1: ████████████ (8-12)
CMC 2: ████████████ (8-12)
CMC 3: ████████     (6-8)
CMC 4: ████         (2-4)
CMC 5+: ██          (0-2)
```

**Midrange target:**
```
CMC 1: ████         (2-4)
CMC 2: ████████     (6-10)
CMC 3: ████████████ (8-12)
CMC 4: ████████     (6-8)
CMC 5+: ████        (2-4)
```

**Control target:**
```
CMC 1: ████         (2-4 interaction)
CMC 2: ████████████ (10-14 interaction)
CMC 3: ████████     (6-8 threats/answers)
CMC 4: ████████     (4-6 haymakers/sweepers)
CMC 5+: ████        (2-3 win conditions)
```

Adjust counts of cards to fit the target curve. When you have 5 three-drops and need 8, go back to the cut list for candidates to add at CMC 3.

---

### Step 5: Build the Change List

Produce a clean change list:

```markdown
## Changes

**OUT:**
- 2x [Card Name] — [Reason: too slow, not on theme, better option exists]
- 1x [Card Name] — [Reason]

**IN:**
- 2x [Card Name] — [Reason: better rate, on-theme, fixes the X problem]
- 1x [Card Name] — [Reason]

**Count Changes:**
- [Card Name]: 3 → 4 (core to the strategy, want to see it every game)
- [Card Name]: 4 → 3 (often floods, 3 is enough)
```

---

### Step 6: Mana Base Adjustment

After card changes, re-run `scripts/color-analysis.py`. If pip requirements shifted, adjust the mana base accordingly.

Reference `optimization/docs/mana-base-theory.md` for source count targets.

---

### Step 7: Re-Simulate and Compare

After changes are made, run goldfish again on the updated list:

```bash
python optimization/scripts/goldfish.py --file [deckfile] --key-cards "[same as before]" --games 1000
```

Compare against the baseline run:
- Did keep rate improve?
- Did mana development at T4 improve?
- Did key piece consistency go up?

If numbers got worse, a swap went wrong — review which specific change caused the regression.

---

## Output

Produce:
1. The full revised decklist
2. The change list (what went in/out and why)
3. A before/after comparison of the key simulation numbers (keep rate, T4 mana, key piece %)
4. A 2-3 sentence assessment of the deck's current state and what, if anything, still needs work

Save session notes to `optimization/sessions/[deck]-[YYYY-MM-DD].md`.

Session note format:
```markdown
# [Deck Name] — Optimization Session [YYYY-MM-DD]

## Simulation Baseline
- Keep rate: X%  |  T4 mana: X.X  |  Key piece by T7: X%

## Changes Made
- **Out:** [card] — [reason]
- **In:** [card] — [reason]

## Simulation After
- Keep rate: X%  |  T4 mana: X.X  |  Key piece by T7: X%

## Net Improvement
[brief summary]

## Next Steps
[what still needs work]
```

---

## When to Stop

Stop tuning and flag for the user when:
- The fundamental game plan is incoherent (needs a rebuild, not a tune)
- The mana base requires significant rework (route to `/mana-base` skill)
- The deck needs a full meta positioning analysis (route to `/meta-check` skill)
