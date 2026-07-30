#!/usr/bin/env python3
"""
intake.py — Commander deck ideation intake.

Smart intake that adapts to what you already know. Three paths:

  Quick   — Describe what you want in plain text. The script parses what you
             said and only asks about the gaps. Great when you already have a
             clear picture.

  Guided  — Step-by-step questions. Good for new players or when you genuinely
             don't know what you want yet. Covers all five starting points:
             commander first, playstyle first, card/combo first, not sure, or
             surprise me.

  Surprise — Hands off to discover-playstyle.py for a fully random deck.

Usage:
    python Ideation/scripts/intake.py
"""

import sys
import re

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')


# ─── UI helpers ───────────────────────────────────────────────────────────────

def hr():
    print("=" * 60)


def blank():
    print()


def ask(prompt: str, allow_skip: bool = False) -> str:
    blank()
    print(prompt)
    if allow_skip:
        print("(press Enter to skip)")
    return input("> ").strip()


def ask_choice(prompt: str, options: list, allow_skip: bool = False) -> str:
    """Numbered choice menu. Returns the full option string chosen."""
    blank()
    print(prompt)
    for i, opt in enumerate(options, 1):
        print(f"  {i} — {opt}")
    if allow_skip:
        print("  (press Enter to skip)")
    while True:
        raw = input("> ").strip()
        if allow_skip and raw == "":
            return ""
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return options[int(raw) - 1]
        msg = f"Enter a number 1–{len(options)}."
        if allow_skip:
            msg += " Or press Enter to skip."
        print(msg)


# ─── Free-text parser ─────────────────────────────────────────────────────────

# Guild / color → canonical color string
COLOR_KEYWORDS = {
    "white": "white", "blue": "blue", "black": "black", "red": "red", "green": "green",
    "colorless": "colorless",
    "azorius": "white/blue",   "dimir": "blue/black",   "rakdos": "black/red",
    "gruul": "red/green",      "selesnya": "green/white","orzhov": "white/black",
    "izzet": "blue/red",       "golgari": "black/green", "boros": "red/white",
    "simic": "green/blue",
    "esper": "white/blue/black","grixis": "blue/black/red","jund": "black/red/green",
    "naya": "red/green/white",  "bant": "green/white/blue",
    "abzan": "white/black/green","jeskai": "blue/red/white","sultai": "black/green/blue",
    "mardu": "red/white/black", "temur": "green/blue/red",
    "five color": "WUBRG",     "5 color": "WUBRG",      "wubrg": "WUBRG",
}

# Patterns that indicate specific game plans
GAME_PLAN_PATTERNS = [
    (r"\bcombo\b",                      "Combo"),
    (r"\bcontrol\b",                    "Control"),
    (r"\bgo.?wide\b|\bflood\b",         "Go Wide"),
    (r"\btokens?\b",                    "Go Wide"),
    (r"\bgo.?tall\b|\bvoltron\b",       "Go Tall"),
    (r"\bstax\b|\btax\b|\bdenial\b",    "Stax"),
    (r"\bpolitics?\b|\bpolitical\b",    "Politics"),
    (r"\bburn\b",                       "Burn"),
]

WIN_CON_PATTERNS = [
    (r"\bmill\b|\blibrary\b.*depletion\b|\bempty.*librar",  "Library depletion"),
    (r"\bpoison\b|\binfect\b|\bproliferate\b",              "Poison counters"),
    (r"\bcommander damage\b|\b21.*damage\b",                "Commander damage"),
    (r"\bdrain\b|\blife loss\b|\blife depletion\b|\b0 life\b", "Life depletion"),
    (r"\balternate win\b|\bthassa.?s oracle\b|\bfelidar\b|\bmaze.?s end\b", "Alternate win condition"),
]

INTERACTION_PATTERNS = [
    (r"\breactive\b|\bcounterspell\b|\binteract\b",  "Reactive"),
    (r"\bproactive\b|\baggressive\b|\bfast\b",       "Proactive"),
    (r"\bbalanced\b|\bsome interaction\b",           "Balanced"),
]

BRACKET_KEYWORDS = {
    r"bracket\s*1\b|exhibition\b|ultra.?casual\b":              "1",
    r"bracket\s*2\b|precon\b|pre.?con\b":                       "2",
    r"bracket\s*3\b|upgraded\b|synergistic\b":                  "3",
    r"bracket\s*4\b|optimized\b|high.?power\b":                 "4",
    r"bracket\s*5\b|\bcedh\b|competitive\b|cEDH\b":             "5",
}


