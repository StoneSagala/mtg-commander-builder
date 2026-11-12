# Commander workflow contract

One repeating unit: a Commander deck with an approved brief, an editable draft,
and a reviewed final list. Form: a three-stage pipeline with a deck record library.
Existing folder names stay stable; execution order is defined here.

## Inputs
- New deck: player request → `Ideation/CONTEXT.md`.
- Existing deck: pasted list, file or URL → `optimization/CONTEXT.md`.
- Shared reference: `_shared/voice.md`; provider contracts: `_shared/data-sources.md`.

## Process and human checks
1. Ideation creates `deckbuilding/brews/[slug]-draft.md` with the brief.
   Player approves commander, strategy, budget and constraints before building.
2. Deckbuilding writes `[slug]-generated.md` without replacing the brief.
   Review strategy, missing slots and provider provenance before making
   `[slug]-review.md`. Generated output is not a validated finished deck.
3. Optimization saves `optimization/sessions/[slug]-[YYYY-MM-DD].md` and checks
   mana, legality, budget and strategy. Player reviews before a final list is
   written to `deckbuilding/decklists/[slug]-final.md`.

## Outputs and state
The artifacts above show which stages exist. An existing legacy draft can contain
both a brief and decklist: read it before classifying its state. Filenames alone
cannot prove player approval or validation; record those decisions in the artifact.
New briefs start with `_templates/brew-brief.md`.

## Boundaries
- Rules, scripts and skills are reusable reference; brews and sessions are products.
- No frontend/backend code is present in this repository.
- Don't move or delete historical decks during maintenance.
- Required data: Scryfall commander identity and verified card records. EDHREC,
  public reference lists and combo databases improve evidence but may be unavailable.
- Automated text heuristics do not prove bracket compliance or a functional combo.
