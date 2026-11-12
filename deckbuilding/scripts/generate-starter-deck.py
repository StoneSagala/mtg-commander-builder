#!/usr/bin/env python3
"""
generate-starter-deck.py — Auto-generate a 100-card Commander draft from EDHREC + Scryfall.

Fetches EDHREC's pre-categorized card pool, calculates target slot counts from the
bracket baseline and strategy overrides, and auto-selects cards by synergy score.
Outputs a provisional draft with explicit missing slots. The AI then reviews and swaps in
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


from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "_shared"))
from data_sources import commander_pool, slugify, request_json
from freshness import current_rules
from ratios import BRACKET_BASELINES, STRATEGY_OVERRIDES
from deck_budget import cents, price_cards, constrain_deck

SCRYFALL_BASE = "https://api.scryfall.com"
USER_AGENT = "MTGCommanderBuilder/0.2 (https://github.com/StoneSagala/mtg-commander-builder)"


COLOR_BASICS = {
    "W": "Plains", "U": "Island", "B": "Swamp", "R": "Mountain", "G": "Forest",
}

# Cards that go in every deck regardless of EDHREC ranking
UNIVERSAL_RAMP = ["Sol Ring", "Arcane Signet"]
UNIVERSAL_LANDS = ["Command Tower"]


# ─── EDHREC fetch ─────────────────────────────────────────────────────────────

def fetch_staples(name, strategies=(), partner=None):
    pool, commander, source = commander_pool(name, warn=lambda m: print(m, file=sys.stderr), strategies=strategies, partner=partner)
    return pool, commander, source


def fetch_art_cards_for_theme(art_keywords, color_identity, budget=None):
    """
    Fetch cards matching art keywords from Scryfall for art/flavor-themed decks.
    Uses Scryfall's art: illustration tag search. Returns list of card name strings.
    """
    parts = [f"art:{kw}" for kw in art_keywords]
    parts.append("id<=" + ("".join(color_identity).lower() or "c"))
    parts.append("-type:basic legal:commander")
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
            with urllib.request.urlopen(req, timeout=20) as resp:
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


# ─── Target calculation ───────────────────────────────────────────────────────

def calculate_targets(bracket, engine, game_plan, win_con):
    """Calculate adjusted slot targets from bracket baseline + strategy overrides."""
    baseline = BRACKET_BASELINES.get(bracket, BRACKET_BASELINES[3])
    targets = {key: (value[0] + value[1]) // 2 for key, value in baseline.items() if key != 'note'}
    for slug in [engine, game_plan, win_con]:
        for key, delta in STRATEGY_OVERRIDES.get(slug, {}).items():
            if key.endswith('_adj') and key[:-4] in targets:
                targets[key[:-4]] = max(0, targets[key[:-4]] + delta)
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
    used = set(commander_name if isinstance(commander_name, list) else [commander_name])
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
    remaining_interaction = targets["interaction"]
    fill_slot(sections, "Interaction",    used, staples, ["Removal", "Counterspells", "Protection"],  remaining_interaction)

    fill_slot(sections, "Tutors",         used, staples, ["Tutors"],                                  targets["tutors"])
    fill_slot(sections, "Win Conditions", used, staples, ["Win Conditions"],                          targets["win_cons"])

    total_non_land = (targets["ramp"] + targets["card_draw"] + targets["interaction"] +
                      targets["tutors"] + targets["win_cons"])
    commander_count = len(commander_name) if isinstance(commander_name, list) else 1
    theme_target = 100 - commander_count - targets["lands"] - total_non_land

    if art_cards:
        # Art theme mode: fill theme slots from art search results (sorted by CMC)
        art_pool = {"__art__": sorted(art_cards, key=lambda c: (c.get("cmc", 0), c["name"]))}
        fill_slot(sections, "Theme / Synergy", used, art_pool, ["__art__"], theme_target)
    else:
        # Standard mode: fill theme slots from EDHREC synergy categories
        theme_cats = [
            "Theme Candidates", "High Synergy", "Creatures", "Graveyard", "Self-Mill", "Enchantments",
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


def apply_total_budget(sections, basics, commanders, targets, identity, staples, budget):
    """Keep the chosen total optional and fill cheaper alternatives within it."""
    desired = {section: len(names) for section, names in sections.items()}
    basic_names = [COLOR_BASICS[c] for c in identity if c in COLOR_BASICS] or ['Wastes']
    names = commanders + basic_names + [n for cards in sections.values() for n in cards]
    prices = {c['name']: cents(c.get('price_usd')) for cards in staples.values() for c in cards}
    prices.update(price_cards(names))
    ceiling = cents(budget)
    # A player's budget determines when costly utility lands should become basics.
    per_slot = max(0, (ceiling - sum(prices.get(n) or 0 for n in commanders)) // max(1, 100 - len(commanders)))
    sections = {key: list(value) for key, value in sections.items()}
    sections['Utility Lands'] = [n for n in sections['Utility Lands'] if prices.get(n) is not None and prices[n] <= per_slot]
    basics = build_basics(sections, targets, identity)
    sections, report = constrain_deck(sections, basics, commanders, budget, prices)
    spent = int(round(report['estimated_total_usd'] * 100))
    used = set(commanders) | {n for cards in sections.values() for n in cards}
    categories = {'Ramp': ['Ramp'], 'Card Draw': ['Card Draw'], 'Interaction': ['Board Wipes', 'Removal', 'Counterspells', 'Protection'], 'Tutors': ['Tutors'], 'Win Conditions': ['Win Conditions'], 'Theme / Synergy': ['Theme Candidates', 'High Synergy']}
    for section, cats in categories.items():
        candidates = {card['name']: card for cat in cats for card in staples.get(cat, [])}
        for name in sorted(candidates, key=lambda n: (prices.get(n) is None, prices.get(n) or 0, n)):
            if len(sections[section]) >= desired[section]:
                break
            amount = prices.get(name)
            if name not in used and amount is not None and spent + amount <= ceiling:
                sections[section].append(name); used.add(name); spent += amount
    report['estimated_total_usd'] = spent / 100
    report['unfilled_slots'] = 100 - len(commanders) - sum(basics.values()) - sum(map(len, sections.values()))
    return sections, basics, report


# ─── Output ───────────────────────────────────────────────────────────────────

def format_decklist(commander_name, sections, basics, targets, budget, total_cards, art_theme=None, commanders=None):
    today = datetime.date.today().isoformat()
    lines = []
    lines.append(f"# {commander_name} — Commander")
    lines.append(f"# Theme: [fill in from brief]")
    lines.append(f"# Bracket: {targets.get('_bracket', '?')} | Avg CMC: TBD | Budget: {'No limit' if budget is None else '$' + str(budget)}")
    lines.append(f"# Date: {today}")
    if art_theme:
        lines.append(f"# ART THEME: {art_theme} — theme slots filled by art search, not EDHREC synergy")
    lines.append(f"# AUTO-GENERATED — review and swap non-negotiables from brief")
    lines.append("")

    lines.append("Commander:")
    for name in commanders or [commander_name]:
        lines.append(f"1 {name}")
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
    lines.append("## Draft Coverage (not legality validation)")
    lines.append(f"- Total: {total_cards}/100")
    lines.append(f"- Lands: {land_total} (target: {targets['lands']})")
    lines.append(f"- Ramp: {len(sections['Ramp'])} (target: {targets['ramp']})")
    lines.append(f"- Card Draw: {len(sections['Card Draw'])} (target: {targets['card_draw']})")
    lines.append(f"- Interaction: {len(sections['Interaction'])} (target: {targets['interaction']})")
    lines.append(f"- Tutors: {len(sections['Tutors'])} (target: {targets['tutors']})")
    lines.append(f"- Win Conditions: {len(sections['Win Conditions'])} (target: {targets['win_cons']})")
    lines.append(f"- Theme/Synergy: {len(sections['Theme / Synergy'])}")
    if budget is not None:
        lines.append(f"- Player-supplied total-deck budget: ${budget:.2f}")
    else:
        lines.append("- Budget: no limit specified by player")
    if total_cards < 100:
        lines.append(f"- ⚠ {100 - total_cards} slots unfilled — Provisional pool leaves gaps. Fill verified strategy packages manually.")

    lines.append("")
    lines.append("## AI Review Checklist")
    if art_theme:
        lines.append(f"- [ ] ART THEME MODE: theme slots filled by art:{art_theme} search — review for flavor fit")
        lines.append("- [ ] Structural slots use the verified provider pool — review roles and provenance")
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
    parser.add_argument("--partner", default=None, help="Second commander: supported Partner/Friends forever/Background pairing")
    parser.add_argument("--bracket", type=int, required=True, choices=[1, 2, 3, 4, 5])
    parser.add_argument("--engine", required=True,
                        help="Engine slug: graveyard, aristocrats, artifacts, enchantress, etc.")
    parser.add_argument("--game-plan", required=True, dest="game_plan",
                        help="Game plan slug: combo, control, go-wide, stax, etc.")
    parser.add_argument("--win-con", required=True, dest="win_con",
                        help="Win con slug: life-depletion, mill, poison, commander-damage, etc.")
    parser.add_argument("--budget", type=float, default=None,
                        help="Optional total deck budget in USD, including commanders and lands; omit for no limit")
    parser.add_argument("--art-theme", metavar="KEYWORDS", default=None, dest="art_theme",
                        help="Space-separated art keywords (e.g. 'smile balloon party'). "
                             "Theme slots filled by Scryfall art search instead of the standard strategy pool.")
    parser.add_argument("--output", metavar="PATH", default=None,
                        help="Write draft to this file path")
    parser.add_argument("--force", action="store_true", help="Explicitly allow replacing an existing output file")
    parser.add_argument("--print", action="store_true", dest="print_list",
                        help="Print to stdout instead of writing to file")
    args = parser.parse_args()

    if args.output and os.path.exists(args.output) and not args.force:
        parser.error("Output already exists. Keep the approved brief; choose a new path or explicitly use --force.")

    if args.budget is not None and cents(args.budget) is None:
        parser.error("Budget must be finite and nonnegative; omit --budget for no limit.")
    rules = current_rules()
    slug = slugify(args.commander)

    print(f"Fetching EDHREC staples for '{slug}'...")
    staples, commander, source = fetch_staples(args.commander, strategies=(args.engine, args.game_plan, args.win_con), partner=args.partner)
    commander_names = [c["name"] for c in commander["commanders"]]
    args.commander = commander["name"]
    color_identity = commander["color_identity"]

    print(f"  Color identity: {''.join(color_identity) or 'Colorless'}")
    cat_summary = ", ".join(f"{k}({len(v)})" for k, v in staples.items())
    print(f"  Categories: {cat_summary}")


    # Art theme: fetch art cards before building (if requested)
    art_cards = None
    if args.art_theme:
        art_keywords = args.art_theme.strip().split()
        print(f"\nArt theme mode: fetching cards with art:{' art:'.join(art_keywords)}...")
        art_cards = fetch_art_cards_for_theme(art_keywords, color_identity)
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
        commander_names, targets, staples, color_identity,
        art_cards=art_cards,
    )
    basics = build_basics(sections, targets, color_identity)

    budget_report = {"status": "unrestricted", "limit_usd": None}
    if args.budget is not None:
        sections, basics, budget_report = apply_total_budget(sections, basics, commander_names, targets, color_identity, staples, args.budget)

    total_cards = len(commander_names)
    total_cards += sum(basics.values())
    for section in sections.values():
        total_cards += len(section)

    decklist = format_decklist(
        args.commander, sections, basics, targets, args.budget, total_cards,
        art_theme=args.art_theme, commanders=commander_names,
    )

    decklist += f"\n\n## Data provenance\n- Source: {source}\n- Role assignment: Scryfall oracle-text heuristics; human review required.\n- Bracket and strategy require separate review. Rules checked: {rules['checked_at']}.\n"

    decklist += "\n\n## Player budget\n```json\n" + json.dumps(budget_report, indent=2) + "\n```\n"

    if args.print_list:
        print("\n" + decklist)
        return

    if args.output:
        out_dir = os.path.dirname(args.output)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        with open(args.output, "w" if args.force else "x", encoding="utf-8") as f:
            f.write(decklist)
        print(f"\nDraft written to: {args.output}")
    else:
        print("\n" + decklist)

    print(f"\n{total_cards}/100 cards generated.")
    if total_cards < 100:
        print(f"  ⚠ {100 - total_cards} slots unfilled — Provisional pool leaves strategy gaps; fill verified packages manually.")
        print(f"    AI will fill remaining slots manually during review.")
    print(f"  Next: AI reviews draft, slots non-negotiables, then runs validate-deck.py.")


if __name__ == "__main__":
    try:
        main()
    except (urllib.error.URLError, TimeoutError, ValueError) as error:
        print(f"Data source error: {error}. Check connections; do not infer commander age.", file=sys.stderr)
        sys.exit(1)
