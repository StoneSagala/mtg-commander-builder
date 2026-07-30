# Card Evaluation Framework

## The Core Questions

Ask these in order for every card under consideration:

1. **Does this card advance my game plan?** If it doesn't contribute to what the deck is trying to do on turns 1-5, it doesn't belong.
2. **Is the rate good enough?** Compare to known format staples at the same mana cost.
3. **How many situations is this card good in?** Cards that are good in one matchup but dead in others weaken your 75.
4. **Does it replace something?** A new card has to be better than the card it's replacing, not just good in isolation.

---

## Rate Benchmarks by CMC

These are rough "passing grades" for constructed play. A card that doesn't meet these rates needs to compensate with a powerful effect.

| CMC | Creature Rate | Spell Rate |
|-----|--------------|------------|
| 1 | 2/1 or 1/2 with an effect | Bolt (3 damage), removal for 1, cantrip |
| 2 | 2/2 with an effect, or 3/2 | Draw 2, or 2-for-1 removal |
| 3 | 3/3 with an effect, or 4/3 | Draw 3, or board impact on resolution |
| 4 | 4/4 with an effect, or 5/4 | Must impact the board immediately |
| 5+ | Game-ending if it resolves | Must win the game or come close |

**The "Dies to Doom Blade" Problem:** A 4-mana 4/4 that does nothing when it dies is rarely good enough. It needs to either generate value when it enters, be resilient to removal, or provide an effect that matters immediately.

---

## The Cantrip Principle

Card advantage is the currency of Magic. Evaluate every card for whether it generates card advantage:
- **Card neutral:** Draws a card when it enters / dies / attacks (net zero, but keeps hand full)
- **Card positive:** Draws 2+ cards for its cost (2-for-1 or better)
- **Card negative:** Does nothing when answered, no replacement (the weakest category)

In constructed, try to run few "card negative" cards unless their effect is format-warping.

---

## The "Best Card" Test

For any given slot in your deck, ask: "Is this the best card I could run for this function?"
- If yes: include it
- If no: find what IS the best card and include that instead

Comps to know:
- **Removal:** Lightning Bolt (1R, 3 damage), Fatal Push (B, kills ≤2 CMC or ≤4 with revolt), Path to Exile (W, exile any creature), Swords to Plowshares (W, exile any creature)
- **Card draw:** Ancestral Recall (power, not realistic), Brainstorm (Legacy staple), Ponder/Preordain (Modern staples), Consider/Opt (lower power)
- **Counterspells:** Force of Will (Legacy), Counterspell (Modern), Arcane Denial (Commander), Mana Drain (Commander)

---

## Commander-Specific Evaluation

### The 100-Card Problem

In Commander, every card is a 1-of. This changes evaluation significantly:
- Consistency requires tutors or redundant effects
- Cards that are "fine" in 60-card formats may be too low-impact in Commander's longer games
- The bar for individual card quality is higher because you'll see any given card less often

### Power Level Tiers (Commander)

| Tier | Description | Examples |
|------|-------------|---------|
| 10 (cEDH) | Designed for competitive, fast wins. Tutor chains, infinite combos, fast mana. | Fast mana, tutors for 1, infinite combos |
| 7-9 (Optimized) | Strong cards, synergistic packages, efficient answers. Wins reliably. | Mana rocks, premium removal, powerful combos |
| 4-6 (Focused) | Synergistic theme, good card quality, occasional power spike. | Tribal packages, themed combos, moderate removal suite |
| 1-3 (Casual) | Theme-first, often janky, slow. Narrative/flavor focus. | "Flavor" tribal, suboptimal pet cards |

Match your deck's power level to your playgroup's expectations.

### The Rule of Threes (Commander card draw)

Your deck should reliably draw 2-3 extra cards per turn by the midgame, or you'll run out of cards. Ways to achieve this:
- Creatures with ETB draw (Mulldrifter, Reclamation Sage cycle)
- Engines (Rhystic Study, Mystic Remora, Phyrexian Arena)
- Spells with cantrip effects
- Synergy-based draw (e.g., Elf tribe with Elvish Visionary)

### Ramp Requirements (Commander)

Commander decks need enough ramp to not be mana-screwed in a 4-player game. General guidelines:
- **Low curve (avg CMC ≤ 2.5):** 8-10 ramp pieces
- **Mid curve (avg CMC 3-4):** 10-13 ramp pieces
- **High curve (avg CMC 4.5+):** 12-15 ramp pieces

Count: mana rocks (Sol Ring, Arcane Signet), land ramp (Cultivate, Rampant Growth), dorks (Llanowar Elves, Birds of Paradise)

---

## The "Does It Do Enough?" Filter

A quick pass filter before detailed evaluation:

**Automatic include:**
- Best in format at its function
- Generates card advantage AND is on-rate
- Enables the deck's core game plan

**Needs justification:**
- Slightly below rate but unique effect
- Situationally powerful but sometimes dead
- The 59th or 60th card in a 60-card deck

**Automatic cut:**
- Does something the deck can already do (redundancy without rate)
- Doesn't affect the board on resolution and is vulnerable to answers
- "Win-more" card (only good when already ahead)

---

## Common Mistakes to Avoid

- **The Jund Tax:** Packing every good card regardless of synergy. "Good stuff" beats coherent strategies, but only if the card quality is significantly higher.
- **Over-valuing flavor:** A card with great flavor that doesn't perform its mechanical role is always wrong.
- **Under-valuing consistency:** A slightly worse card you can run 4 of is often better than a powerful card you can run 1 of (in 60-card formats).
- **Forgetting the sideboard role:** In 60-card formats, some main deck slots can be flex spots that become specific hate in game 2. Factor this in.
