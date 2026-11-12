#!/usr/bin/env python3
"""
validate-deck.py — Comprehensive deck validation: Commander rules, bracket, and ban list.

Runs all compliance checks in a single pass and outputs a structured report.
Use this at Phase 11 instead of manual checks.

Checks:
  Commander Rules:
    - Exactly 100 cards (99 + commander)
    - Singleton (no duplicates, basic lands exempt)
    - Commander is a legal commander (legendary creature or has "can be your commander")
    - Color identity — every card within the commander's identity
    - No banned cards

  Bracket Compliance (based on official WotC bracket system):
    - Game Changer count vs bracket cap
    - Live oracle-text extra-turn / land-denial screening for player review
    - Combo completeness and timing need the separate Spellbook check and strategy review

  House Rules:
    - Cross-references the brief's exclude list and house rules against the deck

Usage:
    python deckbuilding/scripts/validate-deck.py --file deckbuilding/brews/meren-draft.md --commander "Meren of Clan Nel Toth" --bracket 3
    python deckbuilding/scripts/validate-deck.py --file brew.md --commander "Atraxa" --bracket 4
    python deckbuilding/scripts/validate-deck.py --file brew.md --commander "Teysa Karlov" --bracket 2 --exclude "Dockside Extortionist" "Thassa's Oracle"
    python deckbuilding/scripts/validate-deck.py --file brew.md --commander "Meren" --bracket 3 --format json
"""

import sys
import json
import re
import time
import argparse
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "_shared"))
from freshness import current_rules
from data_sources import commander_group
from deck_budget import price_cards, cents

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

SCRYFALL_BASE = "https://api.scryfall.com"
USER_AGENT = "MTGCommanderBuilder/0.2 (https://github.com/StoneSagala/mtg-commander-builder)"

BASIC_LANDS = {
    "Plains", "Island", "Swamp", "Mountain", "Forest", "Wastes",
    "Snow-Covered Plains", "Snow-Covered Island", "Snow-Covered Swamp",
    "Snow-Covered Mountain", "Snow-Covered Forest",
}

# ── Game changers ─────────────────────────────────────────────────────────────

def load_game_changers():
    return {name for names in current_rules()['game_changers'].values() for name in names}


# ── Scryfall ──────────────────────────────────────────────────────────────────

def scryfall_get(url):
    time.sleep(0.5)
    req = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_card(name):
    encoded = urllib.parse.urlencode({"fuzzy": name}, quote_via=urllib.parse.quote)
    try:
        return scryfall_get(f"{SCRYFALL_BASE}/cards/named?{encoded}")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return {"_not_found": True, "name": name}
        raise


def get_commander_data(name):
    card = fetch_card(name)
    if card.get("_not_found"):
        raise ValueError(f"Commander '{name}' not found on Scryfall.")
    return card


def fetch_cards_batch(names):
    """Fetch cards in batches via Scryfall /cards/collection POST (75 per request)."""
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
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        for card in data.get("data", []):
            found[card["name"].lower()] = card

    result = []
    for name in names_list:
        card = found.get(name.lower())
        result.append(card if card else {"_not_found": True, "name": name})
    return result


# ── Decklist parsing ──────────────────────────────────────────────────────────

def parse_decklist(filepath):
    """
    Parse a decklist file. Returns a list of card names (commander excluded).
    Commander is supplied via --commander CLI argument; no in-file detection.
    """
    cards = []

    with open(filepath, encoding="utf-8") as f:
        lines = f.readlines()

    in_commander_section = False
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Skip markdown headers and comments
        if stripped.startswith("#") or stripped.startswith("//") or stripped.startswith("<!--"):
            continue

        # Section headers
        if re.match(r"^Commander\s*:", stripped, re.IGNORECASE):
            in_commander_section = True
            continue
        if stripped.endswith(":") and not stripped[0].isdigit():
            in_commander_section = False

        # Parse "1 Card Name" or "1x Card Name" — skip commander section entry
        parts = stripped.split(None, 1)
        if len(parts) == 2:
            qty_str = parts[0].rstrip("x")
            if qty_str.isdigit() and not in_commander_section:
                qty = int(qty_str)
                name = parts[1].strip()
                for _ in range(qty):
                    cards.append(name)

    return cards


# ── Validation checks ─────────────────────────────────────────────────────────

