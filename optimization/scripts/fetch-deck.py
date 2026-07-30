#!/usr/bin/env python3
"""
fetch-deck.py — Fetch a decklist from Moxfield or Archidekt and output it in
standard format, ready to save as an optimization session file.

Supported platforms:
    Moxfield   — https://www.moxfield.com/decks/{publicId}
    Archidekt  — https://archidekt.com/decks/{id}/

Usage:
    python optimization/scripts/fetch-deck.py "https://www.moxfield.com/decks/abc123"
    python optimization/scripts/fetch-deck.py "https://archidekt.com/decks/12345/"
    python optimization/scripts/fetch-deck.py "https://www.moxfield.com/decks/abc123" --output optimization/sessions/my-deck-2026-04-06.md
"""

import sys
import json
import re
import time
import argparse
import urllib.request
import urllib.parse
import urllib.error
import datetime

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


# ─── Platform detection ───────────────────────────────────────────────────────

def detect_platform(url: str):
    """Returns ('moxfield', id) or ('archidekt', id) or raises ValueError."""
    mox = re.search(r'moxfield\.com/decks/([A-Za-z0-9_-]+)', url)
    if mox:
        return "moxfield", mox.group(1)

    arch = re.search(r'archidekt\.com/decks/(\d+)', url)
    if arch:
        return "archidekt", arch.group(1)

    raise ValueError(
        f"Unrecognized deck URL: {url}\n"
        f"  Supported: moxfield.com/decks/... or archidekt.com/decks/..."
    )


# ─── Fetchers ─────────────────────────────────────────────────────────────────

def fetch_json(url: str) -> dict:
    time.sleep(0.1)
    req = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_moxfield(deck_id: str) -> dict:
    """
    Fetch deck from Moxfield public API.
    Returns normalized deck dict: {name, format, commander, mainboard}
    mainboard is list of (qty, card_name, categories).
    """
    url = f"https://api2.moxfield.com/v3/decks/all/{deck_id}"
    try:
        data = fetch_json(url)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise ValueError(f"Moxfield deck '{deck_id}' not found or is set to private.")
        raise

    deck_format = data.get("format", "commander").lower()
    deck_name = data.get("name", "Untitled Deck")

    # Commander(s)
    commanders = []
    for name, entry in data.get("commanders", {}).items():
        qty = entry.get("quantity", 1)
        commanders.append((qty, name))

    # Mainboard — Moxfield returns {card_name: {quantity, card, ...}}
    mainboard = []
    for name, entry in data.get("mainboard", {}).items():
        qty = entry.get("quantity", 1)
        mainboard.append((qty, name))

    # Companions
    companions = []
    for name, entry in data.get("companions", {}).items():
        qty = entry.get("quantity", 1)
        companions.append((qty, name))

    return {
        "name": deck_name,
        "format": deck_format,
        "commanders": commanders,
        "companions": companions,
        "mainboard": mainboard,
        "source": f"https://www.moxfield.com/decks/{deck_id}",
    }


def fetch_archidekt(deck_id: str) -> dict:
    """
    Fetch deck from Archidekt API.
    Returns normalized deck dict matching fetch_moxfield output format.
    """
    url = f"https://archidekt.com/api/decks/{deck_id}/"
    try:
        data = fetch_json(url)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise ValueError(f"Archidekt deck '{deck_id}' not found or is set to private.")
        raise

    deck_name = data.get("name", "Untitled Deck")
    deck_format = (data.get("deckFormat") or "commander")
    if isinstance(deck_format, int):
        # Archidekt uses numeric format IDs: 3 = Commander, 1 = Standard, etc.
        FORMAT_MAP = {1: "standard", 2: "modern", 3: "commander", 4: "legacy",
                      5: "vintage", 6: "pauper", 7: "pioneer", 11: "cedh"}
        deck_format = FORMAT_MAP.get(deck_format, "commander")

    commanders = []
    companions = []
    mainboard = []

    for card_entry in data.get("cards", []):
        qty = card_entry.get("quantity", 1)
        # Card name lives at card.oracleCard.name
        card_obj = card_entry.get("card", {})
        oracle = card_obj.get("oracleCard", {})
        name = oracle.get("name") or card_obj.get("name", "Unknown")
        categories = [c.lower() for c in (card_entry.get("categories") or [])]

        if "commander" in categories:
            commanders.append((qty, name))
        elif "companion" in categories:
            companions.append((qty, name))
        else:
            mainboard.append((qty, name))

    return {
        "name": deck_name,
        "format": deck_format,
        "commanders": commanders,
        "companions": companions,
        "mainboard": mainboard,
        "source": f"https://archidekt.com/decks/{deck_id}/",
    }


