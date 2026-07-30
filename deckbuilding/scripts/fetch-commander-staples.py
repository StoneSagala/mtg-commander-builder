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

EDHREC_BASE = "https://edhrec.com"
SCRYFALL_BASE = "https://api.scryfall.com"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

# Map EDHREC cardlist tags to human-readable category names.
# EDHREC uses inconsistent tag names across commanders — this covers known variants.
CATEGORY_MAP = {
    # Ramp
    "ramp": "Ramp",
    "manaartifacts": "Ramp",
    "mana-artifacts": "Ramp",
    "manaartefacts": "Ramp",
    # Card Draw
    "carddraw": "Card Draw",
    "card-draw": "Card Draw",
    "draw": "Card Draw",
    "cardadvantage": "Card Draw",
    # Removal
    "removal": "Removal",
    "targetedremoval": "Removal",
    "targeted-removal": "Removal",
    "singleremoval": "Removal",
    # Board Wipes
    "boardwipes": "Board Wipes",
    "board-wipes": "Board Wipes",
    "massdestruction": "Board Wipes",
    "sweepers": "Board Wipes",
    # Protection
    "protection": "Protection",
    "countermagic": "Counterspells",
    "counter-magic": "Counterspells",
    "counterspells": "Counterspells",
    # Lands
    "lands": "Lands",
    "land": "Lands",
    "utilitylands": "Lands",
    "utility-lands": "Lands",
    # Tutors
    "tutors": "Tutors",
    "tutor": "Tutors",
    # Combo / Win Conditions
    "combo": "Win Conditions",
    "winconditions": "Win Conditions",
    "win-conditions": "Win Conditions",
    "finishers": "Win Conditions",
    # High Synergy (commander-specific)
    "highsynergycards": "High Synergy",
    "high-synergy-cards": "High Synergy",
    "highsynergy": "High Synergy",
    # New / Trending
    "newcards": "New Cards",
    "new-cards": "New Cards",
    # Theme-specific (catch-all)
    "creatures": "Creatures",
    "enchantments": "Enchantments",
    "artifacts": "Artifacts",
    "instants": "Instants",
    "sorceries": "Sorceries",
    "planeswalkers": "Planeswalkers",
    "tokens": "Token Generators",
    "graveyard": "Graveyard",
    "selfmill": "Self-Mill",
    "discard": "Discard",
    "sacrifice": "Sacrifice",
    "lifegain": "Lifegain",
    "tribal": "Tribal",
    "voltron": "Voltron",
    "stax": "Stax",
}

# Categories to skip — these are EDHREC UI sections, not card recommendations
SKIP_TAGS = {
    "topcommanders", "newcommanders", "similarcommanders",
    "partners", "companions", "signaturecard",
    "tagsbypopularitysort", "coloridentity",
}


