#!/usr/bin/env python3
"""
match-themes.py — Match a free-text vibe description to EDHREC theme slugs.

Fetches the full theme list from EDHREC (or uses a local cache), then scores
each theme against the player's vibe using keyword matching + synonym expansion.
Outputs the top 4-6 theme slugs for the AI to use as filter inputs.

Usage:
    python Ideation/scripts/match-themes.py --vibe "graveyard value and sacrifice"
    python Ideation/scripts/match-themes.py --vibe "big creatures that stomp" --top 6
    python Ideation/scripts/match-themes.py --vibe "storm off and win fast" --format json
    python Ideation/scripts/match-themes.py --list        # Show all themes with slugs
    python Ideation/scripts/match-themes.py --refresh     # Force refresh theme cache
"""

import sys
import json
import re
import time
import argparse
import urllib.request
import urllib.error
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

EDHREC_BASE = "https://edhrec.com"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
CACHE_FILE = Path(__file__).parent / "_cache" / "themes-cache.json"
CACHE_MAX_AGE_DAYS = 7

# Synonym map: player words → EDHREC theme words/slugs they should match
# Keys are words a player might say; values are theme name fragments to boost
SYNONYMS = {
    "graveyard": ["graveyard", "recursion", "reanimator", "reanimate", "discard", "mill"],
    "reanimator": ["reanimator", "reanimate", "graveyard", "recursion"],
    "recursion": ["recursion", "graveyard", "reanimator"],
    "sacrifice": ["sacrifice", "aristocrats", "sac"],
    "aristocrats": ["aristocrats", "sacrifice", "sac"],
    "tokens": ["tokens", "token", "go-wide", "populate"],
    "go-wide": ["tokens", "go-wide", "populate", "swarm"],
    "swarm": ["tokens", "go-wide", "swarm"],
    "storm": ["storm", "spellslinger", "cantrip"],
    "spells": ["spellslinger", "storm", "instants", "sorceries"],
    "spellslinger": ["spellslinger", "storm", "instants"],
    "combo": ["combo", "infinite", "storm", "eggs"],
    "infinite": ["infinite", "combo"],
    "control": ["control", "pillowfort", "stax"],
    "stax": ["stax", "control", "tax"],
    "pillowfort": ["pillowfort", "control", "stax"],
    "ramp": ["ramp", "landfall", "lands", "big mana"],
    "lands": ["lands", "landfall", "ramp", "land"],
    "landfall": ["landfall", "lands", "ramp"],
    "big": ["big", "stompy", "ramp", "eldrazi", "giant"],
    "stompy": ["stompy", "big", "aggro", "ramp"],
    "aggro": ["aggro", "stompy", "combat", "voltron"],
    "voltron": ["voltron", "equipment", "aura", "combat"],
    "equipment": ["equipment", "voltron", "aura"],
    "aura": ["aura", "equipment", "voltron", "enchantress"],
    "enchantress": ["enchantress", "aura", "enchantment"],
    "enchantments": ["enchantress", "enchantment", "aura"],
    "counters": ["counters", "+1/+1", "proliferate"],
    "proliferate": ["proliferate", "counters", "+1/+1"],
    "blink": ["blink", "flicker", "etb", "enters"],
    "flicker": ["flicker", "blink", "etb"],
    "etb": ["etb", "blink", "flicker", "enters"],
    "tribal": ["tribal", "typal"],
    "typal": ["typal", "tribal"],
    "clone": ["clone", "copy", "copycat"],
    "copy": ["copy", "clone", "copycat"],
    "artifacts": ["artifacts", "artifact", "treasure", "improvise"],
    "treasure": ["treasure", "artifacts", "gold"],
    "dragons": ["dragons", "dragon", "typal"],
    "zombies": ["zombies", "zombie", "typal", "graveyard"],
    "elves": ["elves", "elf", "typal", "ramp"],
    "goblins": ["goblins", "goblin", "typal", "aggro"],
    "slivers": ["slivers", "sliver", "typal"],
    "mill": ["mill", "graveyard", "self-mill"],
    "draw": ["draw", "card advantage", "wheels", "cantrip"],
    "wheels": ["wheels", "draw", "discard"],
    "discard": ["discard", "wheels", "madness", "graveyard"],
    "madness": ["madness", "discard"],
    "chaos": ["chaos", "random", "politics"],
    "politics": ["politics", "group hug", "monarch", "chaos"],
    "group hug": ["group hug", "politics", "monarch"],
    "monarch": ["monarch", "politics", "group hug"],
    "infect": ["infect", "poison", "toxic"],
    "poison": ["poison", "infect", "toxic"],
    "life": ["lifegain", "life", "drain"],
    "lifegain": ["lifegain", "life", "drain"],
    "drain": ["drain", "lifegain", "life"],
    "bounce": ["bounce", "blink", "flicker"],
    "land destruction": ["land destruction", "lands", "stax"],
}


