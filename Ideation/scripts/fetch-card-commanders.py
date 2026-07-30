#!/usr/bin/env python3
"""
fetch-card-commanders.py — Find commanders that play a given card.

Hits the EDHREC /cards/[slug] page and returns the top commanders that
include this card in their 99. Used in Flow C (win condition / combo first)
to reverse-engineer a commander from a key card.

Usage:
    python Ideation/scripts/fetch-card-commanders.py "Massacre Wurm"
    python Ideation/scripts/fetch-card-commanders.py "Thassa's Oracle" --top 10
    python Ideation/scripts/fetch-card-commanders.py "Dramatic Reversal" --color izzet
    python Ideation/scripts/fetch-card-commanders.py "Gravecrawler" --format json
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

# Deck count thresholds used as bracket proxy (same as filter-commanders.py)
BRACKET_CONFIG = {
    1: {"min_decks": 200,  "flag_above": 15000},
    2: {"min_decks": 200,  "flag_above": 40000},
    3: {"min_decks": 100,  "flag_above": None},
    4: {"min_decks": 0,    "flag_above": None},
    5: {"min_decks": 0,    "flag_above": None},
}

# EDHREC color slug map — used to filter commanders by color identity
COLOR_SLUGS = {
    "white": "white", "blue": "blue", "black": "black", "red": "red", "green": "green",
    "colorless": "colorless",
    # Guilds
    "azorius": "azorius", "dimir": "dimir", "rakdos": "rakdos", "gruul": "gruul",
    "selesnya": "selesnya", "orzhov": "orzhov", "izzet": "izzet", "golgari": "golgari",
    "boros": "boros", "simic": "simic",
    # Shards
    "esper": "esper", "grixis": "grixis", "jund": "jund", "naya": "naya", "bant": "bant",
    # Wedges
    "abzan": "abzan", "jeskai": "jeskai", "sultai": "sultai", "mardu": "mardu", "temur": "temur",
    # 4-color
    "yore": "yore-tiller", "glint": "glint-eye", "dune": "dune-brood",
    "ink": "ink-treader", "witch": "witch-maw",
    # 5-color
    "5c": "five-color", "5color": "five-color", "wubrg": "five-color",
}


def slugify(name):
    """Convert a card name to an EDHREC-style slug."""
    # Remove special characters (commas, apostrophes, etc.), lowercase, replace spaces with hyphens
    slug = name.lower()
    slug = re.sub(r"[''',.]", "", slug)
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    return slug


def fetch_page(path):
    """Fetch an EDHREC page and extract __NEXT_DATA__."""
    time.sleep(0.2)
    url = f"{EDHREC_BASE}{path}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req) as resp:
            html = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        raise e
    match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
    if not match:
        raise ValueError(f"No NEXT_DATA found at {url}")
    return json.loads(match.group(1))["props"]["pageProps"]["data"]


def extract_commanders_from_cardlists(cardlists):
    """
    Pull commander entries from EDHREC cardlists.
    Tries multiple known tag names used on card pages.
    """
    target_tags = {"topcommanders", "commanders", "top-commanders", "newcommanders"}
    commanders = []
    for cl in cardlists:
        tag = cl.get("tag", "")
        if tag in target_tags or "commander" in tag.lower():
            for c in cl.get("cardviews", []):
                commanders.append({
                    "name": c.get("name", ""),
                    "slug": c.get("sanitized", slugify(c.get("name", ""))),
                    "deck_count": c.get("num_decks", 0),
                    "inclusion_rate": c.get("synergy", None),  # % of decks, if available
                    "tag": tag,
                })
    return commanders


def fetch_card_commanders(card_name, color_filter=None):
    """
    Fetch the top commanders that play card_name from EDHREC.
    Optionally filter by color slug.
    Returns list of commander dicts.
    """
    card_slug = slugify(card_name)

    # Build URL — if color filter provided, try the color-specific endpoint
    if color_filter:
        color_slug = COLOR_SLUGS.get(color_filter.lower(), color_filter.lower())
        paths_to_try = [
            f"/cards/{card_slug}/{color_slug}",
            f"/cards/{card_slug}",
        ]
    else:
        paths_to_try = [f"/cards/{card_slug}"]

    data = None
    used_path = None
    last_error = None

    for path in paths_to_try:
        try:
            data = fetch_page(path)
            used_path = path
            break
        except urllib.error.HTTPError as e:
            last_error = e
            if e.code == 404:
                continue
            raise

    if data is None:
        if last_error and last_error.code == 404:
            raise ValueError(
                f"Card '{card_name}' not found on EDHREC.\n"
                f"  Tried slug: '{card_slug}'\n"
                f"  Check the card name spelling or try a different variant."
            )
        raise last_error

    # Try the standard container structure first
    cardlists = (
        data.get("container", {})
            .get("json_dict", {})
            .get("cardlists", [])
    )
    commanders = extract_commanders_from_cardlists(cardlists)

    # Fallback: some card pages expose commanders under panels or top-level keys
    if not commanders:
        for key in ("panels", "related_info"):
            section = data.get(key, {})
            if isinstance(section, dict):
                for subkey, val in section.items():
                    if "commander" in subkey.lower() and isinstance(val, list):
                        for item in val:
                            if "name" in item:
                                commanders.append({
                                    "name": item["name"],
                                    "slug": item.get("sanitized", slugify(item["name"])),
                                    "deck_count": item.get("count", 0),
                                    "inclusion_rate": None,
                                    "tag": subkey,
                                })

    # Remove duplicates by name (keep highest deck_count)
    seen = {}
    for c in commanders:
        name = c["name"]
        if name not in seen or c["deck_count"] > seen[name]["deck_count"]:
            seen[name] = c
    commanders = list(seen.values())

    # Sort by deck count descending
    commanders.sort(key=lambda c: -c["deck_count"])
    return commanders, card_slug, used_path


def fetch_commanders_prices_batch(commanders):
    """Enrich commanders with USD price and color identity via Scryfall batch API."""
    names = [c["name"] for c in commanders]
    found = {}
    for i in range(0, len(names), 75):
        chunk = names[i:i + 75]
        payload = json.dumps({"identifiers": [{"name": n} for n in chunk]}).encode("utf-8")
        time.sleep(0.1)
        req = urllib.request.Request(
            f"{SCRYFALL_BASE}/cards/collection",
            data=payload,
            headers={"User-Agent": USER_AGENT, "Accept": "application/json", "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        for card in data.get("data", []):
            price_str = card.get("prices", {}).get("usd")
            found[card["name"].lower()] = {
                "price": float(price_str) if price_str else None,
                "color_identity": card.get("color_identity", []),
            }
    for c in commanders:
        info = found.get(c["name"].lower(), {})
        c["price_usd"] = info.get("price")
        c["color_identity"] = info.get("color_identity", [])


def apply_bracket_filter(commanders, bracket):
    """Filter by min deck count and flag high-power outliers."""
    config = BRACKET_CONFIG.get(bracket, BRACKET_CONFIG[3])
    min_decks = config["min_decks"]
    flag_above = config["flag_above"]
    filtered, flagged = [], []
    for c in commanders:
        if c["deck_count"] < min_decks:
            continue
        if flag_above and c["deck_count"] > flag_above:
            flagged.append(c["name"])
        filtered.append(c)
    return filtered, flagged


def apply_budget_filter(commanders, budget):
    """Remove commanders priced above budget. Unknown prices kept."""
    return [c for c in commanders if c.get("price_usd") is None or c["price_usd"] <= budget]


def print_results(card_name, commanders, color_filter, top_n, bracket=None, budget=None, flagged=None):
    color_note = f" (filtered to {color_filter})" if color_filter else ""
    bracket_note = f"   Bracket: {bracket}" if bracket else ""
    budget_note = f"   Budget: ${budget}" if budget else ""
    print(f"\n{'='*60}")
    print(f"  Commanders that play: {card_name}{color_note}")
    if bracket_note or budget_note:
        print(f" {bracket_note}{budget_note}")
    print(f"{'='*60}")

    if not commanders:
        print(f"\n  No commanders found matching your filters.")
        print(f"  Try broadening color, raising budget, or removing --bracket.")
        return

    flagged = flagged or []
    shown = commanders[:top_n]
    for c in shown:
        price_str = f"${c['price_usd']:.2f}" if c.get("price_usd") is not None else "price unknown"
        colors = "".join(c.get("color_identity", [])) or "Colorless"
        flag = "  ⚠ HIGH POWER" if c["name"] in flagged else ""
        print(f"  {c['name']:<40} {c['deck_count']:>6,} decks  {colors}  {price_str}{flag}")

    if len(commanders) > top_n:
        print(f"\n  ... and {len(commanders) - top_n} more. Use --top {top_n + 10} to see more.")

    print(f"\n  To explore a commander's themes:")
    for c in shown[:3]:
        print(f"    python Ideation/scripts/fetch-edhrec-data.py --commander {c['slug']}")


def main():
    parser = argparse.ArgumentParser(
        description="Find top commanders that play a given card (Flow C — win condition first)."
    )
    parser.add_argument("card_name", help="Card name to look up (e.g. 'Massacre Wurm')")
    parser.add_argument("--top", type=int, default=8,
                        help="Number of commanders to show (default: 8)")
    parser.add_argument("--color", metavar="SLUG", default=None,
                        help="Filter to a color identity (e.g. 'golgari', 'izzet', 'black')")
    parser.add_argument("--bracket", type=int, choices=[1, 2, 3, 4, 5], default=None,
                        help="Filter by bracket (applies deck count threshold and flags high-power picks)")
    parser.add_argument("--budget", type=float, default=None,
                        help="Max USD price for the commander card (e.g. 20)")
    parser.add_argument("--format", choices=["text", "json"], default="text",
                        help="Output format (default: text)")
    args = parser.parse_args()

    try:
        print(f"Looking up '{args.card_name}' on EDHREC...")
        commanders, card_slug, path = fetch_card_commanders(args.card_name, args.color)

        flagged = []
        if args.bracket is not None:
            commanders, flagged = apply_bracket_filter(commanders, args.bracket)

        if args.bracket is not None or args.budget is not None:
            print(f"  Fetching prices ({len(commanders)} commanders)...")
            fetch_commanders_prices_batch(commanders)

        if args.budget is not None:
            commanders = apply_budget_filter(commanders, args.budget)

        if args.format == "json":
            print(json.dumps({
                "card": args.card_name,
                "slug": card_slug,
                "color_filter": args.color,
                "bracket": args.bracket,
                "budget": args.budget,
                "flagged_high_power": flagged,
                "commanders": commanders[:args.top],
            }, indent=2))
        else:
            print_results(args.card_name, commanders, args.color, args.top,
                          bracket=args.bracket, budget=args.budget, flagged=flagged)

    except urllib.error.HTTPError as e:
        print(f"\nHTTP Error {e.code}: {e.reason}")
        sys.exit(1)
    except ValueError as e:
        print(f"\nError: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
