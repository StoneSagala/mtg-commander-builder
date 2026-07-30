#!/usr/bin/env python3
"""
fetch-top-commanders.py — Fetch the top N commanders from EDHREC using Playwright.

Clicks "load more" until the target count is reached, then saves the list
to a local JSON cache file used by fetch-edhrec-data.py for popularity checks.

Usage:
  python fetch-top-commanders.py                  # Fetch top 150, save to cache
  python fetch-top-commanders.py --count 200      # Fetch top 200
  python fetch-top-commanders.py --check "Prosper, Tome-Bound"  # Check if a commander is in the list
  python fetch-top-commanders.py --list           # Print the cached list
"""

import sys
import json
import time
import argparse
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

CACHE_FILE = Path(__file__).parent / "_cache" / "top-commanders-cache.json"
EDHREC_URL = "https://edhrec.com/commanders"


def fetch_top_commanders(target=150):
    """Use Playwright to load EDHREC commanders page and click 'load more' until target is reached."""
    from playwright.sync_api import sync_playwright

    commanders = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        print(f"Loading {EDHREC_URL}...")
        page.goto(EDHREC_URL, wait_until="networkidle")

        max_clicks = 20
        clicks = 0

        while len(commanders) < target and clicks < max_clicks:
            # Extract current commanders from the page using confirmed selectors
            cards = page.evaluate("""
                () => {
                    const nameEls = document.querySelectorAll('span[class*="Card_name"]');
                    return Array.from(nameEls).map((el, index) => {
                        // Walk up to find the card container and look for deck count
                        const container = el.closest('[class*="Card_container"]');
                        const deckEl = container
                            ? container.querySelector('[class*="Card_num_decks"], [class*="numDecks"], [class*="deck_count"]')
                            : null;
                        return {
                            name: el.textContent.trim(),
                            decks: deckEl ? deckEl.textContent.trim() : null,
                            rank: index + 1
                        };
                    }).filter(c => c.name);
                }
            """)

            if cards:
                commanders = cards
                print(f"  Found {len(commanders)} commanders so far...")

            if len(commanders) >= target:
                break

            # Look for and click "load more" button
            load_more = page.query_selector('button:has-text("Load More")')
            if not load_more:
                load_more = page.query_selector('button:has-text("load more")')
            if not load_more:
                load_more = page.query_selector('[class*="load-more"]')

            if not load_more:
                print("  No 'load more' button found — may have reached the end.")
                break

            prev_count = len(commanders)
            print(f"  Clicking 'load more' (have {prev_count} so far)...")
            load_more.click()
            page.wait_for_timeout(2000)
            clicks += 1

        browser.close()

    return commanders[:target]


def save_cache(commanders):
    data = {
        "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "count": len(commanders),
        "commanders": commanders
    }
    with open(CACHE_FILE, "w") as f:
        json.dump(data, f, indent=2)
    print(f"\nSaved {len(commanders)} commanders to {CACHE_FILE}")


def load_cache():
    if not CACHE_FILE.exists():
        return None
    with open(CACHE_FILE) as f:
        return json.load(f)


def check_commander(name):
    """Check if a commander name is in the cached top list. Returns (in_list, rank)."""
    cache = load_cache()
    if not cache:
        print("No cache found. Run without --check first to build the cache.")
        return None, None

    name_lower = name.lower()
    for c in cache["commanders"]:
        if c["name"] and c["name"].lower() == name_lower:
            return True, c["rank"]

    # Fuzzy match — check if name is contained
    for c in cache["commanders"]:
        if c["name"] and name_lower in c["name"].lower():
            return True, c["rank"]

    return False, None


def main():
    parser = argparse.ArgumentParser(description="Fetch top commanders from EDHREC.")
    parser.add_argument("--count", type=int, default=150,
                        help="Number of commanders to fetch (default: 150)")
    parser.add_argument("--check", metavar="NAME",
                        help="Check if a commander is in the cached list")
    parser.add_argument("--list", action="store_true",
                        help="Print the cached commander list")
    parser.add_argument("--refresh", action="store_true",
                        help="Force refresh the cache even if it exists")
    args = parser.parse_args()

    if args.check:
        in_list, rank = check_commander(args.check)
        if in_list is None:
            sys.exit(1)
        if in_list:
            print(f"'{args.check}' is in the top list at rank #{rank} — TOO POPULAR")
            sys.exit(1)
        else:
            cache = load_cache()
            print(f"'{args.check}' is NOT in the top {cache['count']} — OK to use")
        return

    if args.list:
        cache = load_cache()
        if not cache:
            print("No cache found. Run without flags to build it.")
            sys.exit(1)
        print(f"Top {cache['count']} commanders (fetched {cache['fetched_at']}):\n")
        for c in cache["commanders"]:
            print(f"  #{c['rank']}: {c['name']}  ({c.get('decks', '?')})")
        return

    # Fetch and cache
    if CACHE_FILE.exists() and not args.refresh:
        cache = load_cache()
        print(f"Cache exists ({cache['count']} commanders, fetched {cache['fetched_at']})")
        print("Use --refresh to update, or --list to view.")
        return

    print(f"Fetching top {args.count} commanders from EDHREC...")
    commanders = fetch_top_commanders(target=args.count)

    if not commanders:
        print("Failed to fetch commanders. Check that EDHREC is accessible.")
        sys.exit(1)

    save_cache(commanders)
    print(f"\nTop 5 preview:")
    for c in commanders[:5]:
        print(f"  #{c['rank']}: {c['name']}")


if __name__ == "__main__":
    main()
