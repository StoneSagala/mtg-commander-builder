#!/usr/bin/env python3
"""
generate-starter-deck.py — Auto-generate a 100-card Commander draft from EDHREC + Scryfall.

Fetches EDHREC's pre-categorized card pool, calculates target slot counts from the
bracket baseline and strategy overrides, and auto-selects cards by synergy score.
Outputs a nearly-complete draft (~85-95% filled). The AI then reviews and swaps in
non-negotiables and special synergy pieces — one review pass instead of six selection
phases.

Usage:
    python deckbuilding/scripts/generate-starter-deck.py \
        --commander "Araumi of the Dead Tide" \
        --bracket 3 \
        --engine graveyard \
        --game-plan combo \
        --win-con life-depletion \
        --budget 200 \
        --output deckbuilding/brews/araumi-of-the-dead-tide-draft.md

    # Dry run (print to stdout):
    python deckbuilding/scripts/generate-starter-deck.py \
        --commander "Meren of Clan Nel Toth" \
        --bracket 3 --engine aristocrats --game-plan combo --win-con life-depletion \
        --print
"""

import sys
import json
import re
import time
import os
import argparse
import urllib.request
import urllib.parse
import urllib.error
import datetime

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

EDHREC_BASE = "https://edhrec.com"
SCRYFALL_BASE = "https://api.scryfall.com"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


# ─── Bracket baselines (midpoint of ranges from calculate-target-ratios.py) ───

BRACKET_TARGETS = {
    1: {"lands": 37, "ramp": 11, "card_draw": 9, "interaction": 11, "board_wipes": 2, "win_cons": 6, "tutors": 1},
    2: {"lands": 37, "ramp": 11, "card_draw": 9, "interaction": 11, "board_wipes": 2, "win_cons": 6, "tutors": 1},
    3: {"lands": 36, "ramp": 9,  "card_draw": 9, "interaction": 9,  "board_wipes": 2, "win_cons": 6, "tutors": 2},
    4: {"lands": 34, "ramp": 9,  "card_draw": 9, "interaction": 10, "board_wipes": 1, "win_cons": 3, "tutors": 6},
    5: {"lands": 30, "ramp": 6,  "card_draw": 7, "interaction": 10, "board_wipes": 0, "win_cons": 1, "tutors": 10},
}

# Strategy adjustments (same logic as calculate-target-ratios.py)
STRATEGY_ADJUSTMENTS = {
    "graveyard":          {"lands": -1},
    "lands":              {"lands": +4, "ramp": -2},
    "enchantress":        {"card_draw": -2},
    "spellslinger":       {"card_draw": -1},
    "combo":              {"win_cons": -2, "tutors": +3},
    "stax":               {"interaction": +2, "board_wipes": -1},
    "control":            {"interaction": +2, "win_cons": -1},
    "commander-damage":   {"win_cons": -2},
    "alternate-win-cons": {"win_cons": -2, "tutors": +2},
}


# ─── EDHREC category → deck slot mapping ─────────────────────────────────────

CATEGORY_TO_SLOT = {
    "Ramp":             "ramp",
    "Card Draw":        "card_draw",
    "Removal":          "interaction",
    "Board Wipes":      "board_wipes",
    "Counterspells":    "interaction",
    "Protection":       "interaction",
    "Tutors":           "tutors",
    "Win Conditions":   "win_cons",
    "High Synergy":     "theme",
    "Lands":            "utility_lands",
    "Creatures":        "theme",
    "Graveyard":        "theme",
    "Self-Mill":        "theme",
    "Enchantments":     "theme",
    "Artifacts":        "theme",
    "Instants":         "theme",
    "Sorceries":        "theme",
    "Sacrifice":        "theme",
    "Discard":          "theme",
    "New Cards":        "theme",
    "Token Generators": "theme",
    "Tribal":           "theme",
    "Voltron":          "theme",
    "Planeswalkers":    "theme",
}

