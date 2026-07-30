#!/usr/bin/env python3
"""
filter-commanders.py — Fetch and filter commander candidates for a given theme + color.

Step 1: Fetch top commanders from EDHREC for a theme + color combination.
Step 2: Apply bracket heuristic based on deck count ranges.
Step 3: If budget provided, hit Scryfall to check each commander's price and strip over-budget picks.
Step 4: Output a ranked shortlist (default: top 6) for the AI to reason about.

Usage:
    python Ideation/scripts/filter-commanders.py --theme graveyard --color golgari --bracket 3
    python Ideation/scripts/filter-commanders.py --theme tokens --color selesnya --bracket 2 --budget 80
    python Ideation/scripts/filter-commanders.py --theme artifacts --color izzet --bracket 4 --limit 8
    python Ideation/scripts/filter-commanders.py --theme spellslinger --color izzet --bracket 3 --format json
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

# Deck count thresholds used as bracket proxy.
# A commander's EDHREC deck count gives a rough signal of its power ceiling
# and community adoption — not a perfect bracket map, but a useful pre-filter.
#
# Logic:
#   - Very low counts (<200): poorly supported, risky pick for new players
#   - Very high counts (>80k): often cEDH or near-cEDH staples → flag at brackets 1-2
#
BRACKET_CONFIG = {
    1: {"min_decks": 200,  "flag_above": 15000},
    2: {"min_decks": 200,  "flag_above": 40000},
    3: {"min_decks": 100,  "flag_above": None},
    4: {"min_decks": 0,    "flag_above": None},
    5: {"min_decks": 0,    "flag_above": None},
}


# ── EDHREC ────────────────────────────────────────────────────────────────────

def edhrec_fetch(path):
    """Fetch an EDHREC page and extract __NEXT_DATA__."""
    time.sleep(0.2)
    url = f"{EDHREC_BASE}{path}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req) as resp:
        html = resp.read().decode("utf-8")
    match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
    if not match:
        raise ValueError(f"No NEXT_DATA found at {url}")
    return json.loads(match.group(1))["props"]["pageProps"]["data"]


def fetch_commanders_for_theme_color(theme_slug, color_slug):
    """Return top + new commanders for a theme+color from EDHREC."""
    data = edhrec_fetch(f"/tags/{theme_slug}/{color_slug}")
    cardlists = data.get("container", {}).get("json_dict", {}).get("cardlists", [])
    top, new = [], []
    for cl in cardlists:
        if cl.get("tag") == "topcommanders":
            top = cl.get("cardviews", [])
        elif cl.get("tag") == "newcommanders":
            new = cl.get("cardviews", [])
    commanders = []
    for c in top:
        commanders.append({
            "name": c["name"],
            "slug": c.get("sanitized", ""),
            "deck_count": c.get("num_decks", 0),
            "source": "top",
        })
    for c in new:
        commanders.append({
            "name": c["name"],
            "slug": c.get("sanitized", ""),
            "deck_count": c.get("num_decks", 0),
            "source": "new",
        })
    return commanders


# ── Scryfall ──────────────────────────────────────────────────────────────────

def scryfall_get(url):
    """Make a GET request to Scryfall with rate limit respect."""
    time.sleep(0.1)
    req = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_commander_price(name):
    """
    Fetch a commander's USD price from Scryfall.
    Returns (price_usd: float | None, color_identity: list[str]).
    Uses fuzzy name match.
    """
    encoded = urllib.parse.urlencode({"fuzzy": name}, quote_via=urllib.parse.quote)
    url = f"{SCRYFALL_BASE}/cards/named?{encoded}"
    try:
        card = scryfall_get(url)
        price_str = card.get("prices", {}).get("usd")
        price = float(price_str) if price_str else None
        color_identity = card.get("color_identity", [])
        return price, color_identity
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None, []
        raise


# ── Filtering & scoring ───────────────────────────────────────────────────────

def apply_bracket_filter(commanders, bracket):
    """
    Filter commanders by deck count minimum and flag high-power outliers.
    Returns (filtered_list, flagged_names).
    """
    config = BRACKET_CONFIG.get(bracket, BRACKET_CONFIG[3])
    min_decks = config["min_decks"]
    flag_above = config["flag_above"]

    filtered = []
    flagged = []

    for c in commanders:
        if c["deck_count"] < min_decks:
            continue  # Too obscure / poorly supported
        if flag_above and c["deck_count"] > flag_above:
            flagged.append(c["name"])
        filtered.append(c)

    return filtered, flagged


def enrich_with_prices(commanders):
    """
    Add USD price and color identity to each commander via Scryfall.
    Modifies commanders in place.
    """
    total = len(commanders)
    for i, c in enumerate(commanders, 1):
        print(f"  Checking price {i}/{total}: {c['name']}...", end="\r", flush=True)
        price, colors = fetch_commander_price(c["name"])
        c["price_usd"] = price
        c["color_identity"] = colors
    print(" " * 60, end="\r")  # Clear the progress line


def apply_budget_filter(commanders, budget):
    """Remove commanders priced above the budget. Unknown prices are kept."""
    return [
        c for c in commanders
        if c.get("price_usd") is None or c["price_usd"] <= budget
    ]


def rank_commanders(commanders, bracket):
    """
    Sort commanders for presentation.
    Primary: deck count (more = better-supported)
    Secondary: new cards get a small boost (interesting picks)
    """
    def sort_key(c):
        new_boost = 1000 if c.get("source") == "new" else 0
        return -(c["deck_count"] + new_boost)

    return sorted(commanders, key=sort_key)


# ── Output ────────────────────────────────────────────────────────────────────

def format_colors(color_identity):
    color_map = {"W": "White", "U": "Blue", "B": "Black", "R": "Red", "G": "Green"}
    if not color_identity:
        return "Colorless"
    return "/".join(color_map.get(c, c) for c in color_identity)


def print_results(theme, color, bracket, budget, commanders, flagged, limit):
    budget_str = f"${budget}" if budget else "no limit"
    print(f"\n{'='*60}")
    print(f"  Commander Shortlist: {theme} / {color}")
    print(f"  Bracket: {bracket}   Budget: {budget_str}")
    print(f"{'='*60}")

    if not commanders:
        print("  No commanders matched your filters.")
        print("  Try broadening the color identity or raising the budget.")
        return

    shown = commanders[:limit]
    for c in shown:
        price_str = f"${c['price_usd']:.2f}" if c.get("price_usd") is not None else "price unknown"
        color_str = format_colors(c.get("color_identity", []))
        flag = "  ⚠ HIGH POWER" if c["name"] in flagged else ""
        new_tag = "  [new]" if c.get("source") == "new" else ""
        print(f"\n  {c['name']}{new_tag}{flag}")
        print(f"    {color_str}  |  {c['deck_count']:,} decks  |  {price_str}")

    if len(commanders) > limit:
        print(f"\n  ({len(commanders) - limit} more filtered out — raise --limit to see them)")

    if flagged:
        print(f"\n  ⚠ High-power flags at bracket {bracket}:")
        for name in flagged:
            if name in [c["name"] for c in shown]:
                print(f"    - {name} (very popular, may exceed bracket {bracket} power level)")


def main():
    parser = argparse.ArgumentParser(
        description="Filter EDHREC commander candidates by bracket and budget."
    )
    parser.add_argument("--theme", required=True, metavar="SLUG",
                        help="EDHREC theme slug (e.g. 'graveyard', 'tokens')")
    parser.add_argument("--color", required=True, metavar="SLUG",
                        help="EDHREC color slug (e.g. 'golgari', 'izzet', 'simic')")
    parser.add_argument("--bracket", type=int, choices=[1, 2, 3, 4, 5], default=3,
                        help="Power bracket 1-5 (default: 3)")
    parser.add_argument("--budget", type=float, default=None,
                        help="Max USD price for the commander card (e.g. 20, 50)")
    parser.add_argument("--limit", type=int, default=6,
                        help="Max commanders to show (default: 6)")
    parser.add_argument("--format", choices=["text", "json"], default="text",
                        help="Output format (default: text)")
    args = parser.parse_args()

    try:
        print(f"Fetching commanders for {args.theme}/{args.color}...")
        commanders = fetch_commanders_for_theme_color(args.theme, args.color)

        if not commanders:
            print(f"No commanders found for theme '{args.theme}' + color '{args.color}'.")
            print("Check slugs with: python Ideation/scripts/fetch-edhrec-data.py --themes")
            sys.exit(1)

        print(f"Found {len(commanders)} commanders. Applying bracket {args.bracket} filter...")
        commanders, flagged = apply_bracket_filter(commanders, args.bracket)

        if args.budget is not None:
            print(f"Checking prices (budget: ${args.budget})...")
            enrich_with_prices(commanders)
            commanders = apply_budget_filter(commanders, args.budget)
        else:
            # Still fetch colors even without budget filter (useful metadata for AI)
            print("Fetching color identity from Scryfall...")
            enrich_with_prices(commanders)

        commanders = rank_commanders(commanders, args.bracket)

        if args.format == "json":
            output = {
                "theme": args.theme,
                "color": args.color,
                "bracket": args.bracket,
                "budget": args.budget,
                "flagged_high_power": flagged,
                "commanders": commanders[:args.limit],
            }
            print(json.dumps(output, indent=2))
        else:
            print_results(args.theme, args.color, args.bracket, args.budget,
                          commanders, flagged, args.limit)

    except urllib.error.HTTPError as e:
        print(f"\nHTTP Error {e.code}: {e.reason}")
        sys.exit(1)
    except ValueError as e:
        print(f"\nError: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