def check_card_count(commander, cards):
    total = len(cards) + (len(commander) if isinstance(commander, list) else 1 if commander else 0)
    return {
        "pass": total == 100,
        "total": total,
        "detail": f"{total}/100 cards" + (" ✓" if total == 100 else f" ({'add' if total < 100 else 'remove'} {abs(100 - total)})"),
    }


def check_singleton(cards):
    counts = {}
    for name in cards:
        if name not in BASIC_LANDS:
            counts[name] = counts.get(name, 0) + 1
    duplicates = {k: v for k, v in counts.items() if v > 1}
    return {
        "pass": len(duplicates) == 0,
        "duplicates": duplicates,
        "detail": "No duplicates ✓" if not duplicates else f"{len(duplicates)} duplicate(s): {', '.join(duplicates.keys())}",
    }


def check_commander_legality(commander_card):
    type_line = commander_card.get("type_line", "")
    oracle = commander_card.get("oracle_text", "")
    legalities = commander_card.get("legalities", {})

    is_banned = legalities.get("commander") != "legal"
    is_legendary = "Legendary" in type_line
    is_creature = any(kind in type_line for kind in ("Creature", "Vehicle", "Spacecraft"))
    can_be_commander = "can be your commander" in oracle.lower()
    legal = not is_banned and (is_legendary and is_creature or can_be_commander)

    reasons = []
    if is_banned:
        reasons.append("Not verified legal in Commander")
    if not (is_legendary and is_creature) and not can_be_commander:
        reasons.append("Not a legendary creature and no 'can be your commander' text")

    return {
        "pass": legal,
        "detail": "Legal commander ✓" if legal else f"Illegal commander: {', '.join(reasons)}",
    }


def check_color_identity(commander_card, cards_data):
    commander_identity = set(commander_card.get("color_identity", []))
    violations = []
    for card in cards_data:
        if card.get("_not_found"):
            continue
        card_identity = set(card.get("color_identity", []))
        illegal = card_identity - commander_identity
        if illegal:
            color_names = {"W": "White", "U": "Blue", "B": "Black", "R": "Red", "G": "Green"}
            illegal_str = "/".join(color_names.get(c, c) for c in illegal)
            violations.append({"name": card["name"], "illegal_colors": illegal_str})
    return {
        "pass": len(violations) == 0,
        "violations": violations,
        "detail": "Color identity OK ✓" if not violations else f"{len(violations)} color violation(s)",
    }


def check_ban_list(cards_data):
    banned = []
    named_bans = set(current_rules()["banned_cards"])
    for card in cards_data:
        if card.get("_not_found"):
            continue
        if card.get("legalities", {}).get("commander") != "legal" or card.get("name") in named_bans:
            banned.append(card["name"])
    return {
        "pass": len(banned) == 0,
        "banned_cards": banned,
        "detail": "No banned cards ✓" if not banned else f"{len(banned)} banned card(s): {', '.join(banned)}",
    }


def check_game_changers(card_names, bracket):
    game_changers = load_game_changers()
    found = [n for n in card_names if n in game_changers]
    cap = current_rules()["brackets"][str(bracket)]["game_changers_max"]

    if cap is None:
        passed = True
        detail = f"{len(found)} Game Changer(s) — no limit at bracket {bracket} ✓"
    else:
        passed = len(found) <= cap
        detail = f"{len(found)}/{cap} Game Changers allowed at bracket {bracket}"
        if passed:
            detail += " ✓"
        else:
            over = len(found) - cap
            detail += f" — {over} over limit"

    return {
        "pass": passed,
        "found": found,
        "cap": cap,
        "detail": detail,
    }


def effect_screen(cards_data, pattern, label, bracket):
    found = []
    for card in cards_data:
        text = card.get('oracle_text', '') + ' ' + ' '.join(face.get('oracle_text', '') for face in card.get('card_faces', []))
        if re.search(pattern, text, re.IGNORECASE):
            found.append(card['name'])
    return {"pass": not found or bracket >= 4, "found": found, "review_required": bool(found),
            "detail": f"{label} candidates need player/table review: " + ', '.join(found) if found else f"No candidates in the live oracle-text {label.lower()} screen"}


def check_extra_turns(card_names, bracket, cards_data=()):
    return effect_screen(cards_data, r'extra turn', 'Extra-turn', bracket)


