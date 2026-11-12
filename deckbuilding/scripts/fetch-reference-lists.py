#!/usr/bin/env python3
"""
fetch-reference-lists.py — Fetch top public decklists for a commander from Moxfield and Archidekt.

Returns the most-viewed public decklists from both platforms so the AI has reference points
beyond EDHREC aggregates. Use this to see what experienced pilots actually run —
card choices, ratios, and package decisions that community averages often miss.

Pass --theme to filter by build direction (theme, playstyle, win condition keywords).
Without --theme, returns the top overall decklists for the commander.

Usage:
    python deckbuilding/scripts/fetch-reference-lists.py "Meren of Clan Nel Toth"
    python deckbuilding/scripts/fetch-reference-lists.py "Meren" --theme "graveyard aristocrats sacrifice"
    python deckbuilding/scripts/fetch-reference-lists.py "Atraxa" --theme "proliferate counters infect" --top 3
    python deckbuilding/scripts/fetch-reference-lists.py "Teysa Karlov" --source moxfield
    python deckbuilding/scripts/fetch-reference-lists.py "Meren" --sort likes --format json
"""

import sys
import json
import time
import argparse
import urllib.request
import urllib.parse
import urllib.error
import contextlib

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

MOXFIELD_API = "https://api.moxfield.com/v2"
ARCHIDEKT_API = "https://archidekt.com/api"
USER_AGENT = "MTGCommanderBuilder/0.2 (https://github.com/StoneSagala/mtg-commander-builder)"

MOXFIELD_SORT = {
    "views": "views",
    "likes": "likes",
    "updated": "updated-at",
}

ARCHIDEKT_SORT = {
    "views": "-viewCount",
    "likes": "-likeCount",
    "updated": "-updatedAt",
}

# Archidekt format ID for Commander/EDH
ARCHIDEKT_COMMANDER_FORMAT = 3


# ── HTTP helpers ──────────────────────────────────────────────────────────────

def http_get(url, params=None, headers=None):
    time.sleep(0.2)
    if params:
        url += "?" + urllib.parse.urlencode(params)
    default_headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    if headers:
        default_headers.update(headers)
    req = urllib.request.Request(url, headers=default_headers)
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


# ── Moxfield ──────────────────────────────────────────────────────────────────

def moxfield_search(commander_name, sort_by="views", top_n=3, theme=None):
    # Base query: filter to this commander only.
    # Theme keywords are NOT appended — Moxfield searches titles/descriptions, not card lists,
    # which produces false positives for niche commanders.
    q = f'commander:"{commander_name}"'
    params = {
        "q": q,
        "sortType": MOXFIELD_SORT.get(sort_by, "views"),
        "sortDirection": "Descending",
        "pageNumber": 1,
        "pageSize": top_n,
        "fmt": "commander",
        "isPublic": "true",
    }
    data = http_get(
        f"{MOXFIELD_API}/decks/search",
        params=params,
        headers={"Origin": "https://www.moxfield.com"},
    )
    return data.get("data", [])


def moxfield_deck_cards(deck_id):
    data = http_get(
        f"{MOXFIELD_API}/decks/all/{deck_id}",
        headers={"Origin": "https://www.moxfield.com"},
    )
    sections = {}
    mainboard = data.get("boards", {}).get("mainboard", {}).get("cards", {})
    for _, entry in mainboard.items():
        card = entry.get("card", {})
        name = card.get("name", "")
        qty = entry.get("quantity", 1)
        type_line = card.get("type_line", "")
        section = _type_to_section(type_line)
        sections.setdefault(section, []).append({"name": name, "quantity": qty})
    for s in sections:
        sections[s].sort(key=lambda x: x["name"])
    return sections


def moxfield_to_summary(deck):
    deck_id = deck.get("publicId", deck.get("id", ""))
    return {
        "source": "Moxfield",
        "id": deck_id,
        "name": deck.get("name", "Unnamed"),
        "author": deck.get("createdByUser", {}).get("userName", "Unknown"),
        "views": deck.get("viewCount", 0),
        "likes": deck.get("likeCount", 0),
        "updated": (deck.get("lastUpdatedAtUtc", "") or "")[:10],
        "url": f"https://www.moxfield.com/decks/{deck_id}",
        "description": (deck.get("description", "") or "")[:200],
    }


