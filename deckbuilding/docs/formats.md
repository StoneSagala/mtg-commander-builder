# Format Rules & Ban Lists

## Commander / EDH

The primary format supported by this workspace.

### Core Rules

- **Deck size:** Exactly 100 cards (including the commander)
- **Singleton:** Only 1 copy of each card allowed (except basic lands and cards that say otherwise)
- **Commander zone:** Your commander starts in the command zone; can be cast from there at any time you could cast it normally
- **Returns to command zone:** On death or exile, the owner may return it to the command zone instead
- **Command tax:** Costs {2} more each time cast from the command zone after the first
- **Commander damage:** 21 combat damage from a single commander to a single player = that player loses
- **Color identity:** Your deck may only contain mana symbols appearing in your commander's color identity (casting cost + rules text + color indicator)
- **Starting life:** 40
- **Starting hand:** 7 cards

### Partner Commanders

Some commanders have "Partner" or "Partner with [Name]" — these allow a second commander from the command zone. The deck's color identity is the union of both commanders' identities.

### Background Commanders

Commanders with "Choose a Background" may have a Background enchantment as a second commander.

---

### Brackets (Power Level)

| Bracket | Description | Typical Features |
|---------|-------------|-----------------|
| 1 | Precon-level | No tutors, no infinite combos, basic mana fixing |
| 2 | Upgraded precon | Minor upgrades, no focused combos |
| 3 | Focused / optimized | Clear game plan, moderate tutors, some combos |
| 4 | High power | Strong synergies, reliable combos, optimized mana base |
| 5 | cEDH | Maximum competitive, fast combos, full tier-1 cards |

The RC bracket system is the official definition. Run `deckbuilding/scripts/validate-deck.py --bracket [n]` to check.

---

### Ban List

**Always verify against the current Commander RC ban list:** mtgcommander.net/rules/banned-list/

The list changes periodically. Run `deckbuilding/scripts/validate-deck.py` to check legality — the script pulls the live ban list rather than relying on a cached snapshot.

Common reasons cards get banned: too easy to win with (consistency collapses the game), too oppressive (locks other players out), or creates unfun game states at any power level.

---

### Special Rules

- **Split cards:** Both halves contribute to the card's color identity
- **Eminence:** Some commanders have abilities that trigger from the command zone without being in play
- **Mana abilities with generic cost:** {C} mana is colorless, not a color — allowed in any deck

---

## 60-Card Formats

| Format | Deck Size | Sideboard | Sets Legal | Notes |
|--------|-----------|-----------|-----------|-------|
| Standard | 60 min | 15 | Last ~2 years of sets | Rotates annually |
| Pioneer | 60 min | 15 | Return to Ravnica (2012)+ | No original fetchlands |
| Modern | 60 min | 15 | 8th Edition (2003)+ | Fast, combo-present |
| Pauper | 60 min | 15 | All sets | Commons only |
| Legacy | 60 min | 15 | All sets | Power-restricted list |
| Vintage | 60 min | 15 | All sets | Restricted list (1 copy allowed) |

For 60-card format ban lists, check the official Wizards DCI banned/restricted page or run `optimization/scripts/validate-decklist.py [format]`.