# EDHREC tag → human category (duplicated from fetch-commander-staples.py)
CATEGORY_MAP = {
    "ramp": "Ramp", "manaartifacts": "Ramp", "mana-artifacts": "Ramp", "manaartefacts": "Ramp",
    "carddraw": "Card Draw", "card-draw": "Card Draw", "draw": "Card Draw", "cardadvantage": "Card Draw",
    "removal": "Removal", "targetedremoval": "Removal", "targeted-removal": "Removal", "singleremoval": "Removal",
    "boardwipes": "Board Wipes", "board-wipes": "Board Wipes", "massdestruction": "Board Wipes", "sweepers": "Board Wipes",
    "protection": "Protection",
    "countermagic": "Counterspells", "counter-magic": "Counterspells", "counterspells": "Counterspells",
    "lands": "Lands", "land": "Lands", "utilitylands": "Lands", "utility-lands": "Lands",
    "tutors": "Tutors", "tutor": "Tutors",
    "combo": "Win Conditions", "winconditions": "Win Conditions", "win-conditions": "Win Conditions", "finishers": "Win Conditions",
    "highsynergycards": "High Synergy", "high-synergy-cards": "High Synergy", "highsynergy": "High Synergy",
    "newcards": "New Cards", "new-cards": "New Cards",
    "creatures": "Creatures", "enchantments": "Enchantments", "artifacts": "Artifacts",
    "instants": "Instants", "sorceries": "Sorceries", "planeswalkers": "Planeswalkers",
    "graveyard": "Graveyard", "selfmill": "Self-Mill", "discard": "Discard",
    "sacrifice": "Sacrifice", "lifegain": "Lifegain", "tribal": "Tribal",
    "tokens": "Token Generators", "voltron": "Voltron", "stax": "Stax",
}

SKIP_TAGS = {
    "topcommanders", "newcommanders", "similarcommanders",
    "partners", "companions", "signaturecard",
    "tagsbypopularitysort", "coloridentity",
}

COLOR_BASICS = {
    "W": "Plains", "U": "Island", "B": "Swamp", "R": "Mountain", "G": "Forest",
}

# Cards that go in every deck regardless of EDHREC ranking
UNIVERSAL_RAMP = ["Sol Ring", "Arcane Signet"]
UNIVERSAL_LANDS = ["Command Tower"]


# ─── EDHREC fetch ─────────────────────────────────────────────────────────────

def slugify(name):
    slug = name.lower()
    slug = re.sub(r"[''',.]", "", slug)
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")


def fetch_commander_page(slug):
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
                f"  Try the exact EDHREC slug (e.g. 'araumi-of-the-dead-tide')."
            )
        raise
    match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
    if not match:
        raise ValueError(f"No NEXT_DATA found for '{slug}'")
    return json.loads(match.group(1))["props"]["pageProps"]["data"]


def extract_card(cardview):
    prices = cardview.get("prices", {}) or {}
    return {
        "name": cardview.get("name", ""),
        "deck_count": cardview.get("num_decks", 0),
        "inclusion_rate": cardview.get("inclusion", 0),
        "synergy_score": cardview.get("synergy", 0),
        "price_usd": prices.get("usd"),
        "cmc": cardview.get("cmc"),
        "type": cardview.get("primary_type", ""),
    }


def fetch_staples(slug):
    """Fetch and categorize EDHREC card recommendations. Returns (categorized, color_identity)."""
    data = fetch_commander_page(slug)
    cardlists = (
        data.get("container", {}).get("json_dict", {}).get("cardlists", [])
        or data.get("cardlists", [])
    )

    color_identity = []
    try:
        color_identity = data.get("card", {}).get("color_identity", [])
    except Exception:
        pass

    categorized = {}
    for cl in cardlists:
        tag = cl.get("tag", "").lower()
        if tag in SKIP_TAGS:
            continue

        cards = [extract_card(c) for c in cl.get("cardviews", []) if c.get("name")]
        if not cards:
            continue

        category = CATEGORY_MAP.get(tag)
        if not category:
            for key, val in CATEGORY_MAP.items():
                if key in tag or tag in key:
                    category = val
                    break
        if not category:
            header = cl.get("header", "")
            category = header if header else tag.replace("-", " ").title()

        if category not in categorized:
            categorized[category] = []
        existing = {c["name"] for c in categorized[category]}
        for card in cards:
            if card["name"] not in existing:
                categorized[category].append(card)
                existing.add(card["name"])

    return categorized, color_identity