# ─── Output formatter ─────────────────────────────────────────────────────────

# Card type keywords → section name (checked against Scryfall type_line if available,
# otherwise we do a best-effort name-based sort which is good enough for display)
SECTION_ORDER = [
    "Commander",
    "Companion",
    "Lands",
    "Creatures",
    "Instants",
    "Sorceries",
    "Artifacts",
    "Enchantments",
    "Planeswalkers",
    "Other",
]


def format_deck(deck: dict) -> str:
    """Format a normalized deck dict into our standard markdown format."""
    today = datetime.date.today().isoformat()
    lines = []

    lines.append(f"# {deck['name']} — {deck['format'].title()}")
    lines.append(f"# Source: {deck['source']}")
    lines.append(f"# Fetched: {today}")
    lines.append("")

    # Commander
    if deck["commanders"]:
        lines.append("Commander:")
        for qty, name in sorted(deck["commanders"], key=lambda x: x[1]):
            lines.append(f"{qty} {name}")
        lines.append("")

    # Companion
    if deck["companions"]:
        lines.append("Companion:")
        for qty, name in sorted(deck["companions"], key=lambda x: x[1]):
            lines.append(f"{qty} {name}")
        lines.append("")

    # Mainboard — unsectioned (we don't have type data without Scryfall calls)
    # Group into Lands vs Non-lands using a name heuristic for common land names
    KNOWN_BASICS = {"Plains", "Island", "Swamp", "Mountain", "Forest", "Wastes"}
    LAND_SUFFIXES = ("land", "cavern", "hub", "tower", "bog", "mine", "vault",
                     "den", "crypt", "sea", "shore", "coast", "isle", "tomb",
                     "mire", "marsh", "lair", "glen", "pass", "peak", "heath",
                     "glade", "wilds", "expanse", "channel", "delta", "flats",
                     "confluence", "crossing", "reaches", "sanctuary", "estuary",
                     "springs", "lagoon", "depths", "tundra", "taiga", "savannah",
                     "plateau", "scrubland", "bayou", "badlands", "underground sea",
                     "volcanic island", "tropical island",)

    def looks_like_land(name: str) -> bool:
        if name in KNOWN_BASICS:
            return True
        nl = name.lower()
        return any(nl.endswith(s) or s in nl for s in LAND_SUFFIXES)

    lands = [(q, n) for q, n in deck["mainboard"] if looks_like_land(n)]
    nonlands = [(q, n) for q, n in deck["mainboard"] if not looks_like_land(n)]

    if lands:
        lines.append(f"Lands ({sum(q for q,_ in lands)}):")
        for qty, name in sorted(lands, key=lambda x: x[1]):
            lines.append(f"{qty} {name}")
        lines.append("")

    if nonlands:
        lines.append(f"Other ({sum(q for q,_ in nonlands)}):")
        for qty, name in sorted(nonlands, key=lambda x: x[1]):
            lines.append(f"{qty} {name}")
        lines.append("")

    # Total
    total = (sum(q for q,_ in deck["commanders"]) +
             sum(q for q,_ in deck["companions"]) +
             sum(q for q,_ in deck["mainboard"]))
    lines.append(f"# Total: {total} cards")

    return "\n".join(lines)


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Fetch a decklist from Moxfield or Archidekt."
    )
    parser.add_argument("url", help="Deck URL (Moxfield or Archidekt)")
    parser.add_argument("--output", metavar="PATH", default=None,
                        help="Save output to this file path instead of printing to stdout")
    args = parser.parse_args()

    try:
        platform, deck_id = detect_platform(args.url)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    print(f"Fetching from {platform} (id: {deck_id})...")

    try:
        if platform == "moxfield":
            deck = fetch_moxfield(deck_id)
        else:
            deck = fetch_archidekt(deck_id)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code}: {e.reason}")
        sys.exit(1)

    output = format_deck(deck)

    if args.output:
        import os
        os.makedirs(os.path.dirname(args.output) if os.path.dirname(args.output) else ".", exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        total = (sum(q for q,_ in deck["commanders"]) +
                 sum(q for q,_ in deck["mainboard"]))
        print(f"  '{deck['name']}' — {total} cards — saved to {args.output}")
    else:
        print()
        print(output)


if __name__ == "__main__":
    main()
