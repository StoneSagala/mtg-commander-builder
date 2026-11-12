#!/usr/bin/env python3
"""
validate-decklist.py — Validate an MTG decklist for format legality and card counts.

Usage:
  python validate-decklist.py decklist.md standard
  python validate-decklist.py decklist.md commander
  python validate-decklist.py decklist.md modern --skip-legality

Checks:
  - Total card count (correct for format)
  - Individual card counts (4-of limit, 1-of for Commander)
  - Format legality via Scryfall API (optional, requires internet)
  - Commander color identity compliance (Commander only)
"""

import sys
import re
import json
import time
import argparse
import urllib.request
import urllib.parse
import urllib.error
from collections import Counter


SCRYFALL_BASE = "https://api.scryfall.com"

FORMAT_RULES = {
    "standard":  {"min_cards": 60, "max_per_card": 4, "sideboard_max": 15, "commander": False},
    "pioneer":   {"min_cards": 60, "max_per_card": 4, "sideboard_max": 15, "commander": False},
    "modern":    {"min_cards": 60, "max_per_card": 4, "sideboard_max": 15, "commander": False},
    "legacy":    {"min_cards": 60, "max_per_card": 4, "sideboard_max": 15, "commander": False},
    "vintage":   {"min_cards": 60, "max_per_card": 4, "sideboard_max": 15, "commander": False},
    "pauper":    {"min_cards": 60, "max_per_card": 4, "sideboard_max": 15, "commander": False},
    "commander": {"min_cards": 100, "max_per_card": 1, "sideboard_max": 0, "commander": True},
    "oathbreaker": {"min_cards": 60, "max_per_card": 1, "sideboard_max": 10, "commander": True},
    "draft":     {"min_cards": 40, "max_per_card": None, "sideboard_max": None, "commander": False},
    "sealed":    {"min_cards": 40, "max_per_card": None, "sideboard_max": None, "commander": False},
}

# Cards that can have more than 4 copies
UNLIMITED_CARDS = {
    "Plains", "Island", "Swamp", "Mountain", "Forest",
    "Wastes", "Snow-Covered Plains", "Snow-Covered Island",
    "Snow-Covered Swamp", "Snow-Covered Mountain", "Snow-Covered Forest",
    "Persistent Petitioners", "Rat Colony", "Shadowborn Apostle",
    "Seven Dwarves",  # max 7
    "Relentless Rats", "Dragon's Approach", "Slime Against Humanity",
}