def check_mass_land_denial(card_names, bracket, cards_data=()):
    return effect_screen(cards_data, r'destroy all lands|exile all lands|each player sacrifices (?:all|\w+ of) (?:their |the )?lands|lands? (?:don.t|doesn.t) untap', 'Land-denial', bracket)


def check_house_rules(card_names, exclude_list):
    if not exclude_list:
        return {"pass": True, "found": [], "detail": "No house rules to check"}
    exclude_set = {e.lower() for e in exclude_list}
    found = [n for n in card_names if n.lower() in exclude_set]
    return {
        "pass": len(found) == 0,
        "found": found,
        "detail": "No house rule violations ✓" if not found else f"House rule violations: {', '.join(found)}",
    }


def check_budget(cards_data, budget_limit):
    """Sum card prices from Scryfall data. budget_limit=None means report only, no pass/fail."""
    total_cents = 0
    priced = []
    missing_prices = []

    for card in cards_data:
        if card.get("_not_found"):
            missing_prices.append(card.get("name", "?"))
            continue
        name = card.get("name", "?")
        usd = card.get("prices", {}).get("usd")
        amount = cents(usd)
        if amount is not None:
            price = amount / 100
            total_cents += amount
            priced.append((name, price))
        else:
            missing_prices.append(name)

    total = total_cents / 100
    priced.sort(key=lambda x: x[1], reverse=True)

    if budget_limit is None:
        return {
            "pass": True,
            "total": total,
            "limit": None,
            "detail": f"Total: ${total:.2f} (no budget limit set)",
        }

    limit_cents = cents(budget_limit)
    passed = limit_cents is not None and total_cents <= limit_cents and not missing_prices
    over = total - budget_limit
    detail = f"${total:.2f} known subtotal / ${budget_limit:.2f}"
    if missing_prices:
        detail += f" — {len(missing_prices)} unpriced cards; total budget unverified"
    if passed:
        detail += " ✓"
    elif over > 0:
        detail += f" — over by ${over:.2f}"
        if priced:
            top = ", ".join(f"{n} ${p:.2f}" for n, p in priced[:3])
            detail += f"\n           Most expensive: {top}"

    return {
        "pass": passed,
        "total": total,
        "limit": budget_limit,
        "most_expensive": priced[:5],
        "missing_prices": missing_prices,
        "detail": detail,
    }


def check_not_found(cards_data):
    missing = [c["name"] for c in cards_data if c.get("_not_found")]
    return missing


# ── Main ──────────────────────────────────────────────────────────────────────

def print_report(commander_name, bracket, results, not_found):
    def status(passed):
        return "✓ PASS" if passed else "✗ FAIL"

    print(f"\n{'='*60}")
    print(f"  Deck Validation Report")
    print(f"  Commander: {commander_name}  |  Bracket: {bracket}")
    print(f"{'='*60}")

    sections = [
        ("Commander Rules", [
            ("Card count",        results["card_count"]),
            ("Singleton",         results["singleton"]),
            ("Commander legality",results["commander_legality"]),
            ("Color identity",    results["color_identity"]),
            ("Ban list",          results["ban_list"]),
        ]),
        ("Bracket Screening (human review required)", [
            ("Game Changers",     results["game_changers"]),
            ("Extra turn cards",  results["extra_turns"]),
            ("Mass land denial",  results["mass_land_denial"]),
        ]),
        ("House Rules", [
            ("Exclude list",      results["house_rules"]),
        ]),
        ("Budget", [
            ("Budget",            results["budget"]),
        ]),
    ]

    all_passed = all(r["pass"] for r in results.values())
    for section_name, checks in sections:
        print(f"\n  [{section_name}]")
        for label, result in checks:
            s = status(result["pass"])
            print(f"  {s}  {label}: {result['detail']}")
            if not result["pass"]:
                all_passed = False
                # Print sub-details for violations
                if "violations" in result and result["violations"]:
                    for v in result["violations"]:
                        if isinstance(v, dict):
                            print(f"         → {v.get('name', v)}: {v.get('illegal_colors', '')}")
                        else:
                            print(f"         → {v}")
                if "banned_cards" in result:
                    for name in result["banned_cards"]:
                        print(f"         → {name}")

    if not_found:
        print(f"\n  ⚠ {len(not_found)} card(s) not found on Scryfall — verify manually:")
        for name in not_found:
            print(f"    - {name}")

    print(f"\n{'='*60}")
    if all_passed:
        print(f"  RESULT: AUTOMATED CHECKS PASSED — strategy/bracket review still required ✓")
    else:
        print(f"  RESULT: VIOLATIONS FOUND — resolve before finalizing")
    print(f"{'='*60}\n")

    return all_passed


