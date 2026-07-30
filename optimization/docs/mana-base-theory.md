# Mana Base Theory

## The Frank Karsten Method

This doc is based on Frank Karsten's mathematical mana base analysis, widely considered the gold standard for constructed mana base construction.

**Core principle:** You need to cast your spells on curve, on time, consistently. The mana base exists to make that possible. Every land selection decision should answer: "Does this help me cast my spells when I need to?"

---

## 60-Card Deck Mana Base

### How Many Lands?

| Deck Type | Land Count | Why |
|-----------|-----------|-----|
| Aggro | 20-22 | Low curve; 3-4 lands is plenty to function |
| Midrange | 22-24 | Needs consistent 3-4 land openers |
| Control | 25-27 | Needs to hit land drops through turn 6-7 |
| Combo | 18-22 | Depends entirely on the combo's mana requirements |

**Formula (rough):** Land count ≈ (Average CMC of non-land cards × 7) + 1

### Pip Requirement Math

For each color symbol in your deck, count the pips (the colored mana symbols in casting costs).

**Rule of thumb:**
- If you need {C}{C} on turn 2 (e.g., Thoughtseize at 1B vs BB card): need ~14 sources of Black
- If you need {C} on turn 3: need ~10-12 sources
- If {C}{C}{C} on turn 3: need ~18+ sources (hard to achieve in 2-color)

**Karsten's table (simplified) — sources needed to cast on turn N with 90% consistency:**

| Symbols Needed | Turn 1 | Turn 2 | Turn 3 | Turn 4 |
|----------------|--------|--------|--------|--------|
| 1 | 14 | 10 | 9 | 8 |
| 2 | — | 20 | 14 | 12 |
| 3 | — | — | 23 | 18 |

> Use `scripts/color-analysis.py` to automatically count pip requirements for a decklist.

---

## Land Quality Hierarchy (Modern/Pioneer)

Not all lands are equal. Prioritize by tier:

### Tier 1 — Always Untapped, Dual Colored
- **Fetch + Shock:** Scalding Tarn → Steam Vents (costs 1 life to fetch untapped)
- **True Duals (Legacy/Vintage only):** Tropical Island, Underground Sea
- **Surveil/Fast Lands:** Spirebluff Canal, Inspiring Vantage (untapped turns 1-3)
- **Pain Lands:** Shivan Reef, Adarkar Wastes (small downside, always untapped)

### Tier 2 — Conditional Untapped
- **Check Lands:** Glacial Fortress (free if you control a Plains or Island)
- **Pathway Duals:** Needleverge Pathway (pick one side permanently)
- **Horizon Lands:** Silent Clearing (draw a card, comes in untapped, costs life)

### Tier 3 — Enters Tapped
- **Bounce Lands:** Azorius Chancery (returns a land, produces 2 mana — slow but mana positive)
- **Tap Lands:** Tranquil Cove (no upside, just enters tapped — avoid in competitive)
- **Scry Lands:** Temple of Enlightenment (enters tapped but scries — OK in control)

### Utility Lands
Include sparingly — they cost a land slot:
- **Card advantage:** Hall of Storm Giants, Mobilized District, Faceless Haven
- **Mana sinks:** Wandering Fumarole (animator), Hive of the Eye Tyrant
- **Colorless hate:** Field of Ruin, Ghost Quarter (answer to opponent's utility lands)

**Competitive rule:** In Modern/Pioneer, running more than 4 enters-tapped lands is usually wrong for aggro and midrange. Control can tolerate more.

---

## Commander Mana Base

### Total Land Count
37-40 lands is the standard range.
- 37 for low-curve aggressive strategies (average CMC ≤ 2.5)
- 38-39 for midrange (average CMC 3-3.5)
- 40 for high-curve or ramp-dependent strategies

### Non-Basic Land Priority (Commander)

**Tier 1 — Always Run:**
- Sol Ring (not a land, but include in any mana discussion)
- Command Tower (every deck)
- Arcane Signet (not a land, but critical)
- Exotic Orchard / Forbidden Orchard (for multi-color)

**Tier 2 — Run in Appropriate Colors:**
- Shock Lands (Steam Vents, Overgrown Tomb, etc.) — fetch-able, 10-life loss negligible in 40-life Commander
- Check Lands (Glacial Fortress, etc.) — cheap, reliable
- Triomes (Ketria Triome, etc.) — fetch-able, provide 3 colors, enter tapped but fine for Commander
- Pain Lands (Adarkar Wastes, etc.) — reliable, cheap

**Tier 3 — Budget Alternatives:**
- Vivid Lands (Vivid Creek, etc.) — 2 charge counters, enters tapped
- Bounce Lands (Azorius Chancery) — slow but mana-positive
- Tap duals (Tranquil Cove) — only if budget demands

### Basic Land Count
- 2-color decks: 14-16 basics (split proportionally)
- 3-color decks: 10-12 basics
- 4-5 color decks: 5-8 basics (prioritize basics that can be fetched by Cultivate etc.)

### Ramp Package (Commander)
Always include in addition to lands:
- **Sol Ring** (staple, virtually mandatory)
- **Arcane Signet** (2-mana rock for your commander's colors)
- **Mind Stone / Thought Vessel / Worn Powerstone** (utility 2-mana rocks)
- **Cultivate / Kodama's Reach** (Green: fetch 2 basics, put one in hand)
- **Rampant Growth / Three Visits** (Green: basic land fetch)
- **Creature ramp** (Llanowar Elves, Birds of Paradise, Selvala Heart of the Wilds)

---

## Common Mana Base Mistakes

### Mistake 1: Too Many Enters-Tapped Lands
Running 10+ ETL in a competitive 60-card deck costs you a full turn of development. The opponent attacks you for free on the turn you're stuck on 1 mana.

**Fix:** Upgrade to check lands, fast lands, or pain lands.

### Mistake 2: Wrong Color Distribution
Running 10 white sources and 14 blue sources in a W/U deck that has 16 white pips and 8 blue pips. The color allocation is backwards.

**Fix:** Run `scripts/color-analysis.py` and match land distribution to pip counts.

### Mistake 3: Not Enough Sources for Double-Pip Costs
A card like Wrath of God ({2}{W}{W}) needs ~19 white sources to reliably cast on turn 4. Running 12 white sources breaks the deck.

**Fix:** Pip analysis before finalizing the list.

### Mistake 4: Over-Cutting Lands for Interaction
"I'll just run 18 lands and fit in one more removal spell." This causes flooding/drought variance that loses more games than that extra removal spell wins.

**Fix:** Trust the land count formulas. Find cuts elsewhere.

### Mistake 5: Fetchless Color Fixing in Formats Without Fetches
In Pioneer, you can't rely on fetch + shock. You must use a different approach (check lands, pain lands, fast lands).

**Fix:** Know your format's available duals. See `deckbuilding/docs/formats.md`.

---

## Mana Base Checklist

Before marking any mana base as solved:

- [ ] Land count is within range for the archetype
- [ ] Color pip requirements analyzed (use `scripts/color-analysis.py`)
- [ ] Source counts meet Karsten minimums for critical spells
- [ ] Not more than 4 enters-tapped lands (competitive 60-card) or 10 (Commander)
- [ ] Utility lands included if relevant (not mandatory)
- [ ] No format-illegal lands included (run `scripts/validate-decklist.py`)
- [ ] Basic land count is defensible against land destruction (Path to Exile, Field of Ruin)
