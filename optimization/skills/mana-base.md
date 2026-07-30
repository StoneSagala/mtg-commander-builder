# Skill: /mana-base

## What This Skill Does

Builds or repairs a deck's mana base using Frank Karsten's methodology. Takes a decklist (non-land cards) and a format, outputs a complete, mathematically-grounded land configuration.

**Trigger:** Use when building a new mana base, fixing an existing one, or when the optimization session identifies mana consistency problems.

---

## Inputs Required

- Complete non-land card list (with counts)
- Format
- Budget constraints (if any)
- Known problems (optional: "I keep getting color-screwed on red", "I flood too often")

---

## The Mana Base Workflow

### Step 1: Run Color Analysis

```bash
python scripts/color-analysis.py [deckfile]
```

This outputs a breakdown of pip requirements by color and by turn. Record the output — it drives all subsequent decisions.

**Key numbers to extract:**
- Total colored pip count per color
- Highest pip requirement at each CMC (e.g., "WW on turn 2 for Wrath" or "BB on turn 1 for Thoughtseize")
- Any hybrid costs or split requirements

---

### Step 2: Determine Land Count

Reference: `optimization/docs/mana-base-theory.md`

| Archetype | Land Count |
|-----------|-----------|
| Aggro (60-card) | 20-22 |
| Midrange (60-card) | 22-24 |
| Control (60-card) | 25-27 |
| Commander | 37-40 |

If unsure, use: `Land count ≈ (Avg CMC × 7) + 1` for 60-card decks.

---

### Step 3: Calculate Source Requirements

Use Karsten's table from `optimization/docs/mana-base-theory.md`.

For each color, find the most demanding spell (most pips at earliest turn) and find the minimum source count.

**Example:**
- Deck has Thoughtseize (1B, want turn 1): needs 14 black sources
- Deck has Tarmogoyf (1G, want turn 2): needs 10 green sources
- Deck has Liliana of the Veil (1BB, want turn 3): needs 14+ black sources

The more demanding requirement wins. In this case: 14 black, 10 green → Golgari midrange needs ~14 black sources and ~10 green sources across 22-24 lands.

---

### Step 4: Build the Land Base

Work through the tier hierarchy from `optimization/docs/mana-base-theory.md`.

**60-Card Process:**

1. **Fetch lands first** (if format-legal): Count how many fetch targets you need. Each fetch + shock gives you access to 2 colors.
   - Modern/Legacy: Misty Rainforest, Verdant Catacombs, Scalding Tarn, etc.
   
2. **Add shock lands** as fetch targets (format dependent)
   - Modern/Pioneer: Overgrown Tomb, Steam Vents, etc.

3. **Fill remaining slots** with:
   - Dual lands appropriate to the format (check lands, pain lands, fast lands)
   - Utility lands (1-3 maximum for competitive)
   - Basic lands (enough to have a fetchable target for each color + some redundancy)

4. **Check source counts** against Step 3 requirements. Add or remove accordingly.

**Commander Process:**

1. Command Tower (always, slot 1)
2. Relevant shock lands for the color combination
3. Check lands / pain lands
4. Triomes if in 3+ colors (fetchable)
5. Utility lands (3-5 slots)
6. Basic lands to reach 37-40 total
7. Arcane Signet and 2-3 additional mana rocks (not lands, but part of the mana package)

---

### Step 5: Validate Against Problems

If the user reported specific problems:

- **"I get color-screwed on [Color]"** → Count sources again. If sources meet minimum, the problem may be the land ordering decisions at hand evaluation — note this.
- **"I flood too often"** → Consider reducing land count by 1-2. Or add more utility lands that become spells in the late game.
- **"I can't cast my spells on curve"** → The pip requirements aren't being met. Add more sources of the relevant color.
- **"I take too much damage from my lands"** → Too many shock/pain lands. Shift toward check lands or basics.

---

### Output Format

```markdown
# Mana Base: [Deck Name]
# Format: [Format]
# Date: [YYYY-MM-DD]

## Pip Requirements (from color-analysis.py)
- White: XX pips (most demanding: [spell] at CMC X — needs XX sources)
- Blue: XX pips
- [etc.]

## Land Count: XX

## Land Configuration

Fetch Lands (X):
...

Shock Lands (X):
...

Dual Lands (X):
...

Utility Lands (X):
...

Basic Lands (X):
...

## Source Count Verification
- White sources: XX / XX needed ✓
- Blue sources: XX / XX needed ✓

## Notes
[Any compromises made, budget alternatives, or flags for further review]
```

---

## Budget Alternatives

If the optimal mana base is too expensive:

| Replace | With |
|---------|------|
| Fetch + Shock (Modern) | Check lands (Hinterland Harbor, etc.) |
| Any shock land | Pathway dual (Barkchannel Pathway) or pain land |
| Multiple pain lands | Tap duals (accept slower, save money) |
| Expensive utility lands | Budget equivalents or basics |

For Commander budget mana bases, always include:
- Command Tower (free/cheap)
- Arcane Signet (~$2)
- Slow fetches (Evolving Wilds, Terramorphic Expanse) for basic land fixing
- Check lands (~$2-8 each)
- Tap duals to fill remaining slots

---

## When to Stop and Flag

Flag to the user if:
- Meeting pip requirements for both colors is mathematically impossible with a competitive mana base (the color combination may be too demanding — suggest cutting or modifying spells)
- The deck's mana base will necessarily be slow due to format constraints (Pioneer fetchless, budget, etc.) — manage expectations
