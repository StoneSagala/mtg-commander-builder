# Format reference contract

Current Commander facts come from the official Wizards sources and live Scryfall
card records. Refresh before building or validating:

```bash
python3 _system/refresh-data.py
```

- [Current bracket guidance](../../Ideation/docs/brackets.md)
- [Current Game Changers](game-changers.md)
- [Current named bans and special categories](banned-cards.md)
- [Freshness policy](../../_system/data-policy.json)
- [Wizards Commander format](https://magic.wizards.com/en/formats/commander)
- [Wizards banned/restricted lists](https://magic.wizards.com/en/banned-restricted-list)

These generated references expire after 24 hours. Check timestamps; old snapshots
and historical decklists cannot certify current legality. Tools refresh required
facts and stop on failed refreshes or unreviewed rule changes.

Commander decks contain 100 cards including the commander(s). Two permitted
commanders occupy two slots; their combined color identity governs the other 98.
Singleton rules have card-text exceptions, so unusual duplicate allowances need
review. Check exact current card text, identity and legalities through Scryfall.

Use `validate-deck.py` for automated Commander screening. Its bracket/strategy
warnings are not a full rules certification. Budget is the builder's optional
total-deck constraint and does not determine bracket. After swaps, rerun validation
and combo checking, then get player review before finalizing.

For other formats, use current Wizards format guidance and live Scryfall
legalities rather than stored rotation-window or ban-list assumptions. Legacy
optimization support for non-Commander formats needs its own format-specific
review before a final legality claim.
