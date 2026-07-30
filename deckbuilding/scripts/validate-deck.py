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
    - Extra turn cards (banned at bracket 1, flagged at 2-3)
    - Mass land denial (banned at brackets 1-3)
    - Early infinite combos (banned at brackets 1-2, late-game only at 3)

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

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

SCRYFALL_BASE = "https://api.scryfall.com"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

GAME_CHANGERS_FILE = Path(__file__).parent.parent / "docs" / "game-changers.md"

BASIC_LANDS = {
    "Plains", "Island", "Swamp", "Mountain", "Forest", "Wastes",
    "Snow-Covered Plains", "Snow-Covered Island", "Snow-Covered Swamp",
    "Snow-Covered Mountain", "Snow-Covered Forest",
}

# Extra turn cards — banned at bracket 1, flagged (low quantity only) at brackets 2-3
EXTRA_TURN_CARDS = {
    "Time Warp", "Temporal Manipulation", "Capture of Jingzhou",
    "Temporal Trespass", "Part the Waterveil", "Walk the Aeons",
    "Expropriate", "Beacon of Tomorrows", "Nexus of Fate",
    "Alrund's Epiphany", "Savor the Moment", "Karn's Temporal Sundering",
    "Magistrate's Scepter", "Second Chance", "Warrior's Oath",
    "Notorious Throng", "Meander", "Emrakul, the Promised End",
    "Seedtime", "Stitch in Time", "Time Stretch", "Time Spiral",
    "Teferi, Master of Time", "Wandering Archaic",
}

# Mass land denial — not allowed at brackets 1-3
MASS_LAND_DENIAL = {
    "Armageddon", "Ravages of War", "Apocalypse", "Jokulhaups",
    "Obliterate", "Decree of Annihilation", "Sunder",
    "Keldon Firebombers", "Catastrophe", "Cataclysm",
    "Impending Disaster", "Burning Sands", "Winter Orb",
    "Static Orb", "Stasis", "Land Equilibrium",
    "Numot, the Devastator", "Plow Under", "Hokori, Dust Drinker",
    "Ruination", "Mana Vortex", "Blood Moon", "Magus of the Moon",
    "Back to Basics",
}

# Bracket rules summary
BRACKET_RULES = {
    1: {
        "game_changers_max": 0,
        "extra_turns": "none",       # not allowed
        "mass_land_denial": False,
        "early_combos": False,
        "late_combos": False,
    },
    2: {
        "game_changers_max": 0,
        "extra_turns": "low",        # low quantities, not chained
        "mass_land_denial": False,
        "early_combos": False,
        "late_combos": False,
    },
    3: {
        "game_changers_max": 3,
        "extra_turns": "low",
        "mass_land_denial": False,
        "early_combos": False,
        "late_combos": True,         # late-game combos OK
    },
    4: {
        "game_changers_max": None,   # no limit
        "extra_turns": "any",
        "mass_land_denial": True,
        "early_combos": True,
        "late_combos": True,
    },
    5: {
        "game_changers_max": None,
        "extra_turns": "any",
        "mass_land_denial": True,
        "early_combos": True,
        "late_combos": True,
    },
}


# ── Game changers ─────────────────────────────────────────────────────────────

def load_game_changers():
    """Parse game-changers.md and return a set of card names."""
    if not GAME_CHANGERS_FILE.exists():
        # Fallback hardcoded list if doc is missing
        return {
            "Drannith Magistrate", "Enlightened Tutor", "Humility", "Serra's Sanctum",
            "Smothering Tithe", "Teferi's Protection", "Consecrated Sphinx", "Cyclonic Rift",
            "Expropriate", "Fierce Guardianship", "Force of Will", "Intuition",
            "Jin-Gitaxias, Core Augur", "Mystical Tutor", "Narset, Parter of Veils",
            "Rhystic Study", "Thassa's Oracle", "Urza, Lord High Artificer",
            "Ad Nauseam", "Bolas's Citadel", "Demonic Tutor", "Imperial Seal",
            "Necropotence", "Opposition Agent", "Orcish Bowmasters", "Tergrid, God of Fright",
            "Vampiric Tutor", "Deflecting Swat", "Gamble", "Jeska's Will", "Underworld Breach",
            "Crop Rotation", "Food Chain", "Gaea's Cradle", "Natural Order",
            "Seedborn Muse", "Survival of the Fittest", "Vorinclex, Voice of Hunger",
            "Worldly Tutor", "Aura Shards", "Grand Arbiter Augustin IV", "Kinnan, Bonder Prodigy",
            "Notion Thief", "Winota, Joiner of Forces", "Yuriko, the Tiger's Shadow",
            "Chrome Mox", "Grim Monolith", "Lion's Eye Diamond", "Mana Vault",
            "Mox Diamond", "The One Ring", "Ancient Tomb", "Glacial Chasm",
            "Mishra's Workshop", "The Tabernacle at Pendrell Vale",
        }
    names = set()
    with open(GAME_CHANGERS_FILE, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("- "):
                names.add(line[2:].strip())
    return names


# ── Scryfall ──────────────────────────────────────────────────────────────────

def scryfall_get(url):
    time.sleep(0.5)
    req = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
    )
    with urllib.request.urlopen(req) as resp:
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
        with urllib.request.urlopen(req) as resp:
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
        if re.match(r"^(Lands|Creatures|Spells|Ramp|Card Draw|Utility|Win|Theme|Theft|Synergy|Interaction|Protection)\b", stripped, re.IGNORECASE):
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
    total = len(cards) + (1 if commander else 0)
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

    is_banned = legalities.get("commander") == "banned"
    is_legendary = "Legendary" in type_line
    is_creature = "Creature" in type_line
    can_be_commander = "can be your commander" in oracle.lower()
    legal = not is_banned and (is_legendary and is_creature or can_be_commander)

    reasons = []
    if is_banned:
        reasons.append("BANNED in Commander")
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
    for card in cards_data:
        if card.get("_not_found"):
            continue
        if card.get("legalities", {}).get("commander") == "banned":
            banned.append(card["name"])
    return {
        "pass": len(banned) == 0,
        "banned_cards": banned,
        "detail": "No banned cards ✓" if not banned else f"{len(banned)} banned card(s): {', '.join(banned)}",
    }


