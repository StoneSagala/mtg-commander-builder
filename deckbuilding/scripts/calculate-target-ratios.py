#!/usr/bin/env python3
"""
calculate-target-ratios.py — Dynamic Phase 4 target calculator.

Fetches commander oracle text from Scryfall, detects which deck functions
the commander already provides, applies bracket baseline, strategy overrides,
and outputs adjusted build targets.

Usage:
    python deckbuilding/scripts/calculate-target-ratios.py \
        --commander "Toxrill, the Corrosive" \
        --bracket 3 \
        --engine aristocrats \
        --game-plan control \
        --win-con life-depletion

    python deckbuilding/scripts/calculate-target-ratios.py \
        --commander "Rograkh, Son of Rohgahh" \
        --partner "Kediss, Emberclaw Familiar" \
        --bracket 3 \
        --engine artifacts \
        --game-plan go-tall \
        --win-con commander-damage
"""

import argparse
import io
import re
import sys
import urllib.parse
import urllib.request
import json

# Force UTF-8 output on Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


# ---------------------------------------------------------------------------
# Bracket baselines
# ---------------------------------------------------------------------------

from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "_shared"))
from ratios import BRACKET_BASELINES, STRATEGY_OVERRIDES


# ---------------------------------------------------------------------------
# Commander function detection via Scryfall oracle text
# ---------------------------------------------------------------------------

BOARD_CONTROL_PATTERNS = [
    r"destroy all",
    r"exile all",
    r"all creatures get -",
    r"each creature gets -",
    r"all creatures.*die",
    r"each player sacrifices",
    r"all creatures.*\-\d+/\-\d+",
    r"return all creatures",
    r"tap all",
]

CARD_DRAW_PATTERNS = [
    r"draw (?:a|two|three|\d+) card",
    r"draw that many card",
    r"draw cards equal",
    r"look at the top \d+ card",
    r"you may draw",
]

RAMP_PATTERNS = [
    r"add \{[wubrgcWUBRGC2]\}",
    r"add [one|two|three]* mana",
    r"search your library for (?:a |up to \d+ )?basic land",
    r"untap up to \d+ land",
    r"put.*land.*onto the battlefield",
    r"whenever.*add.*mana",
]

WIN_CON_PATTERNS = [
    r"you win the game",
    r"that player loses the game",
    r"players? (?:who|with) \d+ or (?:more|fewer) life",
]

PROTECTION_PATTERNS = [
    r"\bhexproof\b",
    r"\bshroud\b",
    r"\bindestructible\b",
    r"\bregenerate\b",
    r"protection from",
]


def detect_functions(oracle_text: str, mana_cost: str, cmc: float) -> dict:
    """
    Scan oracle text for commander-provided functions.
    Returns a dict of detected functions with confidence and reasoning.
    """
    text = oracle_text.lower()
    detected = {}

    def match_any(patterns):
        for p in patterns:
            if re.search(p, text):
                return True
        return False

    if match_any(BOARD_CONTROL_PATTERNS):
        detected["board_control"] = {
            "found": True,
            "confidence": "high",
            "note": "Commander text contains mass removal or creature wipe effect.",
        }
    else:
        # Flag for AI review if text mentions death, sacrifice, or -1/-1 counters at scale
        indirect_signals = [
            r"-1/-1 counter",
            r"whenever.*creature.*die",
            r"at the beginning of.*upkeep.*each",
            r"each opponent.*sacrifice",
        ]
        if match_any(indirect_signals):
            detected["board_control"] = {
                "found": "indirect",
                "confidence": "low",
                "note": "Commander may provide indirect board control — review manually.",
            }

    if match_any(CARD_DRAW_PATTERNS):
        detected["card_draw"] = {
            "found": True,
            "confidence": "high",
            "note": "Commander draws cards directly.",
        }

    if match_any(RAMP_PATTERNS):
        detected["ramp"] = {
            "found": True,
            "confidence": "high",
            "note": "Commander produces mana or fetches lands.",
        }

    if match_any(WIN_CON_PATTERNS):
        detected["win_con"] = {
            "found": True,
            "confidence": "high",
            "note": "Commander has a built-in 'you win the game' clause.",
        }

    if match_any(PROTECTION_PATTERNS):
        detected["protection"] = {
            "found": True,
            "confidence": "high",
            "note": "Commander has built-in protection.",
        }

    # Low CMC anchor
    if cmc <= 1:
        detected["low_curve_anchor"] = {
            "found": True,
            "confidence": "high",
            "note": f"Commander costs {int(cmc) if cmc == int(cmc) else cmc} mana — deck can run fewer lands.",
        }

    return detected


