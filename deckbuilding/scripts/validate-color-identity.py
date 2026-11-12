#!/usr/bin/env python3
"""
validate-color-identity.py — Check every card in a decklist against the commander's color identity.

Fetches the commander's color identity from Scryfall (ground truth), then checks each card.
Flags any card whose color identity includes a color outside the commander's identity.

Run this during Phase 11 (Legality Checks) or any time after cards are added.

Usage:
    # Check a decklist file
    python deckbuilding/scripts/validate-color-identity.py --commander "Meren of Clan Nel Toth" --file deckbuilding/brews/meren-draft.md

    # Check a list of card names directly
    python deckbuilding/scripts/validate-color-identity.py --commander "Atraxa" --cards "Swords to Plowshares" "Counterspell" "Lightning Bolt"

    # Just print the commander's color identity
    python deckbuilding/scripts/validate-color-identity.py --commander "Teysa Karlov" --identity-only

    # Output as JSON
    python deckbuilding/scripts/validate-color-identity.py --commander "Meren" --file brew.md --format json
"""

import sys
import json
import time
import argparse
import urllib.request
import urllib.parse
import urllib.error

SCRYFALL_BASE = "https://api.scryfall.com"
USER_AGENT = "MTGCommanderBuilder/0.2 (https://github.com/StoneSagala/mtg-commander-builder)"

COLOR_NAMES = {
    "W": "White",
    "U": "Blue",
    "B": "Black",
    "R": "Red",
    "G": "Green",
}

# Cards that are always legal regardless of color identity
ALWAYS_LEGAL = {
    # Basic lands
    "Plains", "Island", "Swamp", "Mountain", "Forest",
    "Wastes",
    # Snow basics
    "Snow-Covered Plains", "Snow-Covered Island", "Snow-Covered Swamp",
    "Snow-Covered Mountain", "Snow-Covered Forest",
}


def scryfall_get(url):
    time.sleep(0.1)
    req = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_card(name):
    """Fetch a card from Scryfall by fuzzy name match."""
    encoded = urllib.parse.urlencode({"fuzzy": name}, quote_via=urllib.parse.quote)
    url = f"{SCRYFALL_BASE}/cards/named?{encoded}"
    try:
        return scryfall_get(url)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return {"error": f"Not found: {name}"}
        raise


def get_commander_identity(commander_name):
    """
    Fetch the commander's color identity from Scryfall.
    Returns (color_identity: list[str], card_data: dict)
    """
    card = fetch_card(commander_name)
    if "error" in card:
        raise ValueError(
            f"Commander '{commander_name}' not found on Scryfall.\n"
            f"  Check spelling or try the exact card name."
        )

    # Verify it can be a commander
    type_line = card.get("type_line", "")
    legalities = card.get("legalities", {})
    if legalities.get("commander") == "banned":
        raise ValueError(f"'{card['name']}' is banned in Commander.")

    return card.get("color_identity", []), card


def parse_decklist(filepath):
    """Parse a decklist file, return list of (quantity, card_name) tuples."""
    cards = []
    with open(filepath, "r", encoding="utf-8") as f:
        in_decklist = False
        for line in f:
            line = line.strip()
            if not line:
                continue
            # Skip markdown headers and comments
            if line.startswith("##") or line.startswith("//"):
                in_decklist = True
                continue
            if line.startswith("#"):
                continue
            # Skip "Commander:" label line
            if line.lower().startswith("commander:"):
                continue

            parts = line.split(None, 1)
            if len(parts) == 2:
                qty_str = parts[0].rstrip("x")
                if qty_str.isdigit():
                    cards.append((int(qty_str), parts[1].strip()))
                    continue
            # Single token that's not a number — treat as card name
            if len(parts) == 1 and not parts[0][0].isdigit():
                cards.append((1, parts[0]))
    return cards


def check_cards(card_names, commander_identity):
    """
    Check a list of card names against the commander's color identity.
    Returns (legal: list, violations: list, not_found: list, skipped: list)
    """
    commander_set = set(commander_identity)
    legal = []
    violations = []
    not_found = []
    skipped = []

    total = len(card_names)
    for i, name in enumerate(card_names, 1):
        print(f"  Checking {i}/{total}: {name[:45]:<45}", end="\r", flush=True)

        # Always-legal cards skip the API call
        if name in ALWAYS_LEGAL:
            skipped.append(name)
            continue

        card = fetch_card(name)

        if "error" in card:
            not_found.append(name)
            continue

        card_identity = set(card.get("color_identity", []))
        illegal_colors = card_identity - commander_set

        if illegal_colors:
            violations.append({
                "name": card["name"],
                "card_identity": list(card_identity),
                "illegal_colors": list(illegal_colors),
                "type": card.get("type_line", ""),
                "legality": card.get("legalities", {}).get("commander", "unknown"),
            })
        else:
            legal.append(card["name"])

    print(" " * 70, end="\r")
    return legal, violations, not_found, skipped