def parse_free_text(text: str) -> dict:
    """
    Extract known fields from a free-text description.
    Returns a dict of detected values (empty string = not detected).
    """
    t = text  # preserve original for storage
    tl = text.lower()

    detected = {
        "raw": text,
        "colors": "",
        "bracket": "",
        "budget": "",
        "game_plan": "",
        "win_con": "",
        "interaction": "",
        "art_theme": "",
    }

    # Budget — match $N, $NNN, "under $X", "X dollar"
    m = re.search(r'\$\s*(\d+)', text)
    if m:
        detected["budget"] = f"${m.group(1)}"
    else:
        m = re.search(r'(\d+)\s*dollar', tl)
        if m:
            detected["budget"] = f"${m.group(1)}"

    # Bracket
    for pattern, value in BRACKET_KEYWORDS.items():
        if re.search(pattern, tl):
            detected["bracket"] = value
            break

    # Colors / guild names
    for keyword, value in COLOR_KEYWORDS.items():
        if re.search(rf'\b{re.escape(keyword)}\b', tl):
            detected["colors"] = value
            break

    # Game plan
    for pattern, value in GAME_PLAN_PATTERNS:
        if re.search(pattern, tl):
            detected["game_plan"] = value
            break

    # Win condition
    for pattern, value in WIN_CON_PATTERNS:
        if re.search(pattern, tl):
            detected["win_con"] = value
            break

    # Interaction style
    for pattern, value in INTERACTION_PATTERNS:
        if re.search(pattern, tl):
            detected["interaction"] = value
            break

    # Art theme — explicit mention
    m = re.search(r'art[- ]?them(?:e|ed)[^\.\,]*|only cards.*?art|art.*?only', tl)
    if m:
        detected["art_theme"] = m.group(0)

    return detected


def show_parsed(detected: dict) -> list:
    """Print what was understood. Returns list of field names that were detected."""
    found = []
    field_labels = {
        "colors":     "Colors",
        "bracket":    "Bracket",
        "budget":     "Budget",
        "game_plan":  "Game plan",
        "win_con":    "Win condition",
        "interaction":"Interaction",
        "art_theme":  "Art theme",
    }
    hits = [(label, detected[key]) for key, label in field_labels.items() if detected.get(key)]
    if not hits:
        return []
    blank()
    print("Understood from your description:")
    for label, value in hits:
        print(f"  {label}: {value}")
        found.append(label)
    return found


# ─── Required fields gap-filler ───────────────────────────────────────────────

def fill_bracket(data: dict):
    if data.get("bracket"):
        return
    raw = ask_choice(
        "Power level of your pod:",
        [
            "1 — Exhibition: ultra-casual, unmodified precons",
            "2 — Core: precon-level with light upgrades, no combos",
            "3 — Upgraded: synergistic decks, light combos OK",
            "4 — Optimized: high power, tutors, fast mana",
            "5 — cEDH: competitive, find-and-execute one win line",
        ],
    )
    data["bracket"] = raw[0]


def fill_budget(data: dict):
    if data.get("budget"):
        return
    data["budget"] = ask("Budget ceiling? (e.g. $100, $300, no limit)", allow_skip=True) or "not specified"


def fill_win_con(data: dict):
    if data.get("win_con"):
        return
    raw = ask_choice(
        "How do you want to WIN?",
        [
            "Life depletion — reduce opponents to 0 life",
            "Commander damage — 21 combat damage with your commander",
            "Library depletion — mill opponents out",
            "Poison counters — 10 poison",
            "Alternate win condition — a specific card (Thassa's Oracle, Approach, etc.)",
            "Not sure yet — let the commander and theme guide it",
        ],
    )
    data["win_con"] = raw.split(" — ")[0]
    if data["win_con"] == "Alternate win condition":
        card = ask("Which alternate win condition card?", allow_skip=True)
        if card:
            data["alt_win_con_card"] = card


def fill_game_plan(data: dict):
    if data.get("game_plan"):
        return
    raw = ask_choice(
        "How do you want to PLAY turn by turn?",
        [
            "Go Wide — flood the board, win through numbers",
            "Go Tall — one massive threat, win through power",
            "Combo — assemble specific pieces for a deterministic win",
            "Burn — deal damage through spells and triggers",
            "Stax — slow opponents with taxes and denial",
            "Control — answer threats reactively, win from dominance",
            "Politics — deals and table dynamics",
            "Not sure yet",
        ],
    )
    data["game_plan"] = raw.split(" — ")[0]


