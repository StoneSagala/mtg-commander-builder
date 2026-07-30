#!/usr/bin/env python3
"""
validate-combos.py — Validate proposed combos against Commander Spellbook.

Checks whether a set of cards forms a known combo, and if so returns:
- What the combo produces (infinite mana, infinite tokens, win the game, etc.)
- Prerequisites (what needs to be in play / in hand)
- Step-by-step execution
- Rules notes explaining edge cases and why the combo does or doesn't work

Use this BEFORE including a combo in a deck to catch broken/non-functional combos.

Usage:
    # Check if specific cards form a combo
    python deckbuilding/scripts/validate-combos.py --cards "Gravecrawler" "Phyrexian Altar" "Zulaport Cutthroat"

    # Check a single card — find all combos it appears in
    python deckbuilding/scripts/validate-combos.py --card "Thassa's Oracle"

    # Check all cards in a decklist for known combos
    python deckbuilding/scripts/validate-combos.py --file deckbuilding/brews/meren-draft.md

    # Output as JSON
    python deckbuilding/scripts/validate-combos.py --card "Isochron Scepter" --format json
"""

import sys
import json
import re
import time
import argparse
import urllib.request
import urllib.parse
import urllib.error
from itertools import combinations

SPELLBOOK_API = "https://backend.commanderspellbook.com"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


def api_get(path, params=None):
    """Make a GET request to Commander Spellbook API."""
    time.sleep(0.15)
    url = f"{SPELLBOOK_API}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def search_combos_by_card(card_name):
    """Find all combos containing a specific card."""
    data = api_get("/api/v1/variants/", {"q": f'card:"{card_name}"', "limit": 50})
    return data.get("results", [])


def search_combos_by_cards(card_names):
    """Find combos that use ALL of the specified cards."""
    # Build query: card:"Name1" card:"Name2" ...
    query = " ".join(f'card:"{name}"' for name in card_names)
    data = api_get("/api/v1/variants/", {"q": query, "limit": 20})
    return data.get("results", [])


def parse_decklist(filepath):
    """Parse a decklist markdown file and return card names."""
    cards = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("//"):
                continue
            if line.startswith("Commander:") or line.startswith("##"):
                continue
            parts = line.split(None, 1)
            if len(parts) == 2 and (parts[0].isdigit() or parts[0].rstrip("x").isdigit()):
                cards.append(parts[1].strip())
            elif len(parts) == 1 and not parts[0][0].isdigit():
                cards.append(parts[0])
    return cards


def extract_combo_details(variant):
    """
    Extract readable details from a Commander Spellbook variant object.
    """
    # Card uses
    uses = []
    for item in variant.get("uses", []):
        card = item.get("card", {})
        qty = item.get("quantity", 1)
        name = card.get("name", "")
        if name:
            uses.append({"name": name, "quantity": qty})

    # Requirements (permanents needed in play, conditions)
    requires = []
    for item in variant.get("requires", []):
        template = item.get("template", {})
        name = template.get("name", "")
        if name:
            requires.append(name)

    # What the combo produces
    produces = []
    for item in variant.get("produces", []):
        feature = item.get("feature", {})
        name = feature.get("name", "")
        if name:
            produces.append(name)

    # Execution steps
    description = variant.get("description", "")

    # Rules notes — critical for catching broken combos
    notes = variant.get("notes", "")

    # Spellbook identity
    combo_id = variant.get("id", "")
    status = variant.get("status", "")  # "S" = spoiler, "E" = errata/banned

    return {
        "id": combo_id,
        "status": status,
        "cards": uses,
        "prerequisites": requires,
        "produces": produces,
        "description": description,
        "notes": notes,
        "legal_commander": variant.get("legalCommander", True),
        "spoiler": variant.get("spoiler", False),
    }


def check_deck_for_combos(card_names, min_combo_size=2, max_combo_size=4):
    """
    Check a full decklist for known combos.
    Tests combinations of 2, 3, and 4 cards against Spellbook.
    Returns list of found combos.
    """
    found = []
    seen_ids = set()

    print(f"  Checking {len(card_names)} cards for combos (sizes {min_combo_size}-{max_combo_size})...")

    # First pass: check each card individually to find potential combo pieces
    candidate_cards = set()
    for i, card in enumerate(card_names):
        print(f"  Scanning card {i+1}/{len(card_names)}: {card[:40]:<40}", end="\r", flush=True)
        try:
            results = search_combos_by_card(card)
            if results:
                candidate_cards.add(card)
        except urllib.error.HTTPError:
            pass

    print(" " * 70, end="\r")
    print(f"  Found {len(candidate_cards)} potential combo pieces. Checking combinations...")

    # Second pass: check combinations of candidate cards
    candidates = list(candidate_cards)
    for size in range(min_combo_size, min(max_combo_size + 1, len(candidates) + 1)):
        for combo_cards in combinations(candidates, size):
            try:
                results = search_combos_by_cards(list(combo_cards))
                for variant in results:
                    combo = extract_combo_details(variant)
                    if combo["id"] not in seen_ids:
                        # Verify all combo cards are actually in the deck
                        combo_card_names = {c["name"].lower() for c in combo["cards"]}
                        deck_names = {n.lower() for n in card_names}
                        if combo_card_names.issubset(deck_names):
                            seen_ids.add(combo["id"])
                            found.append(combo)
            except urllib.error.HTTPError:
                pass

    return found


