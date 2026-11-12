"""Heuristic build ratios, not official format rules. Shared by both tools."""
BRACKET_BASELINES = {
    1: {
        "lands":        (37, 38),
        "ramp":         (10, 12),
        "card_draw":    (8, 10),
        "interaction":  (10, 12),
        "board_wipes":  (2, 3),
        "win_cons":     (5, 7),
        "tutors":       (0, 2),
        "note": "Slower games — prioritize resilience and redundancy over efficiency.",
    },
    2: {
        "lands":        (37, 38),
        "ramp":         (10, 12),
        "card_draw":    (8, 10),
        "interaction":  (10, 12),
        "board_wipes":  (2, 3),
        "win_cons":     (5, 7),
        "tutors":       (0, 2),
        "note": "Precon-level power. More redundancy, fewer tutors.",
    },
    3: {
        "lands":        (36, 38),
        "ramp":         (8, 12),
        "card_draw":    (8, 10),
        "interaction":  (8, 10),
        "board_wipes":  (2, 2),
        "win_cons":     (5, 7),
        "tutors":       (0, 4),
        "note": "Synergistic decks. Baseline ratios. Most common bracket.",
    },
    4: {
        "lands":        (32, 36),
        "ramp":         (8, 10),
        "card_draw":    (8, 10),
        "interaction":  (8, 12),
        "board_wipes":  (1, 2),
        "win_cons":     (2, 4),
        "tutors":       (4, 8),
        "note": "High power. Tutors replace redundancy. Fast mana prioritized.",
    },
    5: {
        "lands":        (28, 33),
        "ramp":         (5, 8),
        "card_draw":    (6, 8),
        "interaction":  (8, 12),
        "board_wipes":  (0, 1),
        "win_cons":     (1, 2),
        "tutors":       (8, 12),
        "note": "cEDH. Find 1 win line fast. Tutors replace redundancy. Speed > resilience.",
    },
}


# ---------------------------------------------------------------------------
# Strategy overrides — keyed to brief slugs
# ---------------------------------------------------------------------------

STRATEGY_OVERRIDES = {
    # Engine overrides
    "graveyard": {
        "note": "Graveyard decks can run slightly fewer lands (lands in yard = resources). "
                "Shuffle effects are anti-synergy.",
        "lands_adj": -1,
    },
    "lands": {
        "note": "Lands decks want more lands than baseline — lands ARE the engine.",
        "lands_adj": +4,
        "ramp_adj": -2,
    },
    "artifacts": {
        "note": "Prioritize mana rocks over land ramp. Artifact hate is a real threat.",
    },
    "enchantress": {
        "note": "Draw engine is built into the strategy. May reduce dedicated draw slots.",
        "card_draw_adj": -2,
    },
    "spellslinger": {
        "note": "Instants and sorceries generate value. Cantrips count toward draw.",
        "card_draw_adj": -1,
    },

    # Game plan overrides
    "combo": {
        "note": "Deterministic win lines. Fewer win cons, more tutors and protection.",
        "win_cons_adj": -2,
        "tutors_adj": +3,
    },
    "stax": {
        "note": "Taxing opponents replaces some interaction slots. Your board survives; "
                "theirs doesn't. Board wipes become less necessary.",
        "interaction_adj": +2,
        "board_wipes_adj": -1,
    },
    "control": {
        "note": "Win from inevitability. More interaction, fewer win cons needed.",
        "interaction_adj": +2,
        "win_cons_adj": -1,
    },
    "go-wide": {
        "note": "Board wipes are dangerous to your own board. Prefer asymmetrical sweepers.",
        "board_wipes_flag": "Prefer asymmetrical sweepers only — mass wipes hurt your board.",
    },
    "politics": {
        "note": "Political decks win through table dynamics. Interaction slots can be "
                "redirected to pillowfort and deal-making pieces.",
    },

    # Win condition overrides
    "commander-damage": {
        "note": "Commander IS the primary win con. Equipment and auras count as win con support. "
                "Protection becomes critical — commander dying = losing the win con.",
        "win_cons_adj": -2,
        "note_extra": "Count commander as 1 win con. Add equipment/auras/buffs to win con package.",
    },
    "alternate-win-cons": {
        "note": "Alternate win con card is the primary target. Tutors to find it are critical.",
        "win_cons_adj": -2,
        "tutors_adj": +2,
    },
    "poison": {
        "note": "10 poison is the threshold. Proliferate effects and infect creatures are "
                "the win con package. Less overlap with regular damage.",
    },
    "mill": {
        "note": "Mill requires enough density to actually empty libraries. 7+ mill effects minimum.",
    },
}