def fill_interaction(data: dict):
    if data.get("interaction"):
        return
    raw = ask_choice(
        "Interaction style:",
        [
            "Reactive — answer threats as they come (removal, counters, wipes)",
            "Proactive — focus on your gameplan, let opponents deal with you",
            "Balanced — some interaction, not the deck's identity",
        ],
    )
    data["interaction"] = raw.split(" — ")[0]


def fill_success(data: dict):
    if data.get("success"):
        return
    data["success"] = ask(
        "What does a great game look like with this deck?\n"
        "When you imagine the perfect game — what happens?"
    )


def fill_optional(data: dict):
    """Ask optional fields. User can skip any of these."""
    if not data.get("colors"):
        data["colors"] = ask(
            "Color preferences or restrictions?\n"
            "e.g. 'want black', 'no white', 'open to anything'",
            allow_skip=True,
        )
    if not data.get("house_rules"):
        data["house_rules"] = ask(
            "Any house rules in your pod? (e.g. 'no infinite combos', 'none')",
            allow_skip=True,
        )
    if not data.get("include"):
        data["include"] = ask(
            "Cards you definitely want in the deck?",
            allow_skip=True,
        )
    if not data.get("exclude"):
        data["exclude"] = ask(
            "Cards you refuse to play or your group has informally banned?",
            allow_skip=True,
        )
    if not data.get("art_theme"):
        data["art_theme"] = ask(
            "Art or flavor theme? Leave blank for standard synergy selection.\n"
            "e.g. 'smile', 'balloon party', 'dungeon torch skeleton' — uses Scryfall art search",
            allow_skip=True,
        )


# ─── Paths ────────────────────────────────────────────────────────────────────

def path_quick() -> dict:
    """
    Free-text first. Parse what was stated, ask only the gaps.
    Best for players who already know what they want.
    """
    description = ask(
        "Tell me what you're thinking.\n"
        "The more you share, the fewer questions I'll ask.\n\n"
        "e.g. 'graveyard combo deck, bracket 3, $200, kill everyone with Massacre Wurm,\n"
        "      reactive, blue/black, no infinite combos'"
    )

    data = parse_free_text(description)

    # Use the raw description as the theme/vibe for the AI
    data["theme"] = description
    data.setdefault("commander", "")
    data.setdefault("combo", "")
    data.setdefault("house_rules", "")
    data.setdefault("include", "")
    data.setdefault("exclude", "")
    data.setdefault("alt_win_con_card", "")
    data.setdefault("success", "")
    data["flow"] = "A"  # default; AI may re-classify based on content

    show_parsed(data)

    blank()
    print("A few more things:")

    # Required gaps
    fill_bracket(data)
    fill_budget(data)
    fill_win_con(data)
    fill_game_plan(data)
    fill_interaction(data)
    fill_success(data)

    # Optional — only ask what wasn't parsed
    blank()
    print("Optional — press Enter to skip any of these:")
    fill_optional(data)

    return data