# ─── Scryfall ─────────────────────────────────────────────────────────────────

def fetch_cards_batch(names):
    """Batch-fetch prices from Scryfall /cards/collection (75 per request)."""
    found = {}
    names_list = list(names)
    for i in range(0, len(names_list), 75):
        chunk = names_list[i:i + 75]
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
            found[card["name"].lower()] = float(price_str) if price_str else None
    return found


def fetch_commander_scryfall(name):
    """Fetch commander data from Scryfall for color identity fallback."""
    encoded = urllib.parse.urlencode({"fuzzy": name}, quote_via=urllib.parse.quote)
    url = f"{SCRYFALL_BASE}/cards/named?{encoded}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    time.sleep(0.1)
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_art_cards_for_theme(art_keywords, color_identity, budget=None):
    """
    Fetch cards matching art keywords from Scryfall for art/flavor-themed decks.
    Uses Scryfall's art: illustration tag search. Returns list of card name strings.
    """
    parts = [f"art:{kw}" for kw in art_keywords]
    if color_identity:
        parts.append(f"id<=({''.join(color_identity).upper()})")
    parts.append("-type:basic")
    query = " ".join(parts)

    encoded = urllib.parse.urlencode(
        {"q": query, "order": "cmc", "unique": "cards"},
        quote_via=urllib.parse.quote,
    )
    url = f"{SCRYFALL_BASE}/cards/search?{encoded}"

    cards = []
    while url and len(cards) < 400:
        time.sleep(0.1)
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 404:
                break
            raise
        for card in data.get("data", []):
            price_str = card.get("prices", {}).get("usd")
            price = float(price_str) if price_str else None
            if budget is not None and price is not None and price > budget:
                continue
            cards.append({
                "name": card["name"],
                "cmc": card.get("cmc", 0),
                "price_usd": price_str,
                # Art cards have no synergy score — sort_key will return (0, 0)
                "synergy_score": 0,
                "inclusion_rate": 0,
            })
        url = data.get("next_page") if data.get("has_more") else None

    print(f"  Art search '{' '.join(art_keywords)}': {len(cards)} cards found.")
    return cards


def enrich_prices(categorized):
    """Replace EDHREC prices with real Scryfall prices."""
    all_names = [c["name"] for cats in categorized.values() for c in cats]
    if not all_names:
        return
    print(f"  Enriching prices ({len(all_names)} cards)...", flush=True)
    prices = fetch_cards_batch(all_names)
    for cards in categorized.values():
        for card in cards:
            scryfall_price = prices.get(card["name"].lower())
            if scryfall_price is not None:
                card["price_usd"] = str(scryfall_price)


# ─── Target calculation ───────────────────────────────────────────────────────

def calculate_targets(bracket, engine, game_plan, win_con):
    """Calculate adjusted slot targets from bracket baseline + strategy overrides."""
    targets = dict(BRACKET_TARGETS.get(bracket, BRACKET_TARGETS[3]))
    for slug in [engine, game_plan, win_con]:
        adj = STRATEGY_ADJUSTMENTS.get(slug, {})
        for key, delta in adj.items():
            if key in targets:
                targets[key] = max(0, targets[key] + delta)
    # board_wipes is a subset of interaction
    targets["board_wipes"] = min(targets["board_wipes"], targets["interaction"])
    return targets


# ─── Card selection ───────────────────────────────────────────────────────────

def sort_key(card):
    """Rank by synergy score first, then inclusion rate."""
    return (-card.get("synergy_score", 0), -card.get("inclusion_rate", 0))