def fetch_cards_batch(names):
    """Fetch card prices in batches via Scryfall /cards/collection POST (75 per request)."""
    found = {}
    names_list = list(names)
    for i in range(0, len(names_list), 75):
        chunk = names_list[i:i + 75]
        payload = json.dumps({"identifiers": [{"name": n} for n in chunk]}).encode("utf-8")
        time.sleep(0.1)
        req = urllib.request.Request(
            f"{SCRYFALL_BASE}/cards/collection",
            data=payload,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        for card in data.get("data", []):
            found[card["name"].lower()] = card.get("prices", {}).get("usd")
    return found


def enrich_prices(categorized):
    """Replace EDHREC price placeholders with real Scryfall prices."""
    all_names = []
    for cards in categorized.values():
        for card in cards:
            all_names.append(card["name"])
    if not all_names:
        return
    print(f"  Enriching prices from Scryfall ({len(all_names)} cards)...", flush=True)
    prices = fetch_cards_batch(all_names)
    for cards in categorized.values():
        for card in cards:
            scryfall_price = prices.get(card["name"].lower())
            if scryfall_price is not None:
                card["price_usd"] = scryfall_price


def slugify(name):
    slug = name.lower()
    slug = re.sub(r"[''',.]", "", slug)
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")


def fetch_commander_page(slug):
    """Fetch EDHREC commander page and return raw data."""
    time.sleep(0.2)
    url = f"{EDHREC_BASE}/commanders/{slug}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req) as resp:
            html = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise ValueError(
                f"Commander '{slug}' not found on EDHREC.\n"
                f"  Try the exact EDHREC slug (e.g. 'meren-of-clan-nel-toth')."
            )
        raise
    match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
    if not match:
        raise ValueError(f"No NEXT_DATA found for commander '{slug}'")
    return json.loads(match.group(1))["props"]["pageProps"]["data"]


def extract_card(cardview):
    """Extract relevant fields from an EDHREC cardview object."""
    prices = cardview.get("prices", {}) or {}
    return {
        "name": cardview.get("name", ""),
        "slug": cardview.get("sanitized", ""),
        "deck_count": cardview.get("num_decks", 0),
        "inclusion_rate": cardview.get("inclusion", 0),  # % of decks
        "synergy_score": cardview.get("synergy", 0),
        "price_usd": prices.get("usd"),
        "cmc": cardview.get("cmc"),
        "type": cardview.get("primary_type", ""),
    }


def fetch_staples(commander_slug, category_filter=None, top_n=15):
    """
    Fetch and categorize EDHREC card recommendations for a commander.
    Returns dict of {category: [card, ...]}
    """
    data = fetch_commander_page(commander_slug)
    cardlists = (
        data.get("container", {})
            .get("json_dict", {})
            .get("cardlists", [])
    )

    # Also check top-level cardlists
    if not cardlists:
        cardlists = data.get("cardlists", [])

    categorized = {}
    uncategorized = []

    for cl in cardlists:
        tag = cl.get("tag", "").lower()

        if tag in SKIP_TAGS:
            continue

        cards = [extract_card(c) for c in cl.get("cardviews", []) if c.get("name")]
        if not cards:
            continue

        category = CATEGORY_MAP.get(tag)
        if not category:
            # Try partial matches
            for key, val in CATEGORY_MAP.items():
                if key in tag or tag in key:
                    category = val
                    break

        if not category:
            # Use the header text if available, else tag name
            header = cl.get("header", "")
            category = header if header else tag.replace("-", " ").title()

        if category_filter and category.lower() != category_filter.lower():
            continue

        if category not in categorized:
            categorized[category] = []

        # Deduplicate within category
        existing_names = {c["name"] for c in categorized[category]}
        for card in cards[:top_n]:
            if card["name"] not in existing_names:
                categorized[category].append(card)
                existing_names.add(card["name"])

    return categorized


def get_commander_meta(data):
    """Extract commander name and color identity from page data."""
    name = ""
    colors = []
    try:
        # Try to get from card data on the page
        card_data = data.get("card", {})
        name = card_data.get("name", "")
        colors = card_data.get("color_identity", [])
    except Exception:
        pass
    return name, colors


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
    print(f"  EDHREC Staples: {commander_slug}")
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
    print(f"  AI selects from this list — no searching required.")


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
        print(f"Fetching EDHREC data for '{slug}'...")
        categorized = fetch_staples(slug, category_filter=args.category, top_n=args.top)

        if not categorized:
            print(f"No card categories found for '{slug}'.")
            print("The commander may use an unusual EDHREC page structure.")
            sys.exit(1)

        enrich_prices(categorized)

        if args.format == "json":
            print(json.dumps(categorized, indent=2))
        else:
            print_staples(slug, categorized, args.top, budget=args.budget)

    except urllib.error.HTTPError as e:
        print(f"\nHTTP Error {e.code}: {e.reason}")
        sys.exit(1)
    except ValueError as e:
        print(f"\nError: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