def color_identity_string(colors):
    if not colors:
        return "Colorless"
    return "/".join(COLOR_NAMES.get(c, c) for c in sorted(colors))


def print_results(commander_name, commander_identity, legal, violations, not_found, skipped):
    identity_str = color_identity_string(commander_identity)
    total_checked = len(legal) + len(violations) + len(not_found)

    print(f"\n{'='*60}")
    print(f"  Color Identity Validation")
    print(f"  Commander: {commander_name}")
    print(f"  Identity:  {identity_str} ({', '.join(commander_identity) or 'Colorless'})")
    print(f"{'='*60}")
    print(f"\n  Checked: {total_checked} cards")
    print(f"  Legal:   {len(legal)}")
    print(f"  Skipped (always legal): {len(skipped)}")

    if violations:
        print(f"\n  ⛔ COLOR IDENTITY VIOLATIONS ({len(violations)} cards):")
        print(f"  These cards cannot be in a {identity_str} deck.\n")
        for v in violations:
            illegal_str = "/".join(COLOR_NAMES.get(c, c) for c in v["illegal_colors"])
            card_str = color_identity_string(v["card_identity"])
            print(f"  ✗ {v['name']}")
            print(f"      Card identity: {card_str}  |  Illegal colors: {illegal_str}")
    else:
        print(f"\n  ✓ No color identity violations found.")

    if not_found:
        print(f"\n  ⚠ Cards not found on Scryfall ({len(not_found)}) — verify manually:")
        for name in not_found:
            print(f"    - {name}")


def main():
    parser = argparse.ArgumentParser(
        description="Validate decklist color identity against the commander."
    )
    parser.add_argument("--commander", required=True, metavar="NAME",
                        help="Commander card name (e.g. 'Meren of Clan Nel Toth')")
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--file", metavar="PATH",
                        help="Decklist file to validate")
    source.add_argument("--cards", nargs="+", metavar="CARD",
                        help="Card names to check")
    parser.add_argument("--identity-only", action="store_true",
                        help="Just print the commander's color identity and exit")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args()

    try:
        print(f"Fetching color identity for '{args.commander}'...")
        commander_identity, commander_card = get_commander_identity(args.commander)
        commander_name = commander_card["name"]

        if args.identity_only:
            identity_str = color_identity_string(commander_identity)
            if args.format == "json":
                print(json.dumps({
                    "commander": commander_name,
                    "color_identity": commander_identity,
                    "identity_string": identity_str,
                }, indent=2))
            else:
                print(f"\n  {commander_name}")
                print(f"  Color Identity: {identity_str} ({', '.join(commander_identity) or 'Colorless'})")
            return

        if not args.file and not args.cards:
            parser.error("Provide --file or --cards (or use --identity-only)")

        if args.file:
            print(f"Parsing decklist: {args.file}...")
            entries = parse_decklist(args.file)
            card_names = [name for _, name in entries]
            print(f"  Found {len(card_names)} cards. Checking against {color_identity_string(commander_identity)}...")
        else:
            card_names = args.cards
            print(f"Checking {len(card_names)} cards against {color_identity_string(commander_identity)}...")

        legal, violations, not_found, skipped = check_cards(card_names, commander_identity)

        if args.format == "json":
            print(json.dumps({
                "commander": commander_name,
                "color_identity": commander_identity,
                "violations": violations,
                "not_found": not_found,
                "legal_count": len(legal),
                "skipped_count": len(skipped),
            }, indent=2))
        else:
            print_results(commander_name, commander_identity, legal, violations, not_found, skipped)

        # Exit with error code if violations found — useful for CI-style checks
        if violations:
            sys.exit(1)

    except urllib.error.HTTPError as e:
        print(f"\nHTTP Error {e.code}: {e.reason}")
        sys.exit(1)
    except FileNotFoundError:
        print(f"\nFile not found: {args.file}")
        sys.exit(1)
    except ValueError as e:
        print(f"\nError: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
