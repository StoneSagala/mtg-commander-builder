# Ideation Workspace

## Workflow contract
- **Inputs:** Player request; `skills/ideate.md`; `docs/playstyles.md` and `docs/brackets.md` only as needed. Shared provider handling: `../_shared/data-sources.md`.
- **Process:** Capture commander, verified color identity, strategy, bracket, constraints and total budget using `../_templates/brew-brief.md`.
- **Outputs:** `../deckbuilding/brews/[slug]-draft.md`, copied from the brief template.
- **Human check:** Player approves the written brief before deckbuilding. Cache misses are not proof of commander absence.


## What This Workspace Is

Where new Commander decks are born. A consultant-style intake conversation that helps a player discover what they want to build — their commander, playstyle, win condition, and power level. Output is a build brief that feeds directly into deckbuilding.

**This workspace is Commander-only.**

---

## What to Load

| Task                       | Load These                                                | Skip These           |
| -------------------------- | --------------------------------------------------------- | -------------------- |
| Run an ideation session    | `docs/playstyles.md`, `docs/brackets.md`, skill `/ideate` | Everything else      |
| Player unsure of bracket   | `docs/brackets.md`                                        | `docs/playstyles.md` |
| Player unsure of playstyle | `docs/playstyles.md`                                      | `docs/brackets.md`   |

---

## Folder Structure

```
Ideation/
├── CONTEXT.md          ← You are here
├── docs/
│   ├── playstyles.md   ← Playstyle descriptions in plain language
│   └── brackets.md     ← Commander bracket definitions (1–5)
├── skills/
│   └── ideate.md       ← Commander ideation intake conversation
└── scripts/
    ├── intake.py                ← Interactive intake questionnaire, outputs structured summary
    ├── discover-playstyle.py    ← Playstyle discovery questionnaire for undecided players (Flow D)
    ├── match-themes.py          ← Keyword-match free-text vibe to EDHREC theme slugs (Flow A)
    ├── filter-commanders.py     ← Fetch + filter commanders by bracket/budget via EDHREC + Scryfall
    ├── fetch-card-commanders.py ← Find commanders that play a given card (Flow C)
    ├── fetch-edhrec-data.py     ← Low-level EDHREC access: themes, colors, raw commander lists
    ├── fetch-top-commanders.py  ← Fetch/refresh top commanders popularity cache
    └── _cache/                  ← Auto-generated cache files (themes-cache.json, top-commanders-cache.json)
```

---

## The Three Flows

### Flow A — Playstyle/Theme First
User knows what they want to play but not which commander:
```
intake.py → match-themes.py --vibe "[text]"
          → filter-commanders.py --theme [slug] --color [slug] --bracket [n] --budget [x]
          → AI presents shortlist → conversation → player picks → confirm role + dependency
          → create brew starter file in deckbuilding/brews/
```

### Flow B — Commander First
User has a commander in mind but wants to explore how to build:
```
intake.py → fetch-edhrec-data.py --commander [slug] (themes)
          → filter-commanders.py confirms color identity + price via Scryfall
          → AI presents themes → conversation → confirm role + dependency
          → create brew starter file in deckbuilding/brews/
```

### Flow D — Undecided / Surprise Me
Player doesn't know what they want or wants a random pick:
```
discover-playstyle.py          ← 10-question personality quiz → outputs engine + game plan + win con profile
  OR
discover-playstyle.py --surprise-me  ← skip questionnaire, fully random profile
          → player pastes Playstyle Profile output into AI
          → AI treats it as a Flow A intake summary → match-themes.py → filter-commanders.py
          → conversation → player picks → confirm role + dependency
          → create brew starter file in deckbuilding/brews/
```

### Flow C — Win Condition / Combo First
User knows the card or combo they want to win with but needs a commander and shell:
```
intake.py → AI reasons through combo requirements + enabler categories
          → fetch-card-commanders.py "[key card]" --color [slug]
          → filter-commanders.py --bracket [n] --budget [x] on candidates
          → AI presents commanders with specific combo lines → player picks
          → confirm role + dependency → create brew starter file in deckbuilding/brews/
```