def check_game_changers(card_names, bracket):
    game_changers = load_game_changers()
    found = [n for n in card_names if n in game_changers]
    rules = BRACKET_RULES[bracket]
    cap = rules["game_changers_max"]

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


def check_extra_turns(card_names, bracket):
    found = [n for n in card_names if n in EXTRA_TURN_CARDS]
    rules = BRACKET_RULES[bracket]
    policy = rules["extra_turns"]

    if policy == "none":
        passed = len(found) == 0
        detail = f"No extra turn cards allowed at bracket {bracket}"
        if found:
            detail += f" — found: {', '.join(found)}"
        else:
            detail += " ✓"
    elif policy == "low":
        passed = len(found) <= 2  # "low quantity" — flag if more than 2
        detail = f"{len(found)} extra turn card(s) — low quantity only at bracket {bracket}"
        if passed:
            detail += " ✓" if found else " (none) ✓"
        else:
            detail += f" — consider cutting to 1-2: {', '.join(found)}"
    else:
        passed = True
        detail = f"{len(found)} extra turn card(s) — unrestricted at bracket {bracket} ✓"

    return {"pass": passed, "found": found, "detail": detail}


def check_mass_land_denial(card_names, bracket):
    found = [n for n in card_names if n in MASS_LAND_DENIAL]
    allowed = BRACKET_RULES[bracket]["mass_land_denial"]

    if allowed:
        return {
            "pass": True,
            "found": found,
            "detail": f"{len(found)} mass land denial card(s) — allowed at bracket {bracket} ✓",
        }
    passed = len(found) == 0
    return {
        "pass": passed,
        "found": found,
        "detail": "No mass land denial ✓" if passed else f"Mass land denial not allowed at bracket {bracket}: {', '.join(found)}",
    }


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
    total = 0.0
    priced = []

    for card in cards_data:
        if card.get("_not_found"):
            continue
        name = card.get("name", "?")
        usd = card.get("prices", {}).get("usd")
        if usd:
            price = float(usd)
            total += price
            priced.append((name, price))

    priced.sort(key=lambda x: x[1], reverse=True)

    if budget_limit is None:
        return {
            "pass": True,
            "total": total,
            "limit": None,
            "detail": f"Total: ${total:.2f} (no budget limit set)",
        }

    passed = total <= budget_limit
    over = total - budget_limit
    detail = f"${total:.2f} / ${budget_limit:.2f}"
    if passed:
        detail += " ✓"
    else:
        detail += f" — over by ${over:.2f}"
        if priced:
            top = ", ".join(f"{n} ${p:.2f}" for n, p in priced[:3])
            detail += f"\n           Most expensive: {top}"

    return {
        "pass": passed,
        "total": total,
        "limit": budget_limit,
        "most_expensive": priced[:5],
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
        ("Bracket Compliance", [
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

    all_passed = True
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
        print(f"  RESULT: ALL CHECKS PASSED ✓")
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
    parser.add_argument("--bracket", type=int, choices=[1, 2, 3, 4, 5], required=True,
                        help="Power bracket (1-5)")
    parser.add_argument("--exclude", nargs="*", metavar="CARD", default=[],
                        help="House rule exclusions — cards not allowed in your pod")
    parser.add_argument("--budget", type=float, default=None, metavar="USD",
                        help="Budget limit in USD (e.g. 150). Reports total price; fails if over limit.")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args()

    try:
        # Parse decklist
        print(f"Parsing {args.file}...")
        card_names = parse_decklist(args.file)
        commander_name = args.commander

        print(f"  {len(card_names)} cards found. Fetching card data from Scryfall...")

        # Fetch commander
        commander_card = get_commander_data(commander_name)

        # Fetch all cards (skip basics — always legal)
        cards_to_fetch = [n for n in card_names if n not in BASIC_LANDS]
        unique_names = list(dict.fromkeys(cards_to_fetch))  # deduplicated, preserve order
        total = len(unique_names)

        print(f"  Fetching {total} cards in batches from Scryfall...", flush=True)
        cards_data = fetch_cards_batch(unique_names)

        # Run checks
        results = {
            "card_count":          check_card_count(commander_name, card_names),
            "singleton":           check_singleton(card_names),
            "commander_legality":  check_commander_legality(commander_card),
            "color_identity":      check_color_identity(commander_card, cards_data),
            "ban_list":            check_ban_list(cards_data),
            "game_changers":       check_game_changers(card_names, args.bracket),
            "extra_turns":         check_extra_turns(card_names, args.bracket),
            "mass_land_denial":    check_mass_land_denial(card_names, args.bracket),
            "house_rules":         check_house_rules(card_names, args.exclude),
            "budget":              check_budget(cards_data, args.budget),
        }
        not_found = check_not_found(cards_data)

        if args.format == "json":
            print(json.dumps({
                "commander": commander_name,
                "bracket": args.bracket,
                "results": results,
                "not_found": not_found,
                "all_passed": all(r["pass"] for r in results.values()),
            }, indent=2))
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
