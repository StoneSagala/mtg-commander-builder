# Reliability followup — 2026-11-12

This supersedes the outstanding implementation items in the earlier
[incident audit](2026-11-12-audit.md). Historical evidence stays dated; active
references and scripts now use explicit freshness contracts.

## Builder-controlled budget

There is **no default spending cap**. `--budget` is optional and belongs to the
player's approved deck brief. If omitted, generation is unrestricted. If supplied,
it covers the whole deck: commander(s), utility lands, every basic-land copy and
spells. Spending does not determine bracket.

The generator fetches current USD estimates, replaces expensive utility lands
with basics as needed, omits unpriced discretionary cards, and fills affordable
alternatives from verified candidates. Unpriced mandatory cards or a commander/
mana base already above the player's limit stop a bounded build. Integer cents
avoid floating-point boundary errors. Gaps remain explicit; a partial draft is
not represented as a completed 100-card deck. Revalidate after manual changes.
Estimates do not include shipping, taxes, or a collector's chosen printing.

Live Kotis test: a **$100 supplied total**, **$94.15 estimated current draft**,
all prices resolved, **95 cards**. Independent validation passes its budget check
and fails card count as expected. Five remaining strategy slots require review.
The budget adjustment does not manufacture win conditions to reach 100.

## Current data and periodic updates

Canonical policy: [`../data-policy.json`](../data-policy.json).

| Data | Expiry / refresh | Failure behavior |
|---|---|---|
| Official rules, brackets, Game Changers, named bans and conditional ban rules | 24 hours; refresh before use, plus daily workflow | Required tools stop on expired/unavailable facts. Changed rule wording/hash needs source review. |
| Theme and popularity discovery snapshots | Seven days; refresh on access and daily workflow | Expired snapshots are not reused as current evidence. |
| Card identity, legality and prices | Live each generation/validation | Required missing data remains unknown or blocks the relevant claim. |
| Combos | Live each check, paginated with bounded requests | Incomplete queries cannot support a no-combo claim. |
| Historical brews, primers, audit records | Dated historical records | Not current reference data; revalidate before reuse. |

Current facts are fetched from [Wizards' Commander page](https://magic.wizards.com/en/formats/commander)
and [banned/restricted page](https://magic.wizards.com/en/banned-restricted-list).
The reviewed snapshot contains 53 Game Changers, 42 individually named bans,
special ban categories, and the distinction that Lutri is banned only as a companion.
Generated guides show their source and check time; old hand-maintained lists and
hardcoded validator fallbacks have been retired. Extra-turn and land-denial
screens now inspect live oracle text rather than old card-name sets.

Refreshes validate source shape before replacing the last-good JSON atomically.
A failed refresh cannot extend its expiry. Semantic rule changes require an exact
hash acceptance plus a review note; source-list changes are refreshed directly.
The fresh snapshot is still not a complete rules engine or bracket certification.

`.github/workflows/freshness.yml` runs daily at **10:15 UTC** when installed on the
GitHub default branch. It proposes updated reference data in a PR, retains refresh
reports, and fails visibly on retrieval/schema/review errors. This workflow is
added locally; it is **not active on GitHub until pushed** and Actions/PR creation
are enabled. Local generation/validation refresh guards already work without it.

## Other reliability repairs

- **Combo completeness:** use Spellbook's documented `/find-my-combos` POST,
  preserve quantities and command-zone cards, follow pagination, retain partial
  confirmed results and report `complete: false` on errors, loops or request caps.
  Exit 2 means incomplete. `/variants/` searches paginate as well. Current
  `legalities.commander` is used rather than a missing field defaulting to legal.
- **Strategy discovery:** bounded Scryfall searches include engine, game plan and
  win-condition terms within the verified combined color identity. Search results
  get no invented EDHREC synergy scores. Unsupported themes and proposed win lines
  still need player review.
- **Two commanders:** support Partner, named Partner, Friends forever and Choose
  a Background. Verify the pairing, combine identity, count both commander slots
  and both prices. Arbitrary two legends are rejected. Special pairings outside
  these patterns require explicit rules review.
- **Moxfield:** 403 remains a provider-side access restriction. The script now
  exposes provider statuses and fallback instructions, while Archidekt succeeds.
  Reference JSON includes `results` and `providers`; all-provider failure exits 2.
  Imported decks also refuse to overwrite existing artifacts unless `--force` is explicit.
- **Popularity:** replace Playwright/CSS scraping with EDHREC JSON. The available
  source provides 100 entries; larger requested counts fail explicitly. No browser
  package is required. Absence is not evidence of a new/nonexistent commander.
- **Shared ratios:** generator and ratio calculator import `_shared/ratios.py`.
  These are strategy heuristics; the ratio calculator still layers commander
  function detection over the same baseline.
- **Simulation:** correct London redraws to seven, give the multiplayer free
  mulligan, put bottomed cards at the bottom, preserve all cards, and add `--seed`.
  Seeded comparisons are reproducible. The simulator still uses a four-card keep
  floor and simplified mana/effects; it does not model opponents or full rules.
- **Active guides:** remove banned-card recommendations and replace duplicated
  bracket sections with current-reference links. Historical artifacts are retained.

## Verification

50 offline regression tests pass. All 33 Python files parse and 24 CLI help checks
pass. Live checks cover official refreshes, card lookup/batching/search, EDHREC,
Archidekt, Spellbook variants and deck POST. Both Moxfield operations remain 403.

Live examples:
- Kotis, $100 total: $94.15 estimate, no missing prices, 95 cards, correctly
  fails overall validation until the five missing slots are reviewed and filled.
- Tymna + Thrasios: unrestricted draft, B/G/U/W identity and two commander slots.
- Wilson + Raised by Giants: valid Background pair, green combined identity.
- Known Oracle/Consultation deck query: completes and returns the known line.
- Kotis goldfish: 50 games with seed 42; JSON is parseable and states heuristic scope.

Evidence files in this directory prefixed `followup-` contain these results.

## Remaining limits

Provider access cannot be granted by changing client code. Human strategy, combo
timing, table expectations and unusual commander/card-text exceptions remain
review work. Unknown prices cannot be guaranteed purchasable. Generated drafts
can be incomplete, and a budget is not a substitute for checking their final
100-card list. The daily GitHub job requires publication; no remote push or merge
has been performed in this session.
