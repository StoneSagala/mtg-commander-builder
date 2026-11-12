# Engine: Spellslinger

Generate value from casting instants and sorceries. The engine rewards high spell density with card draw, damage, tokens, or mana — turning each spell into 1.5+ spells worth of value.

---

## How Value Is Generated

**Spell payoffs** — Guttersnipe, Murmuring Mystic, Talrand Sky Summoner; each spell cast triggers a bonus effect.

**Draw payoffs** — Archmage Emeritus, Niv-Mizzet, Parun; spells that draw cards trigger additional effects.

**Storm** — the spell count matters; Grapeshot and Aetherflux Reservoir reward casting many spells in one turn.

**Reuse** — Snapcaster Mage, Underworld Breach, Past in Flames, Mystic Retrieval; reusing spells multiplies their value without spending additional cards.

---

## Core Card Types Required

- **Cheap spells** — CMC 1–2 instants and sorceries; the engine needs volume to trigger payoffs reliably
- **Cantrips** — Ponder, Preordain, Brainstorm, Gitaxian Probe; draw while triggering payoffs; maintain spell count without card disadvantage
- **Spell payoffs (3–5)** — cards that trigger on spell cast, ETB, or draw; need redundancy so one removal spell doesn't end the engine
- **Spell reuse** — Past in Flames, Underworld Breach; the difference between a good turn and a winning turn
- **Mana acceleration** — Birgi, God of Storytelling; Lotus Petal; Manamorphose; keep mana flowing during chained spells

---

## Key Cards

Birgi, God of Storytelling · Archmage Emeritus · Niv-Mizzet, Parun · Guttersnipe · Talrand, Sky Summoner · Murmuring Mystic · Past in Flames · Underworld Breach · Snapcaster Mage · Aetherflux Reservoir · Grapeshot · Bonus Round

---

## Storm Turn Anatomy

A storm turn (bracket 4+) looks like:
1. Cast cheap mana positive spells (rituals, Manamorphose) to generate excess mana
2. Cast cantrips to draw into more spells
3. Cast Underworld Breach / Past in Flames to reuse the graveyard
4. Storm count reaches threshold → Grapeshot or Aetherflux Reservoir closes

---

## Anti-Synergy — Avoid

- Permanent-heavy builds (creatures and enchantments don't trigger spell payoffs)
- Slow, expensive instants/sorceries (5+ CMC spells can't be chained efficiently)
- Rule of Law / Eidolon of the Great Revel (hate pieces shut off the engine entirely — must be answered immediately)

---

## Current bracket review

Use `Ideation/docs/brackets.md` and `deckbuilding/docs/game-changers.md`
from the repository root after the freshness check. Assess combo timing and table
expectations with the player; this strategy guide is not an official bracket rule.

---

## Common Pairings

- **Game Plans:** Combo (storm win), Burn (spell damage payoffs), Control (spells as both interaction and engine fuel)
- **Win Cons:** Life Depletion (Aetherflux Reservoir burn), Mill (Brain Freeze storm), Alternate Win Cons (Thassa's Oracle after self-mill)
