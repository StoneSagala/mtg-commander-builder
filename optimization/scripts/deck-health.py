#!/usr/bin/env python3
"""
deck-health.py — Instant deck diagnostic. Run this the moment a deck comes in.

Parses the decklist, fetches card data from Scryfall, compares against bracket
baselines, and outputs a plain-language health report with a prioritized list
of what can be worked on. This replaces asking the player "what do you want to
fix?" — we tell them what we found, then they confirm direction.

Usage:
    python optimization/scripts/deck-health.py --file deckbuilding/brews/araumi-draft.md --commander "Araumi of the Dead Tide" --bracket 3
    python optimization/scripts/deck-health.py --file brew.md --commander "Meren of Clan Nel Toth" --bracket 3 --budget 150
    python optimization/scripts/deck-health.py --file brew.md --commander "Atraxa" --bracket 4 --format json
"""

import sys
import json
import re
import time
import argparse
import urllib.request
import urllib.parse
import urllib.error
from collections import defaultdict

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

SCRYFALL_BASE = "https://api.scryfall.com"
USER_AGENT    = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

BASIC_LANDS = {
    "Plains", "Island", "Swamp", "Mountain", "Forest", "Wastes",
    "Snow-Covered Plains", "Snow-Covered Island", "Snow-Covered Swamp",
    "Snow-Covered Mountain", "Snow-Covered Forest",
}

# Section headers → role key (same logic as generate-starter-deck.py)
SECTION_ROLE_MAP = {
    "ramp":            "ramp",
    "card draw":       "card_draw",
    "interaction":     "interaction",
    "tutors":          "tutors",
    "win conditions":  "win_cons",
    "theme":           "theme",
    "theme / synergy": "theme",
    "synergy":         "theme",
    "lands":           "lands",
    "encore synergy":  "theme",
    "edict package":   "interaction",
    "self-mill":       "theme",
    "reanimation":     "theme",
}

# Bracket baselines (midpoints)
BRACKET_BASELINES = {
    1: {"lands": 37, "ramp": 11, "card_draw": 9, "interaction": 11, "win_cons": 6, "tutors": 1},
    2: {"lands": 37, "ramp": 11, "card_draw": 9, "interaction": 11, "win_cons": 6, "tutors": 1},
    3: {"lands": 36, "ramp": 9,  "card_draw": 9, "interaction": 9,  "win_cons": 6, "tutors": 2},
    4: {"lands": 34, "ramp": 9,  "card_draw": 9, "interaction": 10, "win_cons": 3, "tutors": 6},
    5: {"lands": 30, "ramp": 6,  "card_draw": 7, "interaction": 10, "win_cons": 1, "tutors": 10},
}


# ─── Parser ───────────────────────────────────────────────────────────────────

def parse_decklist(filepath):
    """
    Parse a brew/draft file. Returns:
      cards        — list of card name strings (full deck, no commander)
      sections     — dict of {role: [card_name, ...]}
      commander    — str or ""
      raw_sections — dict of {header_text: [card_name, ...]} (for display)
    """
    cards = []
    sections = defaultdict(list)
    raw_sections = defaultdict(list)
    commander = ""
    current_role = None
    current_header = None
    in_commander_section = False

    with open(filepath, encoding="utf-8") as f:
        lines = f.readlines()

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("<!--"):
            continue

        # Commander section header
        if re.match(r"^Commander\s*:", stripped, re.IGNORECASE):
            in_commander_section = True
            current_role = None
            current_header = None
            continue

        # Other section headers (e.g. "Lands (36):", "Ramp (9):")
        m = re.match(r"^([A-Za-z][A-Za-z /\-]+?)\s*(?:\(\d+\))?\s*:", stripped)
        if m:
            header = m.group(1).strip()
            in_commander_section = False
            current_header = header
            current_role = SECTION_ROLE_MAP.get(header.lower())
            continue

        # Card line: "1 Card Name" or "4 Card Name"
        parts = stripped.split(None, 1)
        if len(parts) == 2:
            qty_str = parts[0].rstrip("x")
            if qty_str.isdigit():
                qty = int(qty_str)
                name = parts[1].strip()
                if in_commander_section:
                    commander = name
                else:
                    for _ in range(qty):
                        cards.append(name)
                    if current_role:
                        for _ in range(qty):
                            sections[current_role].append(name)
                    if current_header:
                        for _ in range(qty):
                            raw_sections[current_header].append(name)

    return cards, dict(sections), commander, dict(raw_sections)