def path_guided() -> dict:
    """
    Step-by-step questions. Covers all five starting points.
    """
    data = {
        "commander": "", "theme": "", "combo": "",
        "colors": "", "bracket": "", "budget": "",
        "house_rules": "", "include": "", "exclude": "",
        "win_con": "", "alt_win_con_card": "", "game_plan": "",
        "interaction": "", "success": "", "art_theme": "",
        "flow": "A",
    }

    entry = ask_choice(
        "Where are you starting from?",
        [
            "I have a commander in mind",
            "I have a playstyle or theme in mind",
            "I have a specific card or combo I want to build around",
            "Not sure — help me figure it out",
            "Surprise me",
        ],
    )

    if entry.startswith("I have a commander"):
        data["commander"] = ask("Which commander?")
        data["flow"] = "B"

    elif entry.startswith("I have a specific"):
        data["combo"] = ask(
            "Describe the card or combo and how you want to win with it:\n"
            "e.g. 'drop multiple Massacre Wurms in one turn to wipe boards and drain life'"
        )
        data["flow"] = "C"

    elif entry.startswith("Not sure"):
        blank()
        print("Run the playstyle discovery questionnaire:")
        blank()
        print("    python Ideation/scripts/discover-playstyle.py")
        blank()
        print("It takes 2 minutes and requires no MTG knowledge.")
        print("Paste the Playstyle Profile output back here to continue.")
        blank()
        profile = ask(
            "Paste your Playstyle Profile here, or press Enter to let the AI\n"
            "guide you from scratch.",
            allow_skip=True,
        )
        data["theme"] = profile
        data["flow"] = "D"

    elif entry.startswith("Surprise"):
        blank()
        print("Run:")
        blank()
        print("    python Ideation/scripts/discover-playstyle.py --surprise-me")
        blank()
        print("Paste the output here and the AI will build from it.")
        sys.exit(0)

    else:  # playstyle / theme
        data["theme"] = ask(
            "Describe the vibe, mechanic, or fantasy:\n"
            "e.g. 'graveyard value', 'tokens and sacrifice', 'storm off', 'big creatures'"
        )
        data["flow"] = "A"

    # Universal questions
    data["colors"] = ask(
        "Color preferences or restrictions?\n"
        "e.g. 'want black', 'no white', 'open to anything'",
        allow_skip=True,
    )

    fill_bracket(data)
    fill_budget(data)

    data["house_rules"] = ask(
        "House rules in your pod? (e.g. 'no infinite combos', 'none')",
        allow_skip=True,
    )
    data["include"] = ask("Cards you definitely want in the deck?", allow_skip=True)
    data["exclude"] = ask("Cards you refuse to play?", allow_skip=True)

    fill_win_con(data)
    fill_game_plan(data)
    fill_interaction(data)

    data["art_theme"] = ask(
        "Art or flavor theme? Leave blank for standard synergy selection.\n"
        "e.g. 'smile', 'dungeon torch skeleton', 'balloon party confetti'\n"
        "Uses Scryfall's illustration tag search to fill theme slots.",
        allow_skip=True,
    )

    fill_success(data)

    return data


# ─── Output ───────────────────────────────────────────────────────────────────

def print_summary(data: dict):
    blank()
    hr()
    print("  INTAKE COMPLETE — paste this to the AI")
    hr()
    blank()

    lines = ["## Intake Summary", ""]

    if data.get("commander"):
        lines.append(f"- **Commander:** {data['commander']}")
    if data.get("theme"):
        lines.append(f"- **Theme / vibe:** {data['theme']}")
    if data.get("combo"):
        lines.append(f"- **Win condition / combo:** {data['combo']}")
    if data.get("colors"):
        lines.append(f"- **Color preferences:** {data['colors']}")

    lines.append(f"- **Bracket:** {data.get('bracket', 'not specified')}")
    lines.append(f"- **Budget:** {data.get('budget', 'not specified')}")
    lines.append(f"- **House rules:** {data.get('house_rules') or 'none'}")
    lines.append(f"- **Cards to include:** {data.get('include') or 'none'}")
    lines.append(f"- **Cards to avoid:** {data.get('exclude') or 'none'}")

    win_con = data.get("win_con", "not specified")
    alt = data.get("alt_win_con_card", "")
    lines.append(f"- **Win condition:** {win_con}" + (f" ({alt})" if alt else ""))

    lines.append(f"- **Game plan:** {data.get('game_plan', 'not specified')}")
    lines.append(f"- **Interaction style:** {data.get('interaction', 'not specified')}")

    if data.get("art_theme"):
        lines.append(f"- **Art theme:** {data['art_theme']}")

    lines.append(f"- **Success looks like:** {data.get('success', 'not specified')}")
    lines.append(f"- **Flow:** {data.get('flow', 'A')}")

    print("\n".join(lines))
    blank()


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    hr()
    print("  MTG Commander — Deck Ideation Intake")
    hr()
    blank()
    print("Three ways to start:")
    print("  Quick   — Describe what you want, I'll only ask about the gaps")
    print("  Guided  — Step-by-step questions (good if you're not sure yet)")
    print("  Surprise — Random deck via discover-playstyle.py")

    mode = ask_choice(
        "How would you like to start?",
        [
            "Quick — describe it, I'll fill the gaps",
            "Guided — step-by-step questions",
            "Surprise me",
        ],
    )

    if mode.startswith("Surprise"):
        blank()
        print("Run:")
        blank()
        print("    python Ideation/scripts/discover-playstyle.py --surprise-me")
        blank()
        print("Paste the output here and the AI will build from it.")
        return

    if mode.startswith("Quick"):
        data = path_quick()
    else:
        data = path_guided()

    print_summary(data)


if __name__ == "__main__":
    main()