# ── Archidekt ─────────────────────────────────────────────────────────────────

def archidekt_search(commander_name, sort_by="views", top_n=3, theme=None):
    # Combine commander name and theme keywords into one query
    # Archidekt searches deck names and descriptions
    q = commander_name.split(",")[0]
    if theme:
        q += f" {theme}"
    params = {
        "name": q,
        "deckFormat": ARCHIDEKT_COMMANDER_FORMAT,
        "orderBy": ARCHIDEKT_SORT.get(sort_by, "-viewCount"),
        "pageSize": top_n,
        "page": 1,
    }
    data = http_get(f"{ARCHIDEKT_API}/decks/v3/", params=params)
    return data.get("results", [])[:top_n]


def archidekt_deck_cards(deck_id):
    data = http_get(f"{ARCHIDEKT_API}/decks/{deck_id}/")
    sections = {}
    cards = data.get("cards", [])
    for entry in cards:
        card = entry.get("card", {})
        # Archidekt nests oracle card under card.oracleCard or card directly
        oracle = card.get("oracleCard", card)
        name = oracle.get("name", card.get("name", ""))
        qty = entry.get("quantity", 1)
        categories = entry.get("categories", [])

        # Use Archidekt category if set, else fall back to type line
        if categories:
            section = categories[0]
        else:
            type_line = oracle.get("typeLine", card.get("type_line", ""))
            section = _type_to_section(type_line)

        if name:
            sections.setdefault(section, []).append({"name": name, "quantity": qty})

    for s in sections:
        sections[s].sort(key=lambda x: x["name"])
    return sections


def archidekt_to_summary(deck):
    deck_id = deck.get("id", "")
    owner = deck.get("owner", {})
    author = owner.get("username", owner) if isinstance(owner, dict) else str(owner)
    return {
        "source": "Archidekt",
        "id": deck_id,
        "name": deck.get("name", "Unnamed"),
        "author": author,
        "views": deck.get("viewCount", 0),
        "likes": deck.get("likeCount", 0),
        "updated": (deck.get("updatedAt", "") or "")[:10],
        "url": f"https://archidekt.com/decks/{deck_id}",
        "description": (deck.get("description", "") or "")[:200],
    }


# ── Shared helpers ────────────────────────────────────────────────────────────

def _type_to_section(type_line):
    if "Land" in type_line:
        return "Lands"
    if "Creature" in type_line:
        return "Creatures"
    if "Instant" in type_line:
        return "Instants"
    if "Sorcery" in type_line:
        return "Sorceries"
    if "Enchantment" in type_line:
        return "Enchantments"
    if "Artifact" in type_line:
        return "Artifacts"
    if "Planeswalker" in type_line:
        return "Planeswalkers"
    return "Other"


def fetch_all(commander_name, source, sort_by, top_n, fetch_cards, theme=None, statuses=None):
    """
    Fetch deck summaries (and optionally card lists) from the requested source(s).
    Returns list of (summary_dict, card_data_dict_or_None).
    """
    results = []
    statuses = statuses if statuses is not None else {}
    theme_note = f" + theme: '{theme}'" if theme else ""

    if source in ("moxfield", "all"):
        print(f"  Moxfield: searching for '{commander_name}'{theme_note}...")
        try:
            decks = moxfield_search(commander_name, sort_by=sort_by, top_n=top_n, theme=theme)
            statuses["moxfield"] = {"status": "pass", "found": len(decks)}
            for deck in decks:
                summary = moxfield_to_summary(deck)
                cards = None
                if fetch_cards:
                    try:
                        cards = moxfield_deck_cards(summary["id"])
                    except (urllib.error.URLError, TimeoutError, ValueError) as error:
                        summary["cards_error"] = str(error)
                results.append((summary, cards))
            print(f"    Found {len(decks)} Moxfield list(s).")
        except (urllib.error.URLError, TimeoutError, ValueError) as e:
            statuses["moxfield"] = {"status": "blocked" if getattr(e, "code", None) == 403 else "unavailable", "error": str(e), "fallback": "Archidekt or paste/export a decklist"}
            if getattr(e, "code", None) == 403:
                print(f"    Moxfield returned 403 — API access may be restricted.")
            else:
                print(f"    Moxfield unavailable: {e}")

    if source in ("archidekt", "all"):
        print(f"  Archidekt: searching for '{commander_name}'{theme_note}...")
        try:
            decks = archidekt_search(commander_name, sort_by=sort_by, top_n=top_n, theme=theme)
            statuses["archidekt"] = {"status": "pass", "found": len(decks)}
            for deck in decks:
                summary = archidekt_to_summary(deck)
                cards = None
                if fetch_cards:
                    try:
                        cards = archidekt_deck_cards(summary["id"])
                    except (urllib.error.URLError, TimeoutError, ValueError) as error:
                        summary["cards_error"] = str(error)
                results.append((summary, cards))
            print(f"    Found {len(decks)} Archidekt list(s).")
        except (urllib.error.URLError, TimeoutError, ValueError) as e:
            statuses["archidekt"] = {"status": "unavailable", "error": str(e)}
            print(f"    Archidekt unavailable: {e}")

    return results