def scryfall_get(url):
    """Make a GET request to Scryfall."""
    time.sleep(0.1)
    req = urllib.request.Request(url, headers={"User-Agent": "MTGDeckBuilder/1.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_card(name):
    """Fetch card legality data from Scryfall."""
    encoded = urllib.parse.urlencode({"exact": name})
    url = f"{SCRYFALL_BASE}/cards/named?{encoded}"
    try:
        return scryfall_get(url)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            # Try fuzzy
            encoded = urllib.parse.urlencode({"fuzzy": name})
            url = f"{SCRYFALL_BASE}/cards/named?{encoded}"
            try:
                return scryfall_get(url)
            except urllib.error.HTTPError:
                return None
        return None


def parse_decklist(filepath):
    """
    Parse a decklist file. Returns:
      main_deck: Counter of {card_name: count}
      sideboard: Counter of {card_name: count}
      commander: str or None
    """
    main_deck = Counter()
    sideboard = Counter()
    commander = None
    section = "main"

    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("## "):
                break
            if not line or line.startswith("//"):
                continue

            # Section headers
            line_lower = line.lower().rstrip(":")
            if line_lower in ("sideboard", "side"):
                section = "sideboard"
                continue
            elif line_lower in ("commander", "oathbreaker"):
                section = "commander"
                continue
            elif line_lower in ("main", "maindeck", "main deck", "deck"):
                section = "main"
                continue
            elif line.startswith("#"):
                continue

            if line.endswith(":"):
                section = "main"
                continue
            if line.startswith("##"):
                break

            # Parse "4 Card Name" or "4x Card Name" or "Card Name"
            match = re.match(r"^(\d+)[xX]?\s+(.+)$", line)
            if match:
                count = int(match.group(1))
                name = match.group(2).strip()
                # Strip set codes like "(MOM) 123" if present
                name = re.sub(r"\s*\([A-Z0-9]+\)\s*\d*$", "", name).strip()
            else:
                count = 1
                name = line

            if section == "commander":
                commander = name
            elif section == "sideboard":
                sideboard[name] += count
            else:
                main_deck[name] += count

    return main_deck, sideboard, commander


def validate(filepath, fmt, skip_legality=False):
    """Run all validation checks. Returns list of errors and warnings."""
    errors = []
    warnings = []

    if fmt not in FORMAT_RULES:
        errors.append(f"Unknown format: '{fmt}'. Valid formats: {', '.join(FORMAT_RULES.keys())}")
        return errors, warnings

    rules = FORMAT_RULES[fmt]
    main_deck, sideboard, commander = parse_decklist(filepath)

    total_main = sum(main_deck.values())
    total_side = sum(sideboard.values())
    total = total_main + total_side + (1 if commander else 0)

    # --- Card count validation ---
    if fmt == "commander":
        if total != 100:
            errors.append(f"Commander decks must be exactly 100 cards (including commander). Found: {total}")
        if not commander:
            errors.append("No commander detected. Add a 'Commander:' section to your decklist.")
    elif fmt == "oathbreaker":
        if total_main != 58:
            errors.append(f"Oathbreaker decks must be 60 cards total (58 main + oathbreaker + signature spell). Found main: {total_main}")
    elif rules["min_cards"]:
        if total_main < rules["min_cards"]:
            errors.append(f"{fmt.title()} requires at least {rules['min_cards']} main deck cards. Found: {total_main}")

    if rules["sideboard_max"] is not None and total_side > rules["sideboard_max"]:
        errors.append(f"Sideboard exceeds maximum of {rules['sideboard_max']} cards. Found: {total_side}")

    # --- Per-card count validation ---
    if rules["max_per_card"]:
        for card, count in main_deck.items():
            if card in UNLIMITED_CARDS:
                continue
            if count > rules["max_per_card"]:
                errors.append(
                    f"'{card}': {count} copies found, max allowed in {fmt} is {rules['max_per_card']}"
                )

    # --- Legality check via Scryfall ---
    if not skip_legality:
        print(f"\nChecking format legality for {len(main_deck)} unique cards via Scryfall...")
        all_cards = set(main_deck.keys()) | set(sideboard.keys())
        if commander:
            all_cards.add(commander)

        commander_color_identity = None
        if commander and rules["commander"]:
            card_data = fetch_card(commander)
            if card_data:
                commander_color_identity = set(card_data.get("color_identity", []))
                print(f"  Commander color identity: {'{' + '}{'.join(sorted(commander_color_identity)) + '}' if commander_color_identity else 'Colorless'}")
            else:
                errors.append(f"Could not verify commander '{commander}' via Scryfall.")

        for card_name in sorted(all_cards):
            card_data = fetch_card(card_name)
            if card_data is None:
                errors.append(f"'{card_name}': Card not found on Scryfall. Check spelling.")
                continue

            legality = card_data.get("legalities", {}).get(fmt, "unknown")
            if legality == "banned":
                errors.append(f"'{card_name}': BANNED in {fmt}")
            elif legality == "restricted":
                if main_deck.get(card_name, 0) + sideboard.get(card_name, 0) > 1:
                    errors.append(f"'{card_name}': RESTRICTED in {fmt} (max 1 copy)")
                else:
                    warnings.append(f"'{card_name}': Restricted in {fmt} (1-of limit — you have 1, OK)")
            elif legality != "legal":
                errors.append(f"'{card_name}': Not legal in {fmt} (status: {legality})")

            # Commander color identity check
            if rules["commander"] and commander_color_identity is not None:
                card_identity = set(card_data.get("color_identity", []))
                if not card_identity.issubset(commander_color_identity):
                    illegal_colors = card_identity - commander_color_identity
                    errors.append(
                        f"'{card_name}': Color identity {{{'/'.join(sorted(card_identity))}}} "
                        f"outside commander's identity {{{'/'.join(sorted(commander_color_identity))}}} "
                        f"(illegal colors: {{{'/'.join(sorted(illegal_colors))}}})"
                    )

    return errors, warnings


def main():
    parser = argparse.ArgumentParser(description="Validate an MTG decklist.")
    parser.add_argument("decklist", help="Path to the decklist file")
    parser.add_argument("format", nargs="?", default="commander",
                        help="Format to validate against (default: commander)")
    parser.add_argument("--skip-legality", action="store_true",
                        help="Skip Scryfall legality check (faster, offline)")
    args = parser.parse_args()

    fmt = args.format.lower()
    print(f"Validating: {args.decklist}")
    print(f"Format:     {fmt}")
    print(f"Legality check: {'skipped' if args.skip_legality else 'enabled (requires internet)'}")

    try:
        errors, warnings = validate(args.decklist, fmt, skip_legality=args.skip_legality)
    except FileNotFoundError:
        print(f"\nERROR: File not found: {args.decklist}")
        sys.exit(1)

    print()
    if warnings:
        print(f"WARNINGS ({len(warnings)}):")
        for w in warnings:
            print(f"  ⚠  {w}")
        print()

    if errors:
        print(f"ERRORS ({len(errors)}):")
        for e in errors:
            print(f"  ✗  {e}")
        print(f"\n✗ Validation FAILED — {len(errors)} error(s) found.")
        sys.exit(1)
    else:
        print("✓ Validation PASSED — no errors found.")


if __name__ == "__main__":
    main()