# ─── Scryfall ─────────────────────────────────────────────────────────────────

def fetch_cards_batch(names):
    """Fetch card data in batches of 75 via Scryfall /cards/collection."""
    found = {}
    unique = list(dict.fromkeys(names))  # deduplicate, preserve order
    for i in range(0, len(unique), 75):
        chunk = unique[i:i + 75]
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
            price_str = card.get("prices", {}).get("usd")
            found[card["name"].lower()] = {
                "name": card["name"],
                "cmc": card.get("cmc", 0),
                "type_line": card.get("type_line", ""),
                "price": float(price_str) if price_str else None,
                "color_identity": card.get("color_identity", []),
                "legalities": card.get("legalities", {}),
            }
    return found


def fetch_commander_data(name):
    encoded = urllib.parse.urlencode({"fuzzy": name}, quote_via=urllib.parse.quote)
    url = f"{SCRYFALL_BASE}/cards/named?{encoded}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    time.sleep(0.1)
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


# ─── Analysis ─────────────────────────────────────────────────────────────────

def build_curve(cards, card_data):
    """Build a CMC distribution from card data. Excludes lands."""
    curve = defaultdict(int)
    for name in cards:
        info = card_data.get(name.lower())
        if not info:
            continue
        if "Land" in info.get("type_line", ""):
            continue
        cmc = int(min(info.get("cmc", 0), 8))  # cap at 8+ for display
        curve[cmc] += 1
    return dict(curve)


def avg_cmc(cards, card_data):
    cmcs = []
    for name in cards:
        info = card_data.get(name.lower())
        if not info:
            continue
        if "Land" in info.get("type_line", ""):
            continue
        cmcs.append(info.get("cmc", 0))
    return round(sum(cmcs) / len(cmcs), 2) if cmcs else 0.0


def total_price(cards, card_data):
    total = 0.0
    for name in cards:
        info = card_data.get(name.lower())
        if info and info.get("price") and name not in BASIC_LANDS:
            total += info["price"]
    return round(total, 2)


def color_balance(cards, card_data):
    """Count mana pips by color in non-land cards."""
    pips = defaultdict(int)
    for name in cards:
        info = card_data.get(name.lower())
        if not info or "Land" in info.get("type_line", ""):
            continue
        for color in info.get("color_identity", []):
            pips[color] += 1
    return dict(pips)