# ── Output ────────────────────────────────────────────────────────────────────

def print_summary(summary, index, show_cards=False, card_data=None):
    source_tag = f"[{summary['source']}]"
    print(f"\n  {'-'*55}")
    print(f"  #{index} {source_tag}  {summary['name']}")
    print(f"  By: {summary['author']}  |  {summary['views']:,} views  |  {summary['likes']:,} likes")
    print(f"  Updated: {summary['updated']}")
    print(f"  URL: {summary['url']}")
    if summary.get("description", "").strip():
        desc = summary["description"].strip()
        if len(desc) > 120:
            desc = desc[:117] + "..."
        print(f"  Notes: {desc}")

    if show_cards and card_data:
        for section, cards in card_data.items():
            if section == "Lands":
                continue
            print(f"\n    [{section}]")
            for card in cards:
                qty_str = f"{card['quantity']}x " if card["quantity"] > 1 else "   "
                print(f"      {qty_str}{card['name']}")


def print_results(commander_name, results, show_cards=False, theme=None):
    theme_note = f"  Theme filter: {theme}" if theme else "  No theme filter — top overall lists"
    print(f"\n{'='*60}")
    print(f"  Reference Decklists: {commander_name}")
    print(f"  {len(results)} list(s) from Moxfield + Archidekt")
    print(f"  {theme_note}")
    print(f"{'='*60}")

    if not results:
        print(f"\n  No decklists found. Try the exact commander card name.")
        return

    for i, (summary, card_data) in enumerate(results, 1):
        print_summary(summary, i, show_cards=show_cards, card_data=card_data)

    print(f"\n  Use these as reference — not as a template to copy.")
    print(f"  Key questions: What ramp do they run? What's the win condition?")
    print(f"  What did they cut that you included?")


def main():
    parser = argparse.ArgumentParser(
        description="Fetch top public decklists for a commander from Moxfield and Archidekt."
    )
    parser.add_argument("commander",
                        help="Commander name (e.g. 'Meren of Clan Nel Toth')")
    parser.add_argument("--top", type=int, default=3,
                        help="Number of decklists per source (default: 3)")
    parser.add_argument("--source", choices=["all", "moxfield", "archidekt"], default="all",
                        help="Which platform to pull from (default: all)")
    parser.add_argument("--sort", choices=["views", "likes", "updated"], default="views",
                        help="Sort order (default: views)")
    parser.add_argument("--theme", metavar="KEYWORDS", default=None,
                        help="Theme/playstyle keywords to filter by (e.g. 'graveyard aristocrats sacrifice'). "
                             "Searches deck titles and descriptions on both platforms.")
    parser.add_argument("--cards", action="store_true",
                        help="Also fetch and display full card lists")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args()

    if args.top < 1:
        parser.error("--top must be positive")
    statuses = {}
    with contextlib.redirect_stdout(sys.stderr):
        print(f"Fetching reference decklists for '{args.commander}'...")
        results = fetch_all(args.commander, args.source, args.sort, args.top, args.cards, theme=args.theme, statuses=statuses)

    if args.format == "json":
        output = []
        for summary, card_data in results:
            entry = dict(summary)
            if card_data:
                entry["cards"] = card_data
            output.append(entry)
        print(json.dumps({"results": output, "providers": statuses}, indent=2))
    else:
        print_results(args.commander, results, show_cards=args.cards, theme=args.theme)
    if statuses and all(status["status"] != "pass" for status in statuses.values()):
        sys.exit(2)


if __name__ == "__main__":
    main()