# ---------------------------------------------------------------------------
# Substitution table — how much each function reduces targets
# ---------------------------------------------------------------------------

SUBSTITUTIONS = {
    "board_control": {
        "board_wipes": -2,
        "note": "Commander provides ongoing board control → reduce board wipe slots by 1–2 (can reach 0).",
    },
    "board_control_indirect": {
        "board_wipes": -1,
        "note": "Commander provides indirect board control → reduce board wipes by 1 (keep at least 1).",
    },
    "card_draw": {
        "card_draw": -3,
        "note": "Commander draws cards → reduce dedicated draw slots by 2–3.",
    },
    "ramp": {
        "ramp": -2,
        "note": "Commander provides ramp → reduce ramp slots by 2–3.",
    },
    "win_con": {
        "win_cons": -1,
        "note": "Commander is a win condition → count commander, reduce other win con slots by 1.",
    },
    "protection": {
        "note": "Commander has built-in protection → reduce protection piece count by 1–2.",
    },
    "low_curve_anchor": {
        "lands": -4,
        "note": "Very low CMC commander → reduce land count by 3–5 from baseline.",
    },
}


# ---------------------------------------------------------------------------
# Scryfall fetch
# ---------------------------------------------------------------------------

def fetch_commander(name: str) -> dict:
    encoded = urllib.parse.quote(name)
    url = f"https://api.scryfall.com/cards/named?fuzzy={encoded}"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "MTGDeckBuilder/1.0", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"  ERROR fetching '{name}' from Scryfall: {e}", file=sys.stderr)
        return {}


def get_oracle_text(card: dict) -> str:
    """Handles double-faced cards."""
    if "oracle_text" in card:
        return card["oracle_text"]
    if "card_faces" in card:
        return " ".join(f.get("oracle_text", "") for f in card["card_faces"])
    return ""


def get_cmc(card: dict) -> float:
    return float(card.get("cmc", 3.0))


# ---------------------------------------------------------------------------
# Main calculation
# ---------------------------------------------------------------------------