def generate_issues(sections, bracket, commander_cmc, avg, curve, card_count, budget, actual_price):
    """Generate a list of (severity, message) tuples for flagged issues."""
    issues = []
    baseline = BRACKET_BASELINES.get(bracket, BRACKET_BASELINES[3])

    land_count  = len(sections.get("lands", []))
    ramp_count  = len(sections.get("ramp", []))
    draw_count  = len(sections.get("card_draw", []))
    inter_count = len(sections.get("interaction", []))
    win_count   = len(sections.get("win_cons", []))
    tutor_count = len(sections.get("tutors", []))

    # Card count
    total = card_count + 1  # +1 for commander
    if total != 100:
        issues.append(("error", f"Card count is {total}/100 — deck is {'short' if total < 100 else 'over'} by {abs(100 - total)}"))

    # Lands
    if land_count < baseline["lands"] - 2:
        issues.append(("warn", f"Only {land_count} lands (target {baseline['lands']} for bracket {bracket}) — may struggle to hit mana on curve"))
    elif land_count > baseline["lands"] + 2:
        issues.append(("info", f"{land_count} lands (target {baseline['lands']}) — slightly high, could free up slots"))

    # Ramp
    if ramp_count < baseline["ramp"] - 2:
        issues.append(("warn", f"Only {ramp_count} ramp pieces (target {baseline['ramp']}) — deck will feel slow, especially with CMC {avg}"))

    # Card draw
    if draw_count < baseline["card_draw"] - 2:
        issues.append(("warn", f"Only {draw_count} card draw sources (target {baseline['card_draw']}) — will run out of gas mid-game"))

    # Interaction
    if inter_count < baseline["interaction"] - 2:
        issues.append(("warn", f"Only {inter_count} interaction pieces (target {baseline['interaction']}) — limited answers to threats"))

    # Win conditions
    if win_count < 2:
        issues.append(("warn", f"Only {win_count} win condition(s) — single point of failure, easily disrupted"))
    elif win_count > baseline["win_cons"] + 2:
        issues.append(("info", f"{win_count} win conditions may be diluting the main strategy"))

    # Tutors (bracket 3+)
    if bracket >= 3 and tutor_count < baseline["tutors"]:
        issues.append(("info", f"Only {tutor_count} tutors (target {baseline['tutors']} for bracket {bracket}) — harder to find key pieces consistently"))

    # Average CMC
    if avg > 3.8 and ramp_count < baseline["ramp"]:
        issues.append(("warn", f"High average CMC ({avg}) with low ramp ({ramp_count}) — casting spells on curve will be difficult"))
    elif avg > 4.2:
        issues.append(("warn", f"Average CMC {avg} is very high — consider cutting high-cost cards or adding more ramp"))

    # Curve shape — check for early plays
    early = sum(curve.get(i, 0) for i in [1, 2])
    if early < 8:
        issues.append(("info", f"Only {early} cards at CMC 1-2 — limited early game, vulnerable in the first few turns"))

    # Commander CMC
    if commander_cmc >= 5:
        issues.append(("info", f"Commander costs {int(commander_cmc)} mana — needs enough ramp to cast reliably"))

    # Budget
    if budget and actual_price > budget:
        issues.append(("error", f"Over budget: ${actual_price:.2f} / ${budget:.2f} (over by ${actual_price - budget:.2f})"))

    return issues


def optimization_menu(issues, sections):
    """Derive a prioritized list of what we can work on from the issues found."""
    menu = []

    severities = {sev for sev, _ in issues}
    has_errors  = "error" in severities
    has_warns   = "warn"  in severities

    land_count  = len(sections.get("lands", []))
    ramp_count  = len(sections.get("ramp", []))
    draw_count  = len(sections.get("card_draw", []))
    inter_count = len(sections.get("interaction", []))
    win_count   = len(sections.get("win_cons", []))

    # Priority order: errors first, then structural, then fine-tuning
    if has_errors:
        menu.append("Fix card count or budget violations (errors above)")
    if ramp_count < 7 or land_count < 33:
        menu.append("Mana base overhaul — lands and ramp are below where they need to be")
    elif ramp_count < 9:
        menu.append("Mana base tune — a few more ramp pieces would improve consistency")
    if draw_count < 7:
        menu.append("Add card draw — the engine will stall without more gas")
    if inter_count < 7:
        menu.append("Add interaction — more answers to threats and board states")
    if win_count < 2:
        menu.append("Add a backup win condition — one path is too fragile")
    menu.append("Goldfish simulation — see how fast and consistently the deck wins in a vacuum")
    menu.append("Slot-by-slot audit — find underperformers and upgrade them")
    menu.append("Speed run — identify the 5-10 cards that would make the deck faster")

    return menu


# ─── Output ───────────────────────────────────────────────────────────────────

SEVERITY_ICONS = {"error": "✗", "warn": "⚠", "info": "→"}

def bar_chart(curve, width=30):
    """ASCII bar chart for the CMC curve."""
    max_count = max(curve.values()) if curve else 1
    lines = []
    for cmc in range(0, 9):
        count = curve.get(cmc, 0)
        label = f"{cmc}+" if cmc == 8 else str(cmc)
        bar_len = int((count / max_count) * width) if max_count else 0
        bar = "█" * bar_len
        lines.append(f"  {label}  {bar:<{width}} {count}")
    return "\n".join(lines)