def print_combo(combo, index=None):
    prefix = f"Combo #{index}" if index else "Combo"

    # Status flags
    flags = []
    if not combo.get("legal_commander", True):
        flags.append("BANNED/ILLEGAL")
    if combo.get("spoiler"):
        flags.append("UNRELEASED CARD")
    flag_str = "  ⚠ " + " | ".join(flags) if flags else ""

    print(f"\n  {'='*55}")
    print(f"  {prefix}{flag_str}")
    print(f"  {'='*55}")

    # Cards required
    card_strs = []
    for c in combo["cards"]:
        qty = c["quantity"]
        card_strs.append(f"{c['name']}" + (f" (x{qty})" if qty > 1 else ""))
    print(f"  Cards:   {' + '.join(card_strs)}")

    # What it does
    if combo["produces"]:
        print(f"  Result:  {', '.join(combo['produces'])}")

    # Prerequisites
    if combo["prerequisites"]:
        print(f"  Needs:   {', '.join(combo['prerequisites'])}")

    # How to execute
    if combo["description"]:
        print(f"\n  How it works:")
        # Wrap long descriptions
        desc = combo["description"]
        for line in desc.split("\n"):
            print(f"    {line}")

    # Rules notes — the important part
    if combo["notes"]:
        print(f"\n  ⚠ Rules Notes:")
        for line in combo["notes"].split("\n"):
            if line.strip():
                print(f"    {line}")


def print_results(combos, source_desc):
    print(f"\n{'='*60}")
    print(f"  Commander Spellbook — Combo Validation")
    print(f"  Source: {source_desc}")
    print(f"{'='*60}")

    if not combos:
        print(f"\n  No known combos found.")
        print(f"  This doesn't guarantee cards don't combo — only that Spellbook")
        print(f"  doesn't have a registered entry for them.")
        return

    legal = [c for c in combos if c.get("legal_commander", True) and not c.get("spoiler")]
    illegal = [c for c in combos if not c.get("legal_commander", True)]
    spoilers = [c for c in combos if c.get("spoiler")]

    print(f"\n  Found {len(combos)} combo(s): {len(legal)} legal, {len(illegal)} banned/illegal, {len(spoilers)} unreleased")

    if illegal:
        print(f"\n  ⛔ BANNED / ILLEGAL COMBOS — remove these:")
        for i, combo in enumerate(illegal, 1):
            print_combo(combo, f"ILLEGAL #{i}")

    if legal:
        print(f"\n  ✓ Legal combos found:")
        for i, combo in enumerate(legal, 1):
            print_combo(combo, i)

    if spoilers:
        print(f"\n  ⚠ Combos with unreleased cards:")
        for i, combo in enumerate(spoilers, 1):
            print_combo(combo, f"SPOILER #{i}")


def main():
    parser = argparse.ArgumentParser(
        description="Validate combos against Commander Spellbook — checks rules legality and notes."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--cards", nargs="+", metavar="CARD",
                       help="2+ card names to check as a specific combo")
    group.add_argument("--card", metavar="CARD",
                       help="Single card name — find all combos it appears in")
    group.add_argument("--file", metavar="PATH",
                       help="Decklist file — find all combos in the list")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args()

    try:
        if args.cards:
            print(f"Checking combo: {' + '.join(args.cards)}...")
            results = search_combos_by_cards(args.cards)
            combos = [extract_combo_details(v) for v in results]
            source = " + ".join(args.cards)

        elif args.card:
            print(f"Finding all combos for: {args.card}...")
            results = search_combos_by_card(args.card)
            combos = [extract_combo_details(v) for v in results]
            source = args.card

        else:  # --file
            print(f"Parsing decklist: {args.file}...")
            card_names = parse_decklist(args.file)
            print(f"  Found {len(card_names)} cards.")
            combos = check_deck_for_combos(card_names)
            source = args.file

        if args.format == "json":
            print(json.dumps(combos, indent=2))
        else:
            print_results(combos, source)

    except urllib.error.HTTPError as e:
        print(f"\nHTTP Error {e.code}: {e.reason}")
        print("Commander Spellbook may be temporarily unavailable.")
        sys.exit(1)
    except FileNotFoundError:
        print(f"\nFile not found: {args.file}")
        sys.exit(1)
    except ValueError as e:
        print(f"\nError: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