def fetch_themes():
    """Fetch all themes from EDHREC /tags page."""
    time.sleep(0.2)
    url = f"{EDHREC_BASE}/tags"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req) as resp:
        html = resp.read().decode("utf-8")
    match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
    if not match:
        raise ValueError("No NEXT_DATA found at /tags")
    data = json.loads(match.group(1))["props"]["pageProps"]["data"]
    cardlists = data["container"]["json_dict"]["cardlists"]
    tags_list = next(
        (cl for cl in cardlists if cl.get("tag") == "tagsbypopularitysort"), None
    )
    if not tags_list:
        raise ValueError("Could not find tags list in /tags page")
    return [
        {
            "slug": t["url"].rsplit("/", 1)[-1],
            "name": t["name"],
            "count": t["num_decks"],
        }
        for t in tags_list["cardviews"]
    ]


def load_cache():
    if not CACHE_FILE.exists():
        return None
    with open(CACHE_FILE) as f:
        data = json.load(f)
    # Check age
    fetched_ts = data.get("fetched_at", 0)
    age_days = (time.time() - fetched_ts) / 86400
    if age_days > CACHE_MAX_AGE_DAYS:
        return None
    return data.get("themes", [])


def save_cache(themes):
    data = {"fetched_at": time.time(), "themes": themes}
    with open(CACHE_FILE, "w") as f:
        json.dump(data, f, indent=2)


def get_themes(refresh=False):
    if not refresh:
        cached = load_cache()
        if cached:
            return cached
    themes = fetch_themes()
    save_cache(themes)
    return themes


def score_theme(theme, vibe_words, expanded_words):
    """
    Score a theme against the player's vibe.
    Returns an int score — higher is better.
    """
    name_lower = theme["name"].lower()
    slug_lower = theme["slug"].lower()
    score = 0

    # Direct word matches in theme name/slug
    for word in vibe_words:
        if word in name_lower or word in slug_lower:
            score += 3

    # Synonym-expanded matches
    for word in expanded_words:
        if word in name_lower or word in slug_lower:
            score += 1

    # Boost themes with high deck counts slightly (popular = well-supported)
    if theme["count"] > 10000:
        score += 1

    return score


def expand_vibe(vibe_words):
    """Expand vibe words using the synonym map."""
    expanded = set()
    for word in vibe_words:
        expanded.update(SYNONYMS.get(word, [word]))
        # Also check multi-word keys
        for key, vals in SYNONYMS.items():
            if word in key:
                expanded.update(vals)
    return expanded


def match_themes(vibe, themes, top_n=5):
    """Score all themes against the vibe and return the top N."""
    vibe_lower = vibe.lower()
    # Tokenize: split on spaces and punctuation, filter short words
    vibe_words = [w for w in re.split(r"[\s,/\-]+", vibe_lower) if len(w) > 2]
    expanded_words = expand_vibe(vibe_words)

    scored = []
    for theme in themes:
        score = score_theme(theme, vibe_words, expanded_words)
        if score > 0:
            scored.append((score, theme))

    scored.sort(key=lambda x: (-x[0], -x[1]["count"]))
    return [(score, theme) for score, theme in scored[:top_n]]


def print_matches(vibe, matches):
    print(f"\n{'='*55}")
    print(f"  Theme Matches for: \"{vibe}\"")
    print(f"{'='*55}")
    if not matches:
        print("  No matches found. Try different keywords.")
        print("  Use --list to see all available themes.")
        return
    for score, theme in matches:
        print(f"  {theme['name']:<28} {theme['count']:>7,} decks  slug: {theme['slug']}")
    print()
    print("  Pass any of these slugs to fetch-edhrec-data.py:")
    for _, theme in matches:
        print(f"    python Ideation/scripts/fetch-edhrec-data.py --theme {theme['slug']}")


def print_all_themes(themes):
    print(f"\n{'='*55}")
    print(f"  All EDHREC Themes ({len(themes)} total)")
    print(f"{'='*55}")
    for t in themes:
        print(f"  {t['name']:<30} {t['count']:>7,} decks  slug: {t['slug']}")


def main():
    parser = argparse.ArgumentParser(
        description="Match a free-text vibe to EDHREC theme slugs."
    )
    parser.add_argument("--vibe", metavar="TEXT",
                        help="Free-text description of your playstyle or theme")
    parser.add_argument("--top", type=int, default=5,
                        help="Number of matches to return (default: 5)")
    parser.add_argument("--list", action="store_true",
                        help="Print all available themes")
    parser.add_argument("--refresh", action="store_true",
                        help="Force refresh the theme cache")
    parser.add_argument("--format", choices=["text", "json"], default="text",
                        help="Output format (default: text)")
    args = parser.parse_args()

    if not args.vibe and not args.list:
        parser.print_help()
        sys.exit(1)

    try:
        print("Fetching themes..." if args.refresh else "Loading themes...", end=" ", flush=True)
        themes = get_themes(refresh=args.refresh)
        print(f"({len(themes)} themes loaded)")
    except urllib.error.HTTPError as e:
        print(f"\nHTTP Error {e.code}: {e.reason}")
        sys.exit(1)
    except ValueError as e:
        print(f"\nError: {e}")
        sys.exit(1)

    if args.list:
        if args.format == "json":
            print(json.dumps(themes, indent=2))
        else:
            print_all_themes(themes)
        return

    matches = match_themes(args.vibe, themes, top_n=args.top)

    if args.format == "json":
        print(json.dumps([
            {"score": score, "slug": t["slug"], "name": t["name"], "deck_count": t["count"]}
            for score, t in matches
        ], indent=2))
    else:
        print_matches(args.vibe, matches)


if __name__ == "__main__":
    main()
