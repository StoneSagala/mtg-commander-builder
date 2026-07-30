# Skill: /meta-check

## What This Skill Does

Evaluates how a deck positions in the current competitive meta for its format. Identifies predator archetypes, meta opportunities, and whether the deck's strategy competes at the target power level.

**Use when:** The player asks about meta positioning, tournament viability, or how their deck fares against the current field.

**Don't use for:** Casual Commander decks with no competitive intent. Meta analysis is for competitive and cEDH contexts where the deck is built to win, not just to have fun.

---

## Process

### Step 1: Get the Current Meta Snapshot

Use Web Search MCP to get a fresh picture — never rely on cached knowledge:
```
Search: "[Format] meta [current month year]"
Search: "top [Format] decks MTGGoldfish [current month year]"
Search: "cEDH tier list [current year]"   ← for Commander
```

Summarize the top 3–5 archetypes and what they're doing. Note meta speed (what turn games are closing on average).

### Step 2: Map the Deck Against the Meta

For each top-tier archetype, evaluate:
- **Favorable:** Does this deck win this matchup? Why?
- **Unfavorable:** Does this deck lose? What's the structural reason?
- **Neutral:** Skill matchup — either player can win based on lines played.

| Matchup | Verdict | Key Reason |
|---------|---------|------------|
| [Archetype] | Favorable / Unfavorable / Neutral | [Race condition, hate piece, structural edge] |

### Step 3: Identify Predators and Prey

**Predators:** Decks that specifically invalidate this strategy — hate pieces that turn off the engine, faster race conditions, or answers that shut down the combo.

**Prey:** Archetypes this deck beats structurally — where the game plan has an inherent advantage.

### Step 4: Recommend Adjustments

If the analysis reveals significant weaknesses:
- **Sideboard changes** (60-card formats) → `optimization/docs/sideboard-guide.md`
- **Main deck flex slots** — 3–5 slots that could be meta-specific interaction
- **Commander swap** (cEDH) — if the strategy is right but the commander choice is wrong for the meta

---

## Output Format

```
## Meta Snapshot — [Format] ([Month Year])

Top archetypes: [A], [B], [C]
Meta speed: Turn [X] average close

## [Deck Name] Positioning

| Matchup | Verdict | Key Reason |
|---------|---------|------------|
| [A] | Favorable | [Why] |
| [B] | Unfavorable | [Why] |
| [C] | Neutral | [Why] |

Predators: [archetypes that beat this structurally]
Prey: [archetypes this beats structurally]

## Recommended Adjustments
[Specific sideboard or flex slot changes based on the meta]
```

---

## What NOT to Do

- **Don't run this on casual Commander** — meta positioning questions only matter when the deck is trying to compete
- **Don't use stale data** — always run fresh web searches; the meta shifts on a monthly cadence
- **Don't recommend a full rebuild** — meta-check informs the sideboard and 3–5 flex slots, not the deck's identity
