# External data and recovery contract

## Inputs
Commander name, approved brief, and optionally a public deck URL. Python 3.9+ with standard-library HTTPS support. No browser installation is required.

## Provider responsibilities
| Provider | Contract | Failure behavior |
|---|---|---|
| Scryfall | `/cards/named`, `/cards/collection` (75 identifiers/request), `/cards/search` | Required for generated verified cards. If commander/identity cannot be resolved, stop with the actual error. Never assume colorless. |
| EDHREC | `https://json.edhrec.com/pages/{path}.json`, `container.json_dict.cardlists` | Optional pool. Missing, blocked, empty or schema-changing responses trigger labelled Scryfall fallback. |
| Archidekt | Search `/api/decks/v3/` (`name`, `deckFormat`); import `/api/decks/{id}/` | Optional reference. Name search is discovery, not proof that the commander matches; inspect the imported Commander section. |
| Moxfield | Search `api.moxfield.com/v2`; direct import `api2.moxfield.com/v3` | 403 means blocked access. Use Archidekt or a pasted/exported deck. Do not bypass access controls. |
| Commander Spellbook | `https://backend.commanderspellbook.com/variants/` | Optional combo evidence. Unavailability cannot support a claim of no combos or verified legality. |

EDHREC's public JSON feed is an observed integration, not a versioned API guarantee.
Scryfall API requirements: https://scryfall.com/docs/api
Spellbook backend: https://github.com/SpaceCowMedia/commander-spellbook-backend

## Process: fallback and script repair
1. Run `python3 _system/audit-connections.py --commander "Kotis, the Fangkeeper"`.
   Capture stdout to a dated JSON file in `_system/audits/`. Each provider is checked
   independently. Exit 0 means required providers passed; inspect optional statuses too.
2. Distinguish HTTP 404, 403, timeout, invalid JSON and a changed schema. Retry only
   transient statuses (429/5xx) in the shared client. Shared requests use a 20-second
   timeout, identifiable User-Agent and bounded retries.
3. Deck tools recover from EDHREC failures with a legal-color Scryfall pool and
   bounded targeted searches for the supplied engine, game plan and win condition.
   Discovery results have no invented synergy scores. They may leave slots empty;
   proposed win lines still require verification and player review.
4. Use `deckbuilding/skills/card-search.md` to fill strategy-specific gaps. Check
   names, identity, legality and prices with Scryfall. If the API is down, preserve
   the brief and record the blocker; do not generate guessed card data.
5. Fix shared EDHREC/card-pool behavior in `_shared/data_sources.py`. Legacy direct
   fetchers still have independent Scryfall helpers; the audit identifies those
   callers. Update affected callers and add a regression fixture/test for the
   actual response or exception before accepting a repair.
6. Run `python3 -m unittest discover -s tests -v`, then live probes, then the failing
   command with a new output path. Review the diff and draft before accepting it.

## Outputs / human check
- Machine-readable live evidence: `_system/audits/connections-YYYY-MM-DD.json`.
- Human-readable diagnosis and unresolved limits: a dated audit Markdown file.
- Generated drafts state provenance and unfilled slots. Verify strategy, bracket,
  total price and legality before promotion. Auto-recovery does not rewrite scripts;
  script repairs are reviewed code changes backed by regression tests.

## Current-data policy and review

`_system/data-policy.json` is the policy source. Rules, named bans, conditional ban
restrictions and Game Changers refresh from Wizards at least every 24 hours before
rules-dependent use. The generated Markdown views carry source and check times.
`_shared/current/commander.json` is the machine-readable source; do not hand-edit.
New official rule/conditional-ban wording changes the reviewed hash and blocks
rules-dependent tools until the source has been reviewed. List changes update
without inventing new rules. Failed refreshes never replace a last-good snapshot
or silently extend its expiry. See `_system/refresh-data.py --help`.

Theme and popularity caches expire after seven days and refresh on access. Prices,
legality and combos are fetched live each run. Historical audit and deck artifacts
are dated records, not current reference sources.

`.github/workflows/freshness.yml` runs daily at 10:15 UTC once the workflow is on
the GitHub default branch and Actions/PR creation are enabled. It refreshes data,
proposes a reviewable update PR and retains failure reports. Runtime freshness
checks protect local work independently of whether a scheduled PR is merged.

## Budget and supported workflows

A budget is an optional per-player, per-deck input, not a bracket rule. Omit
`--budget` for an unrestricted build. When supplied, it covers commander(s), all
basic-land copies and the rest of the deck, using live USD estimates. Unknown
mandatory prices or an impossible commander/mana-base cost block a bounded build.
Cheaper candidates replace expensive spells/utility lands; remaining slots are
explicit. Revalidate the total after manual swaps. Shipping, taxes and a chosen
collector printing require a separate purchasing estimate.

Single commanders, Partner, named Partner, Friends forever and Choose a Background
pairs are supported with combined identity and two occupied command-zone slots.
Other special pairings require explicit rules review. Role assignment and goldfish
simulation remain heuristics. Moxfield 403 responses use the Archidekt/pasted-list
path; no source change can grant access denied by the provider.

Combo checks use the documented Spellbook deck endpoint, preserve quantities and
command-zone cards, paginate with a request cap, and exit with an incomplete status
on provider/schema failure or truncation. Complete means the requested database
search completed, not that every possible Magic interaction has been proven.
