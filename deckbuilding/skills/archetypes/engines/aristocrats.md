# Engine: Aristocrats

Generate value from creatures dying. Sacrifice creatures deliberately to trigger death payoffs — life drain, card draw, tokens, or mana — then recur them to sacrifice again.

---

## How Value Is Generated

The engine runs in a loop:
1. **Produce creatures** — tokens, recursive creatures, or creatures that replace themselves
2. **Sacrifice outlet** — free or cheap sacrifice effect (Ashnod's Altar, Viscera Seer, Altar of Dementia)
3. **Death payoff** — trigger on creature death (Blood Artist, Zulaport Cutthroat, Mayhem Devil, Dictate of Erebos)
4. **Recursion** — return the sacrificed creature (Gravecrawler, Reassembling Skeleton, Tenacious Underdog, Young Wolf)

When all four are in play simultaneously, each loop cycle generates net value. With enough loops, the payoffs drain opponents to zero.

---

## Core Card Types Required

- **Free sacrifice outlet** — costed outlets slow the engine significantly; Ashnod's Altar, Viscera Seer, Altar of Dementia, Goblin Bombardment (1+ required, 2–3 preferred)
- **Death payoff** — at least 3 separate payoffs; single payoffs are too easy to remove
- **Recursive creatures** — creatures that come back for free or cheaply (Gravecrawler, Bloodsoaked Champion, Reassembling Skeleton)
- **Token generators** — provide sacrifice fodder; Bitterblossom, Ophiomancer, Dreadhorde Invasion

---

## Key Cards

Ashnod's Altar · Viscera Seer · Altar of Dementia · Blood Artist · Zulaport Cutthroat · Mayhem Devil · Grave Pact · Dictate of Erebos · Gravecrawler · Bitterblossom · Ophiomancer · Pitiless Plunderer · Bastion of Remembrance

---

## The Combo Ceiling

Aristocrats can function as pure value OR as a combo:
- **Value mode:** incremental drain over several turns; resilient, grindy
- **Combo mode:** Gravecrawler + Phyrexian Altar + Blood Artist = infinite drain; Nooze + Mikaeus the Unhallowed + sacrifice outlet = infinite loop

Review explicit infinite loops against the current official bracket guidance and the player's table expectations.

---

## Anti-Synergy — Avoid

- Cards that exile creatures on death rather than putting them in the graveyard (blocks Gravecrawler recursion)
- Graveyard exile effects in your own deck
- High-CMC creatures that don't advance the sacrifice loop

---

## Current bracket review

Use `Ideation/docs/brackets.md` and `deckbuilding/docs/game-changers.md`
from the repository root after the freshness check. Assess combo timing and table
expectations with the player; this strategy guide is not an official bracket rule.

---

## Common Pairings

- **Game Plans:** Combo (drain loops), Go Wide (tokens as sacrifice fodder), Control (Grave Pact clears opponent boards)
- **Win Cons:** Life Depletion (Blood Artist drains), Commander Damage (secondary via combat)