def main():
    parser = argparse.ArgumentParser(
        description="Validate a Commander decklist against rules, bracket, and ban list."
    )
    parser.add_argument("--file", required=True, metavar="PATH",
                        help="Path to the decklist file")
    parser.add_argument("--commander", required=True, metavar="NAME",
                        help="Commander card name")
    parser.add_argument("--partner", default=None, help="Second commander (Partner/Friends forever/Background)")
    parser.add_argument("--bracket", type=int, choices=[1, 2, 3, 4, 5], required=True,
                        help="Power bracket (1-5)")
    parser.add_argument("--exclude", nargs="*", metavar="CARD", default=[],
                        help="House rule exclusions — cards not allowed in your pod")
    parser.add_argument("--budget", type=float, default=None, metavar="USD",
                        help="Budget limit in USD (e.g. 150). Reports total price; fails if over limit.")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args()
    if args.budget is not None and cents(args.budget) is None:
        parser.error("Budget must be a finite nonnegative amount, or omitted for no limit.")

    try:
        rules = current_rules()
        # Parse decklist
        print(f"Parsing {args.file}...", file=sys.stderr)
        card_names = parse_decklist(args.file)
        commander_name = args.commander

        print(f"  {len(card_names)} cards found. Fetching card data from Scryfall...", file=sys.stderr)

        # Fetch commander
        group = commander_group(commander_name, args.partner)
        commander_names = [c["name"] for c in group]
        commander_card = dict(group[0])
        commander_card["color_identity"] = sorted({color for c in group for color in c["color_identity"]})

        # Fetch basics too: color identity and price still matter.
        cards_to_fetch = card_names
        unique_names = list(dict.fromkeys(cards_to_fetch))  # deduplicated, preserve order
        total = len(unique_names)

        print(f"  Fetching {total} cards in batches from Scryfall...", flush=True, file=sys.stderr)
        cards_data = fetch_cards_batch(unique_names)

        # Keep quantities for budget, include commander price.
        lookup = {c["name"].lower(): c for c in cards_data}
        budget_cards = [lookup.get(n.lower(), {"name": n, "_not_found": True}) for n in card_names] + group

        if args.budget is not None:
            live_prices = price_cards(card_names + commander_names)
            budget_cards = [{"name": name, "prices": {"usd": str(live_prices[name] / 100) if live_prices.get(name) is not None else None}} for name in card_names + commander_names]

        # Run checks
        results = {
            "card_count":          check_card_count(commander_names, card_names),
            "singleton":           check_singleton(card_names),
            "commander_legality":  check_commander_legality(commander_card),
            "color_identity":      check_color_identity(commander_card, cards_data),
            "ban_list":            check_ban_list(cards_data),
            "game_changers":       check_game_changers(card_names + commander_names, args.bracket),
            "extra_turns":         check_extra_turns(card_names, args.bracket, cards_data + group),
            "mass_land_denial":    check_mass_land_denial(card_names, args.bracket, cards_data + group),
            "house_rules":         check_house_rules(card_names, args.exclude),
            "budget":              check_budget(budget_cards, args.budget),
        }
        not_found = check_not_found(cards_data)
        results["card_resolution"] = {"pass": not not_found, "detail": "All card names resolved" if not not_found else f"Unresolved cards: {not_found}"}

        all_passed = all(r["pass"] for r in results.values())
        if args.format == "json":
            print(json.dumps({
                "commander": commander_name,
                "commanders": commander_names,
                "rules_checked_at": rules["checked_at"],
                "scope": "Automated screening; human strategy and bracket review required",
                "bracket": args.bracket,
                "results": results,
                "not_found": not_found,
                "all_passed": all(r["pass"] for r in results.values()),
            }, indent=2))
            sys.exit(0 if all_passed else 1)
        else:
            all_passed = print_report(commander_name, args.bracket, results, not_found)
            sys.exit(0 if all_passed else 1)

    except urllib.error.HTTPError as e:
        print(f"\nHTTP Error {e.code}: {e.reason}")
        sys.exit(1)
    except FileNotFoundError:
        print(f"\nFile not found: {args.file}")
        sys.exit(1)
    except ValueError as e:
        print(f"\nError: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