def is_affordable(card, budget):
    if budget is None:
        return True
    price = card.get("price_usd")
    if price is None:
        return True  # unknown price — include and let AI decide
    try:
        return float(price) <= budget
    except (ValueError, TypeError):
        return True


def fill_slot(sections, section_name, used, staples, edhrec_categories, target_count):
    """Pick top cards from the given EDHREC categories into the section, up to target_count."""
    existing = len(sections[section_name])
    needed = target_count - existing
    if needed <= 0:
        return

    candidates = []
    for cat in edhrec_categories:
        for card in staples.get(cat, []):
            if card["name"] not in used:
                candidates.append(card)

    candidates.sort(key=sort_key)
    seen = set()
    added = 0
    for card in candidates:
        if card["name"] not in used and card["name"] not in seen:
            sections[section_name].append(card["name"])
            used.add(card["name"])
            seen.add(card["name"])
            added += 1
            if added >= needed:
                break


def build_deck(commander_name, targets, staples, color_identity, budget=None, art_cards=None):
    """
    Auto-select cards to fill each slot from the EDHREC staples pool.
    When art_cards is provided, theme/synergy slots are filled from art search
    instead of EDHREC — used for art-themed or flavor-themed decks.
    Returns (sections dict, used set).
    """
    # Apply budget filter to all staples
    if budget is not None:
        staples = {
            cat: [c for c in cards if is_affordable(c, budget)]
            for cat, cards in staples.items()
        }

    used = set()
    sections = {
        "Ramp":            [],
        "Card Draw":       [],
        "Interaction":     [],
        "Tutors":          [],
        "Win Conditions":  [],
        "Theme / Synergy": [],
        "Utility Lands":   [],
    }

    # Universal auto-includes (these go in regardless of EDHREC ranking)
    for name in UNIVERSAL_RAMP:
        if name not in used:
            sections["Ramp"].append(name)
            used.add(name)
    for name in UNIVERSAL_LANDS:
        sections["Utility Lands"].append(name)
        used.add(name)

    # Structural slots always come from EDHREC — mechanics matter here
    fill_slot(sections, "Ramp",           used, staples, ["Ramp"],                                    targets["ramp"])
    fill_slot(sections, "Card Draw",      used, staples, ["Card Draw"],                               targets["card_draw"])

    # Interaction: board wipes first, then removal and counterspells
    fill_slot(sections, "Interaction",    used, staples, ["Board Wipes"],                             targets["board_wipes"])
    remaining_interaction = targets["interaction"] - targets["board_wipes"]
    fill_slot(sections, "Interaction",    used, staples, ["Removal", "Counterspells", "Protection"],  remaining_interaction)

    fill_slot(sections, "Tutors",         used, staples, ["Tutors"],                                  targets["tutors"])
    fill_slot(sections, "Win Conditions", used, staples, ["Win Conditions"],                          targets["win_cons"])

    total_non_land = (targets["ramp"] + targets["card_draw"] + targets["interaction"] +
                      targets["tutors"] + targets["win_cons"])
    theme_target = 99 - targets["lands"] - total_non_land

    if art_cards:
        # Art theme mode: fill theme slots from art search results (sorted by CMC)
        art_pool = {"__art__": sorted(art_cards, key=lambda c: (c.get("cmc", 0), c["name"]))}
        fill_slot(sections, "Theme / Synergy", used, art_pool, ["__art__"], theme_target)
    else:
        # Standard mode: fill theme slots from EDHREC synergy categories
        theme_cats = [
            "High Synergy", "Creatures", "Graveyard", "Self-Mill", "Enchantments",
            "Artifacts", "Instants", "Sorceries", "Sacrifice", "Discard",
            "Token Generators", "New Cards", "Tribal", "Voltron", "Planeswalkers",
        ]
        fill_slot(sections, "Theme / Synergy", used, staples, theme_cats, theme_target)

    # Utility lands: up to 10 from EDHREC (Command Tower already counted)
    fill_slot(sections, "Utility Lands",  used, staples, ["Lands"],   min(10, targets["lands"] - 1))

    return sections, used


