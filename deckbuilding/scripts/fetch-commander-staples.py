#!/usr/bin/env python3
"""
fetch-commander-staples.py — Fetch EDHREC's recommended cards for a commander.

Pulls the commander's EDHREC page and extracts pre-categorized card recommendations
(ramp, card draw, removal, board wipes, protection, lands, high-synergy cards, etc.).
The AI uses this pre-populated pool to reason about cuts — not to search from scratch.

Usage:
    python deckbuilding/scripts/fetch-commander-staples.py "Meren of Clan Nel Toth"
    python deckbuilding/scripts/fetch-commander-staples.py "meren-of-clan-nel-toth" --category ramp
    python deckbuilding/scripts/fetch-commander-staples.py "Atraxa" --top 20
    python deckbuilding/scripts/fetch-commander-staples.py "Teysa Karlov" --format json
"""

import sys
import json
import re
import time
import argparse
import urllib.request
import urllib.parse
import urllib.error

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')


from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "_shared"))
from data_sources import commander_pool, slugify


def fetch_staples(commander, category_filter=None, top_n=15):
    categorized, _, _ = commander_pool(commander, warn=lambda m: print(m, file=sys.stderr))
    return {category: sorted(cards, key=lambda c: (-c['synergy_score'], -c['inclusion_rate']))[:top_n]
            for category, cards in categorized.items()
            if not category_filter or category.lower() == category_filter.lower()}


def format_price(price):
    if price is None:
        return "?"
    try:
        return f"${float(price):.2f}"
    except (ValueError, TypeError):
        return "?"


def format_inclusion(rate):
    if not rate:
        return ""
    try:
        return f"{int(rate)}%"
    except (ValueError, TypeError):
        return ""


def print_staples(commander_slug, categorized, top_n, budget=None):
    total = sum(len(v) for v in categorized.values())
    print(f"\n{'='*60}")
    print(f"  Verified Card Pool: {commander_slug}")
    print(f"  {len(categorized)} categories  |  {total} cards")
    if budget is not None:
        print(f"  Budget filter: ${budget:.2f} — cards over budget marked ⚠")
    print(f"{'='*60}")

    for category, cards in categorized.items():
        print(f"\n  [{category}] ({len(cards)} cards)")
        print(f"  {'Card':<35} {'In%':>4}  {'Synergy':>7}  {'Price':>7}")
        print(f"  {'-'*55}")
        for card in cards[:top_n]:
            inclusion = format_inclusion(card["inclusion_rate"])
            synergy = f"{card['synergy_score']:+.0%}" if card.get("synergy_score") else "  —"
            price = format_price(card["price_usd"])
            over_budget = ""
            if budget is not None and card.get("price_usd"):
                try:
                    if float(card["price_usd"]) > budget:
                        over_budget = " ⚠"
                except (ValueError, TypeError):
                    pass
            print(f"  {card['name']:<35} {inclusion:>4}  {synergy:>7}  {price:>7}{over_budget}")

    print(f"\n  Pass these to the AI as the card pool for each phase.")
    print(f"  Roles are heuristic; review strategy and fill missing slots with verified searches.")


def main():
    parser = argparse.ArgumentParser(
        description="Fetch EDHREC card recommendations for a commander, pre-sorted by category."
    )
    parser.add_argument("commander",
                        help="Commander name or EDHREC slug (e.g. 'Meren of Clan Nel Toth')")
    parser.add_argument("--category", metavar="NAME", default=None,
                        help="Filter to one category (e.g. 'ramp', 'card draw', 'removal')")
    parser.add_argument("--top", type=int, default=15,
                        help="Max cards per category (default: 15)")
    parser.add_argument("--budget", type=float, default=None, metavar="USD",
                        help="Mark cards over this price with ⚠ (e.g. --budget 10 flags cards over $10)")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args()

    # Accept either a name or a slug
    slug = slugify(args.commander) if " " in args.commander else args.commander

    try:
        print(f"Fetching card pool for '{slug}'...", file=sys.stderr)
        categorized = fetch_staples(args.commander, category_filter=args.category, top_n=args.top)

        if not categorized:
            print(f"No card categories found for '{slug}'.")
            print("The commander may use an unusual EDHREC page structure.")
            sys.exit(1)


        if args.format == "json":
            print(json.dumps(categorized, indent=2))
        else:
            print_staples(slug, categorized, args.top, budget=args.budget)

    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code}: {e.reason}", file=sys.stderr)
        sys.exit(1)
    except (ValueError, urllib.error.URLError, TimeoutError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