def calculate_targets(
    commander_name: str,
    bracket: int,
    engine: str,
    game_plan: str,
    win_con: str,
    partner_name: str = "",
) -> None:
    print()
    print("=" * 60)
    print("  Phase 4: Adjusted Build Targets")
    print("=" * 60)

    # --- Fetch commander ---
    print(f"\nFetching: {commander_name}...")
    card = fetch_commander(commander_name)
    if not card:
        print("  Could not fetch commander data. Using bracket baseline only.")
        oracle_text = ""
        cmc = 3.0
        mana_cost = "?"
        color_identity = []
    else:
        oracle_text = get_oracle_text(card)
        cmc = get_cmc(card)
        mana_cost = card.get("mana_cost", card.get("card_faces", [{}])[0].get("mana_cost", "?"))
        color_identity = card.get("color_identity", [])
        print(f"  {commander_name} | {mana_cost} | CMC {cmc} | {'/'.join(color_identity) or 'Colorless'}")

    # Partner
    partner_oracle = ""
    if partner_name:
        print(f"Fetching partner: {partner_name}...")
        partner_card = fetch_commander(partner_name)
        if partner_card:
            partner_oracle = get_oracle_text(partner_card)
            partner_cmc = get_cmc(partner_card)
            combined_cmc = min(cmc, partner_cmc)  # use lower CMC for curve anchor check
            oracle_text = oracle_text + " " + partner_oracle
            cmc = (cmc + partner_cmc) / 2  # average for display, but use lower for anchor
            print(f"  {partner_name} | CMC {partner_cmc}")

    # --- Detect functions ---
    detected = detect_functions(oracle_text, mana_cost, cmc)

    # --- Start from bracket baseline ---
    baseline = BRACKET_BASELINES.get(bracket, BRACKET_BASELINES[3])
    targets = {
        "lands":       list(baseline["lands"]),
        "ramp":        list(baseline["ramp"]),
        "card_draw":   list(baseline["card_draw"]),
        "interaction": list(baseline["interaction"]),
        "board_wipes": list(baseline["board_wipes"]),
        "win_cons":    list(baseline["win_cons"]),
        "tutors":      list(baseline["tutors"]),
    }

    reasoning = []
    flags = []

    # --- Apply commander substitutions ---
    for func, info in detected.items():
        if info.get("found") is True and func in SUBSTITUTIONS:
            sub = SUBSTITUTIONS[func]
            for key, delta in sub.items():
                if key in targets and key != "note":
                    targets[key][0] = max(0, targets[key][0] + delta)
                    targets[key][1] = max(0, targets[key][1] + delta)
            reasoning.append(f"  [{func.upper()}] {sub.get('note', '').replace(chr(8594), '->')}")
        elif info["found"] == "indirect":
            if func == "board_control" and "board_control_indirect" in SUBSTITUTIONS:
                sub = SUBSTITUTIONS["board_control_indirect"]
                for key, delta in sub.items():
                    if key in targets and key != "note":
                        targets[key][0] = max(0, targets[key][0] + delta)
                        targets[key][1] = max(0, targets[key][1] + delta)
            flags.append(f"  ⚠ REVIEW: {info['note']}")

    # --- Apply strategy overrides ---
    for slug in [engine, game_plan, win_con]:
        override = STRATEGY_OVERRIDES.get(slug)
        if not override:
            continue
        for key, delta in override.items():
            if key.endswith("_adj") and key.replace("_adj", "") in targets:
                tgt_key = key.replace("_adj", "")
                targets[tgt_key][0] = max(0, targets[tgt_key][0] + delta)
                targets[tgt_key][1] = max(0, targets[tgt_key][1] + delta)
            elif key.endswith("_flag"):
                flags.append(f"  ⚠ {override[key]}")
        if "note" in override:
            note = override["note"].replace("\u2192", "->")
            reasoning.append(f"  [{slug.upper()}] {note}")

    # --- Avg CMC note ---
    cmc_note = ""
    if cmc > 4.0:
        cmc_note = f"Avg CMC {cmc:.1f} — consider +1–2 lands and +2 ramp above targets."
        flags.append(f"  ⚠ High CMC commander ({cmc:.1f}) — adjust lands/ramp upward if avg deck CMC > 3.5")
    elif cmc <= 1.0:
        cmc_note = f"Very low CMC commander — land reduction already applied."

    # --- Output ---
    print()
    print(f"Bracket {bracket}: {baseline['note']}")
    print()
    print("ADJUSTED TARGETS:")
    def rng(key):
        lo, hi = targets[key]
        return f"{lo}" if lo == hi else f"{lo}-{hi}"

    print(f"  Lands:       {rng('lands')}")
    print(f"  Ramp:        {rng('ramp')}")
    print(f"  Card draw:   {rng('card_draw')}")
    print(f"  Interaction: {rng('interaction')}")
    print(f"    Board wipes (included above): {rng('board_wipes')} minimum")
    print(f"  Win cons:    {rng('win_cons')}")
    print(f"  Tutors:      {rng('tutors')}")
    print(f"  Theme/synergy: remaining slots after above packages")

    if reasoning:
        print()
        print("ADJUSTMENTS APPLIED:")
        for r in reasoning:
            print(r)

    if flags:
        print()
        print("REVIEW FLAGS (require AI judgment):")
        for f in flags:
            print(f)

    # Commander function summary
    if detected:
        print()
        print("COMMANDER FUNCTION INVENTORY:")
        all_functions = [
            ("board_control", "Board control / sweeping"),
            ("card_draw",     "Card draw"),
            ("ramp",          "Ramp"),
            ("win_con",       "Win condition built-in"),
            ("protection",    "Protection"),
            ("low_curve_anchor", "Low CMC curve anchor"),
        ]
        for key, label in all_functions:
            info = detected.get(key)
            if info:
                status = "YES" if info["found"] is True else "INDIRECT (review)"
                print(f"  {label}: {status}")
                print(f"    → {info['note']}")
            else:
                print(f"  {label}: no")

    print()
    print("Pass this output to the AI as Phase 4 targets.")
    print("AI should override any line where commander judgment differs from pattern detection.")
    print()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Calculate adjusted Phase 4 build targets for a Commander deck."
    )
    parser.add_argument("--commander", required=True, help="Commander name")
    parser.add_argument("--partner", default="", help="Partner commander name (if applicable)")
    parser.add_argument("--bracket", type=int, required=True, choices=[1, 2, 3, 4, 5],
                        help="Deck bracket (1–5)")
    parser.add_argument("--engine", required=True,
                        help="Engine slug: enchantress, artifacts, graveyard, aristocrats, "
                             "tribal, tokens, counters, spellslinger, lands, blink-etb, theft-chaos")
    parser.add_argument("--game-plan", required=True, dest="game_plan",
                        help="Game plan slug: go-wide, go-tall, combo, burn, stax, control, politics")
    parser.add_argument("--win-con", required=True, dest="win_con",
                        help="Win con slug: life-depletion, commander-damage, mill, poison, alternate-win-cons")

    args = parser.parse_args()

    calculate_targets(
        commander_name=args.commander,
        bracket=args.bracket,
        engine=args.engine,
        game_plan=args.game_plan,
        win_con=args.win_con,
        partner_name=args.partner,
    )


if __name__ == "__main__":
    main()
