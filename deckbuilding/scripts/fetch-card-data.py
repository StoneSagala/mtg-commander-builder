#!/usr/bin/env python3
"""
fetch-card-data.py — Fetch card data from the Scryfall API.

Usage:
  python fetch-card-data.py "Card Name"
  python fetch-card-data.py --query "t:creature c:g cmc<=3 f:commander"
  python fetch-card-data.py --file decklist.md
  python fetch-card-data.py "Lightning Bolt" --format json
"""

import sys
import json
import time
import argparse
import urllib.request
import urllib.parse
import urllib.error

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')


SCRYFALL_BASE = "https://api.scryfall.com"


def get(url):
    """Make a GET request to Scryfall. Respects their rate limit guideline."""
    time.sleep(0.1)  # Scryfall requests 50-100ms between calls
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_card_by_name(name):
    """Fetch a single card by exact name using Scryfall's named endpoint."""
    encoded = urllib.parse.urlencode({"exact": name}, quote_via=urllib.parse.quote)
    url = f"{SCRYFALL_BASE}/cards/named?{encoded}"
    try:
        return get(url)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            # Try fuzzy search
            encoded = urllib.parse.urlencode({"fuzzy": name}, quote_via=urllib.parse.quote)
            url = f"{SCRYFALL_BASE}/cards/named?{encoded}"
            try:
                return get(url)
            except urllib.error.HTTPError:
                return {"error": f"Card not found: {name}"}
        return {"error": f"HTTP {e.code} fetching {name}"}


def search_cards(query, max_results=20):
    """Search cards using Scryfall search syntax."""
    encoded = urllib.parse.urlencode({"q": query, "order": "edhrec"})
    url = f"{SCRYFALL_BASE}/cards/search?{encoded}"
    results = []
    try:
        while url and len(results) < max_results:
            data = get(url)
            results.extend(data.get("data", []))
            url = data.get("next_page") if len(results) < max_results else None
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return []
        raise
    return results[:max_results]


def parse_decklist(filepath):
    """Parse a decklist file and return a list of card names."""
    cards = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            # Skip blank lines, comments, and section headers
            if not line or line.startswith("#") or line.startswith("//"):
                continue
            # Match "4 Card Name" or "1x Card Name" patterns
            parts = line.split(None, 1)
            if len(parts) == 2 and (parts[0].isdigit() or parts[0].rstrip("x").isdigit()):
                cards.append(parts[1].strip())
            elif len(parts) == 1 and not parts[0][0].isdigit():
                cards.append(parts[0])
    return cards


def format_card_summary(card):
    """Return a human-readable summary of a card."""
    if "error" in card:
        return f"ERROR: {card['error']}"

    name = card.get("name", "Unknown")
    mana_cost = card.get("mana_cost", "(no cost)")
    cmc = card.get("cmc", 0)
    type_line = card.get("type_line", "")
    oracle_text = card.get("oracle_text", "")
    power = card.get("power", "")
    toughness = card.get("toughness", "")
    loyalty = card.get("loyalty", "")
    legalities = card.get("legalities", {})
    prices = card.get("prices", {})

    lines = [
        f"{'='*60}",
        f"  {name}  {mana_cost}  (CMC: {cmc})",
        f"  {type_line}",
    ]

    if power and toughness:
        lines.append(f"  {power}/{toughness}")
    if loyalty:
        lines.append(f"  Loyalty: {loyalty}")

    if oracle_text:
        lines.append(f"\n  {oracle_text}")

    # Legality summary (common formats only)
    key_formats = ["standard", "pioneer", "modern", "legacy", "commander", "pauper"]
    legal_in = [f for f in key_formats if legalities.get(f) == "legal"]
    banned_in = [f for f in key_formats if legalities.get(f) == "banned"]

    if legal_in:
        lines.append(f"\n  Legal in: {', '.join(legal_in)}")
    if banned_in:
        lines.append(f"  Banned in: {', '.join(banned_in)}")

    # Prices
    usd = prices.get("usd")
    usd_foil = prices.get("usd_foil")
    if usd:
        lines.append(f"  Price: ${usd} USD" + (f" (foil: ${usd_foil})" if usd_foil else ""))

    lines.append(f"{'='*60}")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Fetch MTG card data from Scryfall.")
    parser.add_argument("card_name", nargs="?", help="Card name to look up")
    parser.add_argument("--query", "-q", help="Scryfall search query")
    parser.add_argument("--file", "-f", help="Decklist file to look up all cards")
    parser.add_argument("--format", choices=["text", "json"], default="text",
                        help="Output format (default: text)")
    parser.add_argument("--max", type=int, default=20,
                        help="Maximum results for search queries (default: 20)")
    args = parser.parse_args()

    if args.query:
        # Search mode
        print(f"Searching: {args.query}\n")
        cards = search_cards(args.query, max_results=args.max)
        if not cards:
            print("No results found.")
            return
        print(f"Found {len(cards)} results:\n")
        if args.format == "json":
            print(json.dumps(cards, indent=2))
        else:
            for card in cards:
                print(format_card_summary(card))

    elif args.file:
        # Decklist mode
        card_names = parse_decklist(args.file)
        print(f"Looking up {len(card_names)} cards from {args.file}\n")
        results = []
        for name in card_names:
            card = fetch_card_by_name(name)
            results.append(card)
            if args.format == "text":
                print(format_card_summary(card))
        if args.format == "json":
            print(json.dumps(results, indent=2))

    elif args.card_name:
        # Single card mode
        card = fetch_card_by_name(args.card_name)
        if args.format == "json":
            print(json.dumps(card, indent=2))
        else:
            print(format_card_summary(card))

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
