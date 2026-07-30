# Zimone and Dina — Optimization Session — 2026-06-10

**Deck:** deckbuilding/brews/zimone-and-dina-draft.md
**Bracket:** 4 | **Budget:** proxy-friendly (~$1000 actual) | **Stage:** post-brew auto-optimization pass

## Diagnostics
- deck-health: lands 38 (intentionally above generic target — lands engine), ramp ✓, interaction ✓, win cons ✓, tutors ✓; card draw flagged at 4 dedicated sources
- goldfish (1000 games, before): keep 83.5%, screw 0.5%, color fails 158%, first ramp T3.6, stuck: Splendid Reclamation 23%, Ophiomancer-adjacent slots slow

## Changes Applied
| Out | In | Why |
|-----|----|----|
| Reliquary Tower | Zagoth Triome | Colorless → fetchable tri-color source; color fails were the top flag |
| Minamo, School at Water's Edge | Overgrown Tomb | Marginal untap utility → fetchable B/G source |
| Shifting Woodland | Breeding Pool | Marginal → fetchable U/G source |
| Kodama's Reach | Farseek | 3 CMC → 2 CMC; Farseek fetches shocks/triome (Island/Swamp types) |
| Splendid Reclamation | Trade Routes | Stuck in 23% of games; Trade Routes is cheap engine glue (bounce land / discard land to draw) |
| Ophiomancer | Teferi's Ageless Insight | Slow fodder → doubles every commander draw, guarantees drain trigger each turn |

## Results (1000 games, after)
- Keep 83.3%, screw 0.0%, flood 0.0%
- Color fails 158% → 138% (residual is simulator blind spot: Urborg + Yavimaya make all lands tap B/G)
- Draw sources 8 → 10; dead turns 0.40/game
- Threats online T1.8 avg

## Consciously Overridden Flags
- "Add 2-CMC mana rocks" — rejected; lands engine anti-synergy. Exploration/Azusa/Oracle of Mul Daya are the ramp; simulator can't model extra land drops.
- "38 lands high" — rejected; lands decks want 38+.
- "Retreat to Coralhelm stuck 31%" — expected; it's a combo piece held until the win turn.

## Validation
- validate-deck.py: ALL PASS (100 cards, singleton, identity, ban list, bracket 4 compliant, 5 game changers — no cap)
- Combo lines verified manually (Commander Spellbook API was down):
  - Retreat to Coralhelm + Sakura-Tribe Scout + any karoo (e.g. Simic Growth Chamber returning itself) = infinite landfall
  - Thespian's Stage copying Dark Depths (no counters) = Marit Lage

## Session 2 (same day, post-playtest feedback)

**Player feedback:** "Can't get out the lands I want easily" + "deck got going on turn 5, want it faster."

**Diagnosis:** Only 5 cards could find a specific nonbasic land; all green ramp/fetches are basic-type only. Speed: first ramp T3.8, engine pieces all 3–4 CMC.

### Changes Applied
| Out | In | Why |
|-----|----|----|
| Scryb Ranger | Elvish Reclaimer | Repeatable any-land tutor on a 1-drop — the core fix |
| Morbid Opportunist | Ulvenwald Hydra | Any-land fetch + body, GSZ target |
| An Offer You Can't Refuse | Tempt with Discovery | Any land direct to battlefield |
| Terramorphic Expanse | Tolaria West | Transmutes for any 0-MV card (Field, Chasm, Depths, Beacon, Sol Ring) |
| Tyvar, Jubilant Brawler | Burgeoning | T1 explosive — land drop on each opponent's turn |
| Teferi's Ageless Insight | Arboreal Grazer | T1 ramp body, later sac fodder |
| Snow-Covered Island | Ancient Tomb | Fast-mana land, adds a Field name |

### Results (1000 games)
- First ramp T3.8 → T3.0; ramp-timing flag cleared
- Mana by T5: 5.7 → 6.2; by T6: 6.4 → 7.2 (≈ full turn faster)
- Color fails 138% → 121%; dead turns 0.40 → 0.34; keep rate steady 83%
- Specific-land access: 5 tutors → 10 (Reclaimer repeatable)
- validate-deck: ALL PASS, $1163, 6 game changers (no cap at bracket 4)

### Watch List for Next Session
- Wayward Swordtooth stuck 31% (no own draw engine to feed it) — cut candidate
- Storm Cauldron stuck 29% — theme-protected, but monitor
- Primer updated to match (combo assembly, T1 priorities, quick reference)

## Next Steps
- Playtest the Glacial Chasm lock upkeep math (Crucible/Loam sustain it; Zimone and Dina lifegain offsets)
- If commander gets targeted heavily, consider adding Lightning Greaves or Sylvan Safekeeper
- Status: draft → ready for table testing; promote to review after first real games
