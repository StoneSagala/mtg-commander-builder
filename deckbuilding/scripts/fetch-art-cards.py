#!/usr/bin/env python3
"""
fetch-art-cards.py — Find MTG cards by art content using Scryfall's illustration tags.

Scryfall tags card art with descriptive keywords (smile, dragon, fire, skeleton, etc.).
This script searches those tags to build an art-themed card pool for Commander decks
where the aesthetic or flavor — not mechanical synergy — drives card selection.

Use this for:
  - Art-themed decks (only smiling cards, only cards featuring butts, etc.)
  - Flavor-matched decks (Pinkie Pie deck = cards with parties/balloons/confetti)
  - IP-themed decks where you map source material to MTG art (Dungeon Crawler Carl, etc.)

The output replaces the EDHREC theme/synergy slot pool during Phase 5 review.
Structural slots (ramp, draw, interaction) still come from EDHREC — this fills
the theme slots only.

Usage:
    python deckbuilding/scripts/fetch-art-cards.py --art "smile"
    python deckbuilding/scripts/fetch-art-cards.py --art "smile balloon party" --color-identity WR
    python deckbuilding/scripts/fetch-art-cards.py --art "smile" --color-identity WR --budget 5
    python deckbuilding/scripts/fetch-art-cards.py --art "butt" --color-identity WUBRG --top 50
    python deckbuilding/scripts/fetch-art-cards.py --art "dungeon skeleton torch" --color-identity UB
    python deckbuilding/scripts/fetch-art-cards.py --art "smile" --color-identity WR --format json

Scryfall art tag examples:
    smile, laugh, cry, angry, skeleton, dragon, cat, dog, tree, fire, water,
    castle, city, sword, shield, crown, book, moon, sun, flower, mushroom,
    food, drink, hat, cloak, armor, wings, tentacle, eye, hand, skull, bone
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
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


def build_query(art_keywords, color_identity):
    """
    Build a Scryfall search query.

    art:keyword — cards whose illustration is tagged with this word
    id<=WUBRG  — color identity is a subset of the commander's (Commander legality)
    -type:basic — exclude basic lands (don't take theme slots)
    """
    parts = [f"art:{kw}" for kw in art_keywords]

    if color_identity:
        ci = "".join(color_identity).upper()
        parts.append(f"id<={ci}")

    parts.append("-type:basic")
    return " ".join(parts)


def fetch_page(url):
    """Fetch one page of Scryfall search results."""
    time.sleep(0.1)
    req = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None  # No results
        raise


def extract_card(card_obj):
    """Pull the fields we care about from a Scryfall card object."""
    price_str = card_obj.get("prices", {}).get("usd")
    # Handle double-faced cards — use front face type if available
    type_line = card_obj.get("type_line", "")
    if "card_faces" in card_obj and not type_line:
        type_line = card_obj["card_faces"][0].get("type_line", "")

    return {
        "name": card_obj["name"],
        "cmc": card_obj.get("cmc", 0),
        "type": type_line,
        "color_identity": card_obj.get("color_identity", []),
        "price_usd": price_str,
        "price": float(price_str) if price_str else None,
        "set": card_obj.get("set_name", ""),
        "is_legendary": "Legendary" in type_line,
    }


def search_art(art_keywords, color_identity, budget=None, max_cards=500):
    """
    Fetch all Scryfall cards matching the art keywords + color identity.
    Handles pagination automatically. Returns (cards, query_used).
    """
    query = build_query(art_keywords, color_identity)
    encoded = urllib.parse.urlencode(
        {"q": query, "order": "name", "unique": "cards"},
        quote_via=urllib.parse.quote,
    )
    url = f"{SCRYFALL_BASE}/cards/search?{encoded}"

    cards = []
    page_num = 0

    while url and len(cards) < max_cards:
        page_num += 1
        data = fetch_page(url)

        if data is None:
            break  # 404 = no results

        for card_obj in data.get("data", []):
            card = extract_card(card_obj)

            # Apply budget filter (keep cards with unknown prices)
            if budget is not None and card["price"] is not None and card["price"] > budget:
                continue

            cards.append(card)

        if data.get("has_more") and data.get("next_page"):
            url = data["next_page"]
        else:
            break

    return cards, query


def format_type(type_line):
    """Shorten type line for display."""
    # Drop everything after em dash (rules text marker in some type lines)
    type_line = type_line.split(" \u2014")[0].strip()
    # Shorten common supertypes
    type_line = type_line.replace("Legendary ", "Lgd. ")
    return type_line[:28]


def print_results(cards, query, art_keywords, color_identity, budget, top_n):
    ci_str = "".join(color_identity).upper() if color_identity else "WUBRG"
    budget_str = f"${budget:.2f}" if budget else "no limit"
    keyword_str = " + ".join(art_keywords)

    print(f"\n{'='*64}")
    print(f"  Art Search: {keyword_str}")
    print(f"  Color identity: {ci_str}   Budget: {budget_str}")
    print(f"  Query: {query}")
    print(f"{'='*64}")

    if not cards:
        print(f"\n  No cards found.")
        print(f"  Try fewer keywords, different keywords, or broader color identity.")
        print(f"\n  Common art tags: smile, laugh, skeleton, dragon, fire, castle,")
        print(f"  cat, sword, crown, food, hat, moon, sun, flower, skull, eye, book")
        return

    shown = cards[:top_n]
    legendary = [c for c in shown if c["is_legendary"]]

    print(f"\n  {len(cards)} cards found ({len(legendary)} legendary — potential commanders).")
    if len(cards) > top_n:
        print(f"  Showing top {top_n}. Use --top {top_n + 25} to see more.")

    print(f"\n  {'Card':<35} {'CMC':>3}  {'Type':<28}  {'Price':>7}")
    print(f"  {'-'*77}")

    for card in shown:
        price_str = f"${card['price']:.2f}" if card["price"] is not None else "unknown"
        lgd = "*" if card["is_legendary"] else " "
        type_str = format_type(card["type"])
        print(f"  {lgd}{card['name']:<34} {int(card['cmc']) if card['cmc'] == int(card['cmc']) else card['cmc']:>3}  {type_str:<28}  {price_str:>7}")

    if legendary:
        print(f"\n  * = Legendary (could serve as commander)")

    print(f"\n  Use these cards to fill theme/synergy slots during Phase 5 review.")
    print(f"  Structural slots (ramp, draw, interaction) still come from EDHREC.")
    print(f"\n  To use in generate-starter-deck.py:")
    print(f"    --art-theme \"{' '.join(art_keywords)}\"")


def main():
    parser = argparse.ArgumentParser(
        description="Find MTG cards by art content for flavor/art-themed Commander decks."
    )
    parser.add_argument(
        "--art", required=True, metavar="KEYWORDS",
        help="Space-separated art keywords (e.g. 'smile balloon party'). All keywords are ANDed.",
    )
    parser.add_argument(
        "--color-identity", metavar="WUBRG", default=None,
        help="Commander's color identity (e.g. WR, UB, WUBRG). Filters to legally playable cards.",
    )
    parser.add_argument(
        "--budget", type=float, default=None,
        help="Max card price in USD. Cards over this price are excluded.",
    )
    parser.add_argument(
        "--top", type=int, default=40, metavar="N",
        help="Max cards to display (default: 40). Use 0 for all.",
    )
    parser.add_argument(
        "--format", choices=["text", "json"], default="text",
        help="Output format (default: text)",
    )
    args = parser.parse_args()

    art_keywords = args.art.strip().split()
    color_identity = list(args.color_identity.upper()) if args.color_identity else []

    print(f"Searching Scryfall for art:{' art:'.join(art_keywords)}" +
          (f" within {args.color_identity.upper()}" if color_identity else "") + "...")

    cards, query = search_art(art_keywords, color_identity, budget=args.budget)

    top_n = len(cards) if args.top == 0 else args.top

    if args.format == "json":
        print(json.dumps({
            "query": query,
            "art_keywords": art_keywords,
            "color_identity": color_identity,
            "budget": args.budget,
            "total_found": len(cards),
            "cards": cards[:top_n],
        }, indent=2))
    else:
        print_results(cards, query, art_keywords, color_identity, args.budget, top_n)


if __name__ == "__main__":
    main()