The `/ideate` skill detects which flow applies from the intake summary. All preference questions are collected by `intake.py` before any data is fetched. Scripts handle all mechanical fetching and filtering — AI only reasons about fit, tradeoffs, and playstyle.

---

## Data Sources

Scripts run in sequence — each one narrows what the AI sees before any reasoning happens.

| Script | Command | Returns |
|--------|---------|---------|
| `match-themes.py` | `--vibe "[text]"` | Top 5 EDHREC theme slugs matching the player's vibe |
| `filter-commanders.py` | `--theme [slug] --color [slug] --bracket [n] --budget [x]` | Filtered shortlist of up to 6 commanders with deck counts + prices |
| `fetch-card-commanders.py` | `"[card name]" --color [slug]` | Top commanders that play the card, ranked by deck count |
| `fetch-edhrec-data.py` | `--themes` / `--theme [slug]` / `--commander [slug]` | Raw EDHREC data — use when lower-level access is needed |
| `fetch-top-commanders.py` | `--refresh` / `--list` / `--check "[name]"` | Popularity cache — refresh periodically |

Scripts live in `Ideation/scripts/`. All data is fetched before the AI presents options — never fetch during reasoning.

---

## Output

When the player approves the brief, create a brew starter file at `deckbuilding/brews/[commander-slug]-draft.md` with the following header block, then hand off to `deckbuilding/CONTEXT.md` → `/brew-commander`.

```markdown
# [Commander Name] — Commander Deck

## Brief
- **Cmdr:** [Name] ([color identity]) — [role: Central / Important / Flexible]
- **Offline plan:** [what the deck does if commander is unavailable]
- **Partner / companion:** [if applicable, or N/A]
- **Theme:** [EDHREC theme slug]
- **Engine:** [enchantress / artifacts / graveyard / aristocrats / tribal / tokens / counters / spellslinger / lands / blink-etb / theft-chaos]
- **Game Plan:** [go-wide / go-tall / combo / burn / stax / control / politics]
- **Win Condition:** [life-depletion / commander-damage / mill / poison / alternate]
- **Alternate Win Con Card:** [card name, or N/A]
- **Interaction style:** [Reactive / Proactive / Balanced]
- **Success looks like:** [player's own words]
- **Bracket:** [1–5]
- **Constraints:** [budget, house rules, include list, exclude list]

## Decklist
<!-- /brew-commander builds from here -->
```

No brief file is saved in Ideation. The brew file is the record.

---

## Skills & Tools

| Skill / Tool                           | When to Use                                                |
| -------------------------------------- | ---------------------------------------------------------- |
| `scripts/intake.py`                    | **Run first.** Player runs this to collect all preferences; paste output to AI |
| `scripts/discover-playstyle.py`        | **Flow D.** For undecided players — 10-question quiz outputs engine/game-plan/win-con profile. `--surprise-me` skips the quiz entirely. |
| `skills/ideate.md`                     | Every session. Processes intake output, presents commanders, guides to brew file |
| `scripts/match-themes.py`              | Flow A — maps free-text vibe to EDHREC theme slugs before fetching anything |
| `scripts/filter-commanders.py`         | All flows — fetches + filters commanders by bracket and budget, enriches with Scryfall prices |
| `scripts/fetch-card-commanders.py`     | Flow C — given a key card, returns commanders that play it (reverse-engineer to commander) |
| `scripts/fetch-edhrec-data.py`         | Lower-level EDHREC access — themes list, color options, raw commander data |
| `scripts/fetch-top-commanders.py`      | Populate/refresh the top commanders popularity cache → writes to `scripts/_cache/` |

---

## What NOT to Do

- **Don't build a decklist here** — ideation ends when the brief is approved and the brew starter file is created
- **Don't skip creating the brew file** — verbal approval isn't enough; the file is what triggers the deckbuilding handoff