def print_report(commander, bracket, sections, curve, avg, price, budget, issues, menu, card_data, raw_sections):
    w = 64
    hr = "=" * w

    print(f"\n{hr}")
    print(f"  Deck Health Check")
    print(f"  Commander: {commander}  |  Bracket: {bracket}")
    print(hr)

    # Role counts
    land_count  = len(sections.get("lands",      []))
    ramp_count  = len(sections.get("ramp",        []))
    draw_count  = len(sections.get("card_draw",   []))
    inter_count = len(sections.get("interaction", []))
    win_count   = len(sections.get("win_cons",    []))
    tutor_count = len(sections.get("tutors",      []))
    baseline    = BRACKET_BASELINES.get(bracket, BRACKET_BASELINES[3])

    def ok_or_flag(actual, target, low_delta=2):
        if actual < target - low_delta:
            return f"⚠ {actual} (target {target})"
        elif actual > target + low_delta:
            return f"→ {actual} (target {target})"
        return f"✓ {actual}"

    print(f"\n  PACKAGE COUNTS")
    print(f"  {'Lands':<18} {ok_or_flag(land_count,  baseline['lands'])}")
    print(f"  {'Ramp':<18} {ok_or_flag(ramp_count,   baseline['ramp'])}")
    print(f"  {'Card Draw':<18} {ok_or_flag(draw_count,   baseline['card_draw'])}")
    print(f"  {'Interaction':<18} {ok_or_flag(inter_count, baseline['interaction'])}")
    print(f"  {'Win Conditions':<18} {ok_or_flag(win_count,   baseline['win_cons'])}")
    print(f"  {'Tutors':<18} {ok_or_flag(tutor_count, baseline['tutors'])}")

    print(f"\n  MANA CURVE  (avg CMC non-land: {avg})")
    print(bar_chart(curve))

    if price is not None:
        budget_str = f" / ${budget:.2f}" if budget else ""
        over = f"  ⚠ over by ${price - budget:.2f}" if budget and price > budget else ""
        print(f"\n  PRICE  ${price:.2f}{budget_str}{over}")

    if issues:
        print(f"\n  FLAGS")
        for sev, msg in issues:
            icon = SEVERITY_ICONS.get(sev, "→")
            print(f"  {icon}  {msg}")

    print(f"\n  WHAT WE CAN WORK ON")
    for i, item in enumerate(menu, 1):
        print(f"  {i}. {item}")

    print(f"\n{hr}\n")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Run a health check on an existing decklist."
    )
    parser.add_argument("--file",      required=True, metavar="PATH", help="Path to the deck file")
    parser.add_argument("--commander", required=True, metavar="NAME", help="Commander card name")
    parser.add_argument("--bracket",   type=int, required=True, choices=[1,2,3,4,5])
    parser.add_argument("--budget",    type=float, default=None, metavar="USD")
    parser.add_argument("--format",    choices=["text", "json"], default="text")
    args = parser.parse_args()

    print(f"Parsing decklist...")
    cards, sections, detected_commander, raw_sections = parse_decklist(args.file)
    commander = args.commander

    print(f"Fetching card data ({len(set(cards))} unique cards)...")
    all_names = list(set(cards)) + [commander]
    card_data = fetch_cards_batch(all_names)

    cmd_info = card_data.get(commander.lower(), {})
    commander_cmc = cmd_info.get("cmc", 0)

    curve   = build_curve(cards, card_data)
    avg     = avg_cmc(cards, card_data)
    price   = total_price(cards, card_data) if args.budget else None
    # Always get price if budget provided
    if args.budget and price is None:
        price = total_price(cards, card_data)
    # Get price regardless for the report
    price = total_price(cards, card_data)

    issues = generate_issues(
        sections, args.bracket, commander_cmc, avg, curve,
        len(cards), args.budget, price,
    )
    menu = optimization_menu(issues, sections)

    if args.format == "json":
        print(json.dumps({
            "commander": commander,
            "bracket": args.bracket,
            "card_count": len(cards) + 1,
            "sections": {k: len(v) for k, v in sections.items()},
            "avg_cmc": avg,
            "curve": curve,
            "price": price,
            "issues": [{"severity": s, "message": m} for s, m in issues],
            "optimization_menu": menu,
        }, indent=2))
    else:
        print_report(
            commander, args.bracket, sections, curve, avg,
            price, args.budget, issues, menu, card_data, raw_sections,
        )


if __name__ == "__main__":
    main()