def build_basics(sections, targets, color_identity):
    """Fill remaining land slots with basic lands, split evenly by color."""
    utility_count = len(sections["Utility Lands"])
    basics_needed = targets["lands"] - utility_count

    if basics_needed <= 0:
        return {}

    colors = [c for c in color_identity if c in COLOR_BASICS]
    if not colors:
        return {"Wastes": basics_needed}

    per_color = basics_needed // len(colors)
    remainder = basics_needed % len(colors)
    basics = {}
    for i, color in enumerate(colors):
        land_name = COLOR_BASICS[color]
        count = per_color + (1 if i < remainder else 0)
        if count > 0:
            basics[land_name] = count
    return basics


# ─── Output ───────────────────────────────────────────────────────────────────

def format_decklist(commander_name, sections, basics, targets, budget, total_cards, art_theme=None):
    today = datetime.date.today().isoformat()
    lines = []
    lines.append(f"# {commander_name} — Commander")
    lines.append(f"# Theme: [fill in from brief]")
    lines.append(f"# Bracket: {targets.get('_bracket', '?')} | Avg CMC: TBD | Budget: ${budget or '?'}")
    lines.append(f"# Date: {today}")
    if art_theme:
        lines.append(f"# ART THEME: {art_theme} — theme slots filled by art search, not EDHREC synergy")
    lines.append(f"# AUTO-GENERATED — review and swap non-negotiables from brief")
    lines.append("")

    lines.append("Commander:")
    lines.append(f"1 {commander_name}")
    lines.append("")

    utility = sections["Utility Lands"]
    basic_total = sum(basics.values())
    land_total = len(utility) + basic_total
    lines.append(f"Lands ({land_total}):")
    for card in utility:
        lines.append(f"1 {card}")
    for land_name, count in sorted(basics.items()):
        lines.append(f"{count} {land_name}")
    lines.append("")

    section_order = ["Ramp", "Card Draw", "Interaction", "Tutors", "Win Conditions", "Theme / Synergy"]
    for section in section_order:
        cards = sections.get(section, [])
        if cards:
            lines.append(f"{section} ({len(cards)}):")
            for card in cards:
                lines.append(f"1 {card}")
            lines.append("")

    lines.append("")
    lines.append("## Validation Summary")
    lines.append(f"- Total: {total_cards}/100")
    lines.append(f"- Lands: {land_total} (target: {targets['lands']})")
    lines.append(f"- Ramp: {len(sections['Ramp'])} (target: {targets['ramp']})")
    lines.append(f"- Card Draw: {len(sections['Card Draw'])} (target: {targets['card_draw']})")
    lines.append(f"- Interaction: {len(sections['Interaction'])} (target: {targets['interaction']})")
    lines.append(f"- Tutors: {len(sections['Tutors'])} (target: {targets['tutors']})")
    lines.append(f"- Win Conditions: {len(sections['Win Conditions'])} (target: {targets['win_cons']})")
    lines.append(f"- Theme/Synergy: {len(sections['Theme / Synergy'])}")
    if budget:
        lines.append(f"- Budget filter: ${budget:.0f}")
    if total_cards < 100:
        lines.append(f"- ⚠ {100 - total_cards} slots unfilled — EDHREC pool thin for this commander. Fill manually.")

    lines.append("")
    lines.append("## AI Review Checklist")
    if art_theme:
        lines.append(f"- [ ] ART THEME MODE: theme slots filled by art:{art_theme} search — review for flavor fit")
        lines.append("- [ ] Structural slots (ramp/draw/interaction) still came from EDHREC — review those normally")
        lines.append("- [ ] Replace any art-theme cards that are mechanically dead weight with better options")
    lines.append("- [ ] Slot non-negotiables from brief (replace weakest theme cards)")
    lines.append("- [ ] Verify win conditions match the planned combo line")
    lines.append("- [ ] Check interaction style — adjust removal/counterspell ratio if needed")
    lines.append("- [ ] Verify mana base covers pip requirements")
    lines.append("- [ ] Run validate-deck.py after swaps")

    return "\n".join(lines)


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Auto-generate a Commander deck draft from EDHREC staples + Scryfall prices."
    )
    parser.add_argument("--commander", required=True, help="Commander name")
    parser.add_argument("--bracket", type=int, required=True, choices=[1, 2, 3, 4, 5])
    parser.add_argument("--engine", required=True,
                        help="Engine slug: graveyard, aristocrats, artifacts, enchantress, etc.")
    parser.add_argument("--game-plan", required=True, dest="game_plan",
                        help="Game plan slug: combo, control, go-wide, stax, etc.")
    parser.add_argument("--win-con", required=True, dest="win_con",
                        help="Win con slug: life-depletion, mill, poison, commander-damage, etc.")
    parser.add_argument("--budget", type=float, default=None,
                        help="Max total budget in USD — cards over this price are filtered out")
    parser.add_argument("--art-theme", metavar="KEYWORDS", default=None, dest="art_theme",
                        help="Space-separated art keywords (e.g. 'smile balloon party'). "
                             "Theme slots filled by Scryfall art search instead of EDHREC synergy.")
    parser.add_argument("--output", metavar="PATH", default=None,
                        help="Write draft to this file path")
    parser.add_argument("--print", action="store_true", dest="print_list",
                        help="Print to stdout instead of writing to file")
    args = parser.parse_args()

    slug = slugify(args.commander)

    print(f"Fetching EDHREC staples for '{slug}'...")
    staples, color_identity = fetch_staples(slug)

    if not color_identity:
        print("  Fetching color identity from Scryfall...")
        try:
            card = fetch_commander_scryfall(args.commander)
            color_identity = card.get("color_identity", [])
        except Exception as e:
            print(f"  Could not fetch color identity: {e}")

    print(f"  Color identity: {''.join(color_identity) or 'Colorless'}")
    cat_summary = ", ".join(f"{k}({len(v)})" for k, v in staples.items())
    print(f"  Categories: {cat_summary}")

    enrich_prices(staples)

    # Art theme: fetch art cards before building (if requested)
    art_cards = None
    if args.art_theme:
        art_keywords = args.art_theme.strip().split()
        print(f"\nArt theme mode: fetching cards with art:{' art:'.join(art_keywords)}...")
        art_cards = fetch_art_cards_for_theme(art_keywords, color_identity, budget=args.budget)
        if not art_cards:
            print("  ⚠ No art cards found — falling back to EDHREC theme selection.")
            art_cards = None

    targets = calculate_targets(args.bracket, args.engine, args.game_plan, args.win_con)
    targets["_bracket"] = args.bracket  # store for output only

    print(f"\nTargets (bracket {args.bracket} / {args.engine} / {args.game_plan} / {args.win_con}):")
    for k, v in targets.items():
        if not k.startswith("_"):
            print(f"  {k}: {v}")

    print("\nAuto-selecting cards...")
    sections, used = build_deck(
        args.commander, targets, staples, color_identity,
        budget=args.budget, art_cards=art_cards,
    )
    basics = build_basics(sections, targets, color_identity)

    total_cards = 1  # commander
    total_cards += sum(basics.values())
    for section in sections.values():
        total_cards += len(section)

    decklist = format_decklist(
        args.commander, sections, basics, targets, args.budget, total_cards,
        art_theme=args.art_theme,
    )

    if args.print_list:
        print("\n" + decklist)
        return

    if args.output:
        out_dir = os.path.dirname(args.output)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(decklist)
        print(f"\nDraft written to: {args.output}")
    else:
        print("\n" + decklist)

    print(f"\n{total_cards}/100 cards generated.")
    if total_cards < 100:
        print(f"  ⚠ {100 - total_cards} slots unfilled — EDHREC pool may be thin for this commander.")
        print(f"    AI will fill remaining slots manually during review.")
    print(f"  Next: AI reviews draft, slots non-negotiables, then runs validate-deck.py.")


if __name__ == "__main__":
    main()
