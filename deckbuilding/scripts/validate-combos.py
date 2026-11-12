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
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "_shared"))
from combos import find_deck, find_cards, parse_deck

def search_combos_by_card(card_name):
    return search_combos_by_cards([card_name])


def search_combos_by_cards(card_names):
    report = find_cards(card_names)
    if not report['complete']:
        raise ValueError('Combo search incomplete: ' + '; '.join(report['errors']))
    return report['variants']


def parse_decklist(filepath):
    main, commanders = parse_deck(filepath)
    return main + commanders


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

    for field in ("easyPrerequisites", "notablePrerequisites"):
        if variant.get(field):
            requires.append(variant[field])

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
        "legal_commander": variant.get("legalities", {}).get("commander", variant.get("legalCommander", False)),
        "spoiler": variant.get("spoiler", False),
    }


def check_deck_for_combos(card_names, min_combo_size=2, max_combo_size=4):
    report = find_deck(card_names)
    if not report['complete']:
        raise ValueError('Combo check incomplete: ' + '; '.join(report['errors']))
    return [extract_combo_details(v) for v in report['variants']]


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
    parser.add_argument("--max-pages", type=int, default=10, help="Bound on requests; reaching it reports incomplete")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args()

    try:
        if args.max_pages < 1:
            parser.error('--max-pages must be positive')
        if args.file:
            main, commanders = parse_deck(args.file)
            report = find_deck(main, commanders, args.max_pages)
            source = args.file
        else:
            names = args.cards or [args.card]
            report = find_cards(names, args.max_pages)
            source = ' + '.join(names)
        combos = [extract_combo_details(v) for v in report.pop('variants')]
        report['combos'] = combos
        if args.format == 'json':
            print(json.dumps(report, indent=2))
        else:
            if not report['complete']:
                print('INCOMPLETE CHECK: ' + '; '.join(report['errors']))
                print(f'{len(combos)} confirmed database records retained; do not infer absence.')
                for index, combo in enumerate(combos, 1):
                    print_combo(combo, index)
            else:
                print_results(combos, source)
        sys.exit(0 if report['complete'] else 2)

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
