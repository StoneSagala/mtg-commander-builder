#!/usr/bin/env python3
"""
goldfish.py — Scryfall-powered Monte Carlo goldfish simulator for Commander decks.

Fetches real card data (oracle text, CMC, produced mana) from Scryfall on startup,
classifies every card's role, then simulates actual Magic decisions per turn:
  - Mulligan with deck-aware thresholds (rock density → min land count)
  - Ramp resolves and adds real mana production to the battlefield
  - Draw spells actually draw cards from the library
  - Mill spells move cards to the graveyard each turn
  - Tutors fetch the optimal target based on game state priority
  - Runs until win condition is assembled (no fixed turn cap, max T30 safety)

Metrics:
  - Flood / screw split (why hands were shipped)
  - Mana development per turn (lands + rocks)
  - Ramp and draw arrival timing
  - Dead turns (mana available, nothing affordable to cast)
  - Key piece arrival (hand or GY mode)
  - Win turn distribution (avg, T5/T7/T9/T12/T15/ever%)
  - Bottleneck piece (last piece to arrive in winning games)
  - Stuck cards (drawn frequently, never cast)
  - Specific fix recommendations

Usage:
    python optimization/scripts/goldfish.py --file araumi-draft.md
    python optimization/scripts/goldfish.py --file brew.md --gy-cards "Massacre Wurm,Archon of Cruelty"
    python optimization/scripts/goldfish.py --file brew.md --keep-if "Sol Ring" --win-mana 8
    python optimization/scripts/goldfish.py --file brew.md --games 2000 --format json
"""

import sys
import json
import re
import random
import time
import argparse
import urllib.request
import urllib.parse
import urllib.error
from collections import defaultdict
from typing import Optional, List, Dict, Tuple

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

SCRYFALL_BASE = "https://api.scryfall.com"
USER_AGENT    = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
MAX_TURNS     = 30  # safety ceiling

BASIC_LANDS = {
    "Plains", "Island", "Swamp", "Mountain", "Forest", "Wastes",
    "Snow-Covered Plains", "Snow-Covered Island", "Snow-Covered Swamp",
    "Snow-Covered Mountain", "Snow-Covered Forest",
}

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
    "self-mill":       "mill",
    "reanimation":     "reanimation",
}

WORD_TO_NUM: Dict[str, int] = {
    "a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4,
    "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
}

GY_KEYWORDS = [
    "encore", "reanimate", "unearth", "dredge", "delve", "escape", "flashback",
    "from a graveyard", "from your graveyard to the battlefield",
    "return target creature card from your graveyard",
]

# Parasitic deck detection: cards that require opponents to function
PARASITIC_KEYWORDS = [
    "gain control", "gains control", "you control target",
    "for each opponent", "each opponent loses", "each opponent sacrifices",
    "target player's library", "steal", "exchange control",
    "target opponent", "an opponent controls",
]

# Deck types and what they mean for simulation
DECK_TYPE_AUTO    = "auto"      # detect from card data
DECK_TYPE_COMBO   = "combo"     # deterministic win condition — full metrics
DECK_TYPE_GY      = "gy"        # graveyard assembly — GY metrics
DECK_TYPE_PARASITIC = "parasitic"  # requires opponents — threat deployment only
DECK_TYPE_FUN     = "fun"       # themed/casual — mana/curve only, no win pressure


# ─── Deck Parser ──────────────────────────────────────────────────────────────

def parse_decklist(filepath: str) -> Tuple[List[str], Dict[str, List[str]], str]:
    """
    Parse a brew/draft .md file.
    Returns (deck, sections, commander).
    deck     — list of card name strings (99-card library, no commander)
    sections — dict of {role: [name, ...]}
    commander — str or ""
    """
    deck: List[str] = []
    sections: Dict[str, List[str]] = defaultdict(list)
    commander = ""
    current_role: Optional[str] = None
    in_brief = False

    with open(filepath, encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()

            if line.startswith("## Brief"):
                in_brief = True
                continue
            if in_brief:
                if line.startswith("## ") and "Brief" not in line:
                    in_brief = False
                else:
                    m = re.match(r'\*{0,2}Commander:\*{0,2}\s*(.+)', line, re.IGNORECASE)
                    if m and not commander:
                        raw_val = m.group(1).strip()
                        commander = re.split(r'\s*[\(\—–-]', raw_val)[0].strip()
                    continue

            if not line or line.startswith('#') or line == '---':
                continue

            m_header = re.match(r'^([A-Za-z][A-Za-z /\-]*?)(?:\s*\(\d+\))?\s*:\s*$', line)
            if m_header:
                header = m_header.group(1).strip().lower()
                current_role = "commander" if header == "commander" else SECTION_ROLE_MAP.get(header, "other")
                continue

            m_card = re.match(r'^(\d+)\s+(.+)$', line)
            if m_card:
                qty  = int(m_card.group(1))
                name = m_card.group(2).strip()
            elif re.match(r'^[A-Z]', line) and current_role == "commander":
                qty, name = 1, line
            else:
                continue

            name = re.sub(r'\s*\[[^\]]+\]$', '', name).strip().strip('*').strip()

            if current_role == "commander":
                if not commander:
                    commander = name
            else:
                role = current_role or "other"
                for _ in range(qty):
                    deck.append(name)
                    sections[role].append(name)

    return deck, dict(sections), commander


# ─── Scryfall Batch Fetch ──────────────────────────────────────────────────────

def _post_json(url: str, payload: dict) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, method="POST",
        headers={"User-Agent": USER_AGENT, "Content-Type": "application/json", "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _get_json(url: str) -> dict:
    time.sleep(0.05)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _extract_card_fields(card: dict) -> dict:
    """Normalize a Scryfall card object into simulation fields."""
    oracle = card.get("oracle_text", "") or ""
    mana_cost = card.get("mana_cost", "") or ""
    # Double-faced cards: data lives on card_faces[0]
    if not oracle and "card_faces" in card:
        oracle = card["card_faces"][0].get("oracle_text", "") or ""
    if not mana_cost and "card_faces" in card:
        mana_cost = card["card_faces"][0].get("mana_cost", "") or ""
    return {
        "cmc":           float(card.get("cmc", 0) or 0),
        "type_line":     card.get("type_line", "") or "",
        "oracle_text":   oracle,
        "mana_cost":     mana_cost,
        "colors":        card.get("colors", []) or [],
        "produced_mana": card.get("produced_mana", []) or [],
        "price":         float((card.get("prices", {}) or {}).get("usd") or 0),
    }


_EMPTY_CARD = {"cmc": 3.0, "type_line": "", "oracle_text": "", "mana_cost": "", "colors": [], "produced_mana": [], "price": 0.0}


def fetch_card_data(names: List[str]) -> Dict[str, dict]:
    """
    Batch fetch Scryfall data. Returns {name: fields_dict}.
    Uses /cards/collection (75 per call), falls back to /cards/named for not_found.
    """
    unique = list(set(names))
    result: Dict[str, dict] = {}
    not_found: List[str] = []

    for i in range(0, len(unique), 75):
        chunk = unique[i:i+75]
        try:
            time.sleep(0.1)
            resp = _post_json(
                f"{SCRYFALL_BASE}/cards/collection",
                {"identifiers": [{"name": n} for n in chunk]},
            )
            for card in resp.get("data", []):
                result[card.get("name", "")] = _extract_card_fields(card)
            for nf in resp.get("not_found", []):
                not_found.append(nf.get("name", ""))
        except Exception:
            not_found.extend(chunk)

    for name in not_found:
        try:
            card = _get_json(f"{SCRYFALL_BASE}/cards/named?exact={urllib.parse.quote(name)}")
            result[name] = _extract_card_fields(card)
        except Exception:
            result[name] = dict(_EMPTY_CARD)

    return result


# ─── Card Classifier ──────────────────────────────────────────────────────────

def _count_add_mana(oracle: str) -> int:
    """Count mana symbols in 'Add {X}{Y}' clauses, or parse 'add one/two mana' text."""
    matches = re.findall(r'[Aa]dd\s+((?:\{[^}]+\}\s*)+)', oracle)
    if matches:
        return max(len(re.findall(r'\{[^}]+\}', m)) for m in matches)
    m = re.search(r'[Aa]dd\s+(one|two|three|four|five)\s+mana', oracle)
    if m:
        return WORD_TO_NUM.get(m.group(1).lower(), 1)
    return 0


def _parse_draw_count(oracle: str) -> int:
    m = re.search(r'draw\s+(a card|an additional card|(\w+)\s+cards?)', oracle, re.IGNORECASE)
    if not m:
        return 0
    full = m.group(0).lower()
    if "a card" in full or "an additional" in full:
        return 1
    word = (m.group(2) or "").lower()
    if word.isdigit():
        return min(int(word), 7)
    return WORD_TO_NUM.get(word, 2)


def _parse_mill_count(oracle: str) -> int:
    m = re.search(r'mill\s+(\w+)', oracle, re.IGNORECASE)
    if not m:
        m = re.search(r'put the top\s+(\w+)\s+cards?\s+of[^.]+graveyard', oracle, re.IGNORECASE)
    if not m:
        return 0
    word = m.group(1).lower()
    if word.isdigit():
        return int(word)
    return WORD_TO_NUM.get(word, 3)


def _parse_tutor_restriction(oracle: str) -> Optional[str]:
    ol = oracle.lower()
    for keyword, restriction in [
        ("creature card", "Creature"), ("land card", "Land"), ("basic land", "Land"),
        ("artifact card", "Artifact"), ("enchantment card", "Enchantment"),
        ("instant or sorcery", "Instant"), ("instant card", "Instant"),
        ("sorcery card", "Sorcery"), ("planeswalker card", "Planeswalker"),
    ]:
        if keyword in ol:
            return restriction
    return None  # any card


def _parse_tutor_dest(oracle: str) -> str:
    ol = oracle.lower()
    if "search your library" in ol:
        if "graveyard" in ol and "battlefield" not in ol and "your hand" not in ol:
            return "gy"
        if "top of" in ol and "library" in ol:
            return "top"
        if "onto the battlefield" in ol:
            return "battlefield"
    return "hand"


def _colors_from_mana_cost(mana_cost: str) -> List[str]:
    colors = []
    for s in re.findall(r'\{([^}]+)\}', mana_cost):
        if s in 'WUBRG':
            colors.append(s)
        elif '/' in s:
            parts = s.split('/')
            for p in parts:
                if p in 'WUBRG':
                    colors.append(p)
                    break
    return colors


def classify_card(name: str, data: dict, section_role: Optional[str] = None) -> dict:
    """
    Classify a card and extract simulation-relevant properties.
    section_role (from deck file headers) takes precedence for role assignment.
    """
    oracle    = data.get("oracle_text", "") or ""
    type_line = data.get("type_line", "")    or ""
    cmc       = float(data.get("cmc", 0)     or 0)
    mana_cost = data.get("mana_cost", "")   or ""
    ol        = oracle.lower()
    tl        = type_line.lower()

    result = {
        "role":              "other",
        "cmc":               cmc,
        "mana_produced":     0,
        "draw_count":        0,
        "mill_count":        0,
        "is_tutor":          False,
        "tutor_dest":        "hand",
        "tutor_restriction": None,
        "colors_needed":     _colors_from_mana_cost(mana_cost),
        "produced_colors":   data.get("produced_mana", []) or [],
        "is_land":           "land" in tl,
        "is_permanent":      any(t in tl for t in ("creature", "artifact", "enchantment", "land", "planeswalker")),
        "is_artifact":       "artifact" in tl,
    }

    # Land — return early
    if "land" in tl:
        result["role"] = "land"
        return result

    # Tutor detection
    if "search your library" in ol:
        result["is_tutor"]          = True
        result["tutor_dest"]        = _parse_tutor_dest(oracle)
        result["tutor_restriction"] = _parse_tutor_restriction(oracle)
        if "land" in ol and "battlefield" in ol:
            # Land fetch = ramp
            result["role"] = "ramp"
            result["mana_produced"] = 1
        else:
            result["role"] = "tutor"

    # Ramp: produces mana
    add_mana = _count_add_mana(oracle)
    if add_mana > 0:
        result["role"] = "ramp"
        result["mana_produced"] = add_mana

    # Draw
    draw_n = _parse_draw_count(oracle)
    if draw_n > 0:
        result["draw_count"] = draw_n
        if result["role"] == "other":
            result["role"] = "card_draw"

    # Mill
    mill_n = _parse_mill_count(oracle)
    if mill_n > 0:
        result["mill_count"] = mill_n
        if result["role"] == "other":
            result["role"] = "mill"

    # High-CMC catch-all → probable win con
    if cmc >= 7 and result["role"] == "other":
        result["role"] = "win_con"

    # Section header overrides (most reliable signal)
    if section_role == "win_cons":
        result["role"] = "win_con"
    elif section_role == "ramp" and result["role"] not in ("land", "tutor"):
        result["role"] = "ramp"
        if result["mana_produced"] == 0:
            result["mana_produced"] = 1
    elif section_role == "card_draw" and result["role"] == "other":
        result["role"] = "card_draw"
        if result["draw_count"] == 0:
            result["draw_count"] = 2
    elif section_role == "tutors" and not result["is_tutor"]:
        result["is_tutor"] = True
        if result["role"] not in ("ramp", "land"):
            result["role"] = "tutor"
    elif section_role == "mill":
        result["role"] = "mill"
        if result["mill_count"] == 0:
            result["mill_count"] = 3

    return result


# ─── Deck Profile ─────────────────────────────────────────────────────────────

def build_profile(
    deck: List[str], sections: Dict[str, List[str]],
    card_data: Dict[str, dict], classified: Dict[str, dict],
    key_hand_override: List[str], key_gy_override: List[str],
    keep_if_override: List[str], win_mana_override: Optional[int],
) -> dict:
    """Build deck profile from classified card data."""

    unique = list(set(deck))
    lands, ramp, draw, tutors, win_cons, mill_cards, other = [], [], [], [], [], [], []

    for name in unique:
        role = classified.get(name, {}).get("role", "other")
        if   role == "land":      lands.append(name)
        elif role == "ramp":      ramp.append(name)
        elif role == "card_draw": draw.append(name)
        elif role == "tutor":     tutors.append(name)
        elif role == "win_con":   win_cons.append(name)
        elif role == "mill":      mill_cards.append(name)
        else:                     other.append(name)

    # Section-header win_cons are authoritative — add any missing ones
    for name in set(sections.get("win_cons", [])):
        if name not in win_cons:
            win_cons.append(name)
            if name in other:
                other.remove(name)

    # Tutors from section header
    for name in set(sections.get("tutors", [])):
        if name not in tutors and name not in ramp:
            tutors.append(name)

    rock_count = sum(
        1 for n in ramp
        if classified.get(n, {}).get("is_artifact")
    )

    non_land_cmcs = [classified[n]["cmc"] for n in unique if n not in lands and n in classified]
    avg_cmc = round(sum(non_land_cmcs) / len(non_land_cmcs), 2) if non_land_cmcs else 3.0

    # GY mode: reanimation section or ≥2 cards with GY keywords
    gy_card_count = sum(
        1 for n in unique
        if any(kw in (card_data.get(n, {}).get("oracle_text", "") or "").lower() for kw in GY_KEYWORDS)
    )
    gy_mode = gy_card_count >= 2 or bool(sections.get("reanimation")) or bool(sections.get("encore synergy"))

    # Parasitic deck detection: counts cards relying on opponents
    parasitic_count = sum(
        1 for n in unique
        if any(kw in (card_data.get(n, {}).get("oracle_text", "") or "").lower()
               for kw in PARASITIC_KEYWORDS)
    )
    is_parasitic = parasitic_count >= 5

    # Mill rate estimate (avg mill per turn once a mill permanent is active)
    avg_mill = 0.0
    if mill_cards:
        total_mill = sum(classified.get(n, {}).get("mill_count", 0) for n in mill_cards)
        avg_mill = total_mill / len(mill_cards)

    min_lands_keep = 1 if rock_count >= 6 else 2

    # Key cards
    key_hand = key_hand_override if key_hand_override else list(win_cons)
    key_gy   = key_gy_override

    # Keep-if: cheap mana rocks (auto if not specified)
    if keep_if_override:
        keep_if = keep_if_override
    else:
        keep_if = [
            n for n in ramp
            if classified.get(n, {}).get("cmc", 99) <= 2
            and classified.get(n, {}).get("is_artifact")
        ][:3]

    # Win mana
    if win_mana_override:
        win_mana = win_mana_override
    elif key_gy:
        # GY mode: need mana for the reanimation trigger (e.g., encore cost)
        win_mana = max(
            (int(classified.get(n, {}).get("cmc", 5)) for n in key_gy if n in classified),
            default=6
        ) + 3  # +3 for encore/reanimate overhead
    elif win_cons:
        win_mana = max(int(classified.get(n, {}).get("cmc", 5)) for n in win_cons if n in classified)
    else:
        win_mana = 6

    land_count = sum(1 for n in deck if n in set(lands))

    # Threat CMC for parasitic decks: lowest-CMC win con (first impactful spell)
    threat_cmc = min(
        (int(classified.get(n, {}).get("cmc", 99)) for n in win_cons if n in classified),
        default=5
    ) if win_cons else 5

    return {
        "lands":          lands,
        "ramp":           ramp,
        "draw":           draw,
        "tutors":         tutors,
        "win_cons":       win_cons,
        "mill_cards":     mill_cards,
        "other":          other,
        "avg_cmc":        avg_cmc,
        "rock_count":     rock_count,
        "avg_mill":       avg_mill,
        "gy_mode":        gy_mode,
        "is_parasitic":   is_parasitic,
        "parasitic_count": parasitic_count,
        "threat_cmc":     threat_cmc,
        "min_lands_keep": min_lands_keep,
        "key_hand":       key_hand,
        "key_gy":         key_gy,
        "keep_if":        keep_if,
        "win_mana":       win_mana,
        "land_count":     land_count,
    }


# ─── Mulligan Engine ──────────────────────────────────────────────────────────

def evaluate_hand(hand: List[str], profile: dict, classified: Dict[str, dict]) -> Tuple[bool, str]:
    land_set = set(profile["lands"])
    keep_if  = set(profile["keep_if"])
    land_count = sum(1 for c in hand if c in land_set)

    if any(c in keep_if for c in hand) and land_count >= 1:
        return True, "keep"

    if land_count < profile["min_lands_keep"]:
        return False, "screw"
    if land_count > 5:
        return False, "flood"

    # Castability: can we play something by T3?
    threshold = min(3, land_count + 1)
    castable = [c for c in hand if c not in land_set and classified.get(c, {}).get("cmc", 99) <= threshold]
    if not castable and land_count < 3:
        return False, "screw"

    return True, "keep"


def london_mulligan(library: List[str], profile: dict, classified: Dict[str, dict]):
    """
    London mulligan. Returns (hand, remaining_library, mulligans, reason).
    """
    deck = library[:]
    random.shuffle(deck)
    mulligans = 0
    reason    = "keep"

    land_set = set(profile["lands"])
    key_set  = set(profile["key_hand"] + profile["key_gy"] + profile["keep_if"])

    def card_priority(c: str) -> float:
        if c in key_set:                                    return 0.0
        if c in land_set:                                   return 1.0
        if c in set(profile["ramp"]):                       return 2.0
        return 3.0 + classified.get(c, {}).get("cmc", 0) * 0.1

    for hand_size in range(7, 3, -1):
        hand      = deck[:hand_size]
        remainder = deck[hand_size:]
        keep, rsn = evaluate_hand(hand, profile, classified)

        if keep:
            put_back_n = 7 - hand_size
            if put_back_n > 0:
                sorted_hand = sorted(hand, key=card_priority)
                hand        = sorted_hand[:hand_size]
                put_back    = sorted_hand[hand_size:]
                random.shuffle(put_back)
                remainder   = put_back + remainder
                random.shuffle(remainder)
            reason = rsn
            break

        mulligans += 1
        reason     = rsn
        deck = hand + remainder
        random.shuffle(deck)
    else:
        hand      = deck[:4]
        remainder = deck[4:]
        reason    = "screw"

    return hand, list(remainder), mulligans, reason


# ─── Tutor Logic ──────────────────────────────────────────────────────────────

def cards_matching_restriction(library: List[str], restriction: Optional[str], card_data: Dict[str, dict]) -> List[str]:
    if restriction is None:
        return list(library)
    rl = restriction.lower()
    return [n for n in library if rl in (card_data.get(n, {}).get("type_line", "") or "").lower()]


def optimal_tutor_target(
    hand: List[str], library: List[str], graveyard: set,
    profile: dict, classified: Dict[str, dict], card_data: Dict[str, dict],
    restriction: Optional[str], mana_available: int, turn: int,
) -> Optional[str]:
    candidates = cards_matching_restriction(library, restriction, card_data)
    if not candidates:
        return None

    cands_set  = set(candidates)
    key_hand   = profile["key_hand"]
    key_gy     = profile["key_gy"]
    hand_set   = set(hand)

    def cmc_of(n: str) -> float:
        return classified.get(n, {}).get("cmc", 99.0)

    # P1: Missing hand-tracked win piece
    for piece in key_hand:
        if piece not in hand_set and piece not in graveyard and piece in cands_set:
            return piece

    # P2: Missing GY piece (for GY mode)
    if profile["gy_mode"]:
        for piece in key_gy:
            if piece not in graveyard and piece in cands_set:
                return piece

    # P3: Ramp if behind on mana
    expected = turn + 1
    if mana_available < expected:
        ramp_set  = set(profile["ramp"])
        ramp_opts = sorted([c for c in candidates if c in ramp_set], key=cmc_of)
        if ramp_opts:
            return ramp_opts[0]

    # P4: Draw if hand thin
    if len(hand) <= 2:
        draw_set  = set(profile["draw"])
        draw_opts = [c for c in candidates if c in draw_set]
        if draw_opts:
            return draw_opts[0]

    # P5: Any win con by lowest CMC
    win_set   = set(profile["win_cons"])
    win_opts  = sorted([c for c in candidates if c in win_set], key=cmc_of)
    if win_opts:
        return win_opts[0]

    # P6: Anything by CMC
    return min(candidates, key=cmc_of)


# ─── Win Condition Check ──────────────────────────────────────────────────────

def check_win_condition(
    hand: List[str], graveyard: set,
    profile: dict, classified: Dict[str, dict], mana_available: int,
) -> bool:
    key_hand = profile["key_hand"]
    key_gy   = profile["key_gy"]
    win_mana = profile["win_mana"]

    if mana_available < win_mana:
        return False

    # GY mode: all GY pieces assembled
    if key_gy:
        if not all(k in graveyard for k in key_gy):
            return False
        return True

    # Hand mode: ANY key piece in hand with enough mana to cast it
    if key_hand:
        hand_set = set(hand)
        for k in key_hand:
            cost = classified.get(k, {}).get("cmc", 99)
            if k in hand_set and mana_available >= cost:
                return True
        return False

    return True  # no key pieces specified — pure mana check


# ─── Game Simulator ───────────────────────────────────────────────────────────

def simulate_game(
    library_orig: List[str],
    profile: dict,
    classified: Dict[str, dict],
    card_data: Dict[str, dict],
) -> dict:
    """Simulate one game. Returns per-game stats dict."""

    # Mulligan
    hand, library, mulligans, mull_reason = london_mulligan(library_orig, profile, classified)

    # Pre-compute sets for fast membership checks
    land_set   = set(profile["lands"])
    ramp_set   = set(profile["ramp"])
    draw_set   = set(profile["draw"])
    tutor_set  = set(profile["tutors"])
    win_set    = set(profile["win_cons"])
    mill_set   = set(profile["mill_cards"])
    key_hand_s = set(profile["key_hand"])
    key_gy_s   = set(profile["key_gy"])

    # Mutable game state
    graveyard       = set()
    battlefield     = []       # permanents in play
    mill_permanents = []       # subset of battlefield with mill effects
    lands_in_play   = 0
    mana_rock_bonus = 0        # extra mana/turn from rocks/dorks

    ramp_first_turn = None
    draw_first_turn = None
    dead_turns      = 0
    color_fails     = 0
    win_turn        = None

    key_hand_seen = {k: None for k in key_hand_s}
    key_gy_seen   = {k: None for k in key_gy_s}

    drawn_cards = set(hand)
    cast_cards  = set()

    land_per_turn = []
    mana_per_turn = []

    # Check opening hand for key pieces
    hand_set_0 = set(hand)
    for k in key_hand_s:
        if k in hand_set_0:
            key_hand_seen[k] = 0

    def _record_gy_key(name: str, turn_n: int) -> None:
        if name in key_gy_s and key_gy_seen.get(name) is None:
            key_gy_seen[name] = turn_n

    def _record_hand_key(name: str, turn_n: int) -> None:
        if name in key_hand_s and key_hand_seen.get(name) is None:
            key_hand_seen[name] = turn_n

    for turn in range(1, MAX_TURNS + 1):

        # ── 1. Draw ──────────────────────────────────────────────────────────
        if library:
            drawn = library.pop(0)
            hand.append(drawn)
            drawn_cards.add(drawn)
            _record_hand_key(drawn, turn)

        # ── 2. Mill (from permanents already on battlefield) ─────────────────
        for perm in mill_permanents:
            mill_n = classified.get(perm, {}).get("mill_count", 0)
            if mill_n > 0 and library:
                actual = min(mill_n, len(library))
                for mc in library[:actual]:
                    graveyard.add(mc)
                    _record_gy_key(mc, turn)
                library = library[actual:]

        # ── 3. Play a land ───────────────────────────────────────────────────
        hand_lands = [c for c in hand if c in land_set]
        if hand_lands:
            # Prefer a land that adds a new color to available colors
            available_colors = set()
            for b in battlefield:
                available_colors.update(classified.get(b, {}).get("produced_colors", []))

            def land_score(ln: str) -> int:
                produced = classified.get(ln, {}).get("produced_colors", [])
                return sum(1 for c in produced if c in 'WUBRG' and c not in available_colors)

            best_land = max(hand_lands, key=land_score)
            hand.remove(best_land)
            cast_cards.add(best_land)
            battlefield.append(best_land)
            lands_in_play += 1

        # ── 4. Compute mana ──────────────────────────────────────────────────
        mana_available = lands_in_play + mana_rock_bonus

        # ── 5. Color pool ────────────────────────────────────────────────────
        color_pool = set()
        for b in battlefield:
            color_pool.update(c for c in (classified.get(b, {}).get("produced_colors", [])) if c in 'WUBRG')

        # ── 6. Cast spells (priority loop) ───────────────────────────────────
        cast_count_this_turn = 0

        def try_cast_ramp() -> bool:
            nonlocal mana_available, mana_rock_bonus, lands_in_play, ramp_first_turn
            hand_ramp = sorted(
                [c for c in hand if c in ramp_set],
                key=lambda c: classified.get(c, {}).get("cmc", 99.0)
            )
            for rc in hand_ramp:
                cost = int(classified.get(rc, {}).get("cmc", 99))
                if cost > mana_available:
                    continue
                # Color check (simplified: if we have lands we can usually splash)
                hand.remove(rc)
                cast_cards.add(rc)
                mana_available -= cost

                mp = classified.get(rc, {}).get("mana_produced", 0)
                is_land_fetch = (classified.get(rc, {}).get("is_tutor")
                                 and classified[rc]["tutor_dest"] in ("hand", "battlefield")
                                 and classified.get(rc, {}).get("tutor_restriction") == "Land")

                if is_land_fetch:
                    # Fetch a basic land to battlefield
                    basics_in_lib = [l for l in library if l in BASIC_LANDS]
                    if basics_in_lib:
                        fetched = basics_in_lib[0]
                        library.remove(fetched)
                        random.shuffle(library)
                        battlefield.append(fetched)
                        lands_in_play += 1
                        mana_available += 1
                    else:
                        mana_rock_bonus += max(mp, 1)
                        battlefield.append(rc)
                else:
                    mana_rock_bonus += mp
                    battlefield.append(rc)
                    if classified.get(rc, {}).get("mill_count", 0) > 0:
                        mill_permanents.append(rc)

                if ramp_first_turn is None:
                    ramp_first_turn = turn
                return True
            return False

        def try_cast_tutor() -> bool:
            nonlocal mana_available
            hand_tutors = sorted(
                [c for c in hand if c in tutor_set or classified.get(c, {}).get("is_tutor")],
                key=lambda c: classified.get(c, {}).get("cmc", 99.0)
            )
            for tc in hand_tutors:
                cost = int(classified.get(tc, {}).get("cmc", 99))
                if cost > mana_available or not library:
                    continue
                hand.remove(tc)
                cast_cards.add(tc)
                mana_available -= cost

                dest        = classified.get(tc, {}).get("tutor_dest", "hand")
                restriction = classified.get(tc, {}).get("tutor_restriction")
                target = optimal_tutor_target(
                    hand, library, graveyard, profile, classified, card_data,
                    restriction, mana_available, turn
                )
                if target and target in library:
                    library.remove(target)
                    random.shuffle(library)
                    if dest == "hand":
                        hand.append(target)
                        drawn_cards.add(target)
                        _record_hand_key(target, turn)
                    elif dest == "top":
                        library.insert(0, target)
                    elif dest == "gy":
                        graveyard.add(target)
                        _record_gy_key(target, turn)
                        # Tutor-to-GY may be able to put multiple cards in GY
                        # (Buried Alive puts 3 — find the other key GY targets too)
                        for other_key in profile["key_gy"]:
                            if other_key not in graveyard and other_key in library:
                                library.remove(other_key)
                                graveyard.add(other_key)
                                _record_gy_key(other_key, turn)
                                random.shuffle(library)
                    elif dest == "battlefield":
                        battlefield.append(target)
                        cast_cards.add(target)
                return True
            return False

        def try_cast_draw() -> bool:
            nonlocal mana_available, draw_first_turn
            if len(hand) > 4:
                return False
            hand_draw = sorted(
                [c for c in hand if c in draw_set],
                key=lambda c: classified.get(c, {}).get("cmc", 99.0)
            )
            for dc in hand_draw:
                cost = int(classified.get(dc, {}).get("cmc", 99))
                if cost > mana_available:
                    continue
                hand.remove(dc)
                cast_cards.add(dc)
                mana_available -= cost

                draw_n = classified.get(dc, {}).get("draw_count", 1)
                for _ in range(draw_n):
                    if library:
                        d = library.pop(0)
                        hand.append(d)
                        drawn_cards.add(d)
                        _record_hand_key(d, turn)

                if draw_first_turn is None:
                    draw_first_turn = turn
                return True
            return False

        def try_cast_win_pieces() -> bool:
            nonlocal mana_available
            if mana_available < profile["win_mana"]:
                return False
            win_in_hand = [c for c in hand if c in win_set]
            if not win_in_hand:
                return False
            wc   = min(win_in_hand, key=lambda c: classified.get(c, {}).get("cmc", 99.0))
            cost = int(classified.get(wc, {}).get("cmc", 99))
            if cost > mana_available:
                return False
            hand.remove(wc)
            cast_cards.add(wc)
            mana_available -= cost
            return True

        # Priority loop: ramp → tutor → draw → win pieces
        something_cast = True
        while something_cast:
            something_cast = False
            if try_cast_ramp():
                something_cast = True
                cast_count_this_turn += 1
                continue
            if try_cast_tutor():
                something_cast = True
                cast_count_this_turn += 1
                continue
            if try_cast_draw():
                something_cast = True
                cast_count_this_turn += 1
                continue
            if try_cast_win_pieces():
                something_cast = True
                cast_count_this_turn += 1
                continue

        # ── 7. Color fail check ──────────────────────────────────────────────
        non_land_in_hand = [c for c in hand if c not in land_set]
        for c in non_land_in_hand:
            needed = classified.get(c, {}).get("colors_needed", [])
            cost   = classified.get(c, {}).get("cmc", 99)
            if needed and cost <= mana_available:
                if any(col not in color_pool for col in needed):
                    color_fails += 1
                    break

        # ── 8. Dead turn ─────────────────────────────────────────────────────
        if cast_count_this_turn == 0 and mana_available > 0 and non_land_in_hand:
            min_cost = min(
                (classified.get(c, {}).get("cmc", 99) for c in non_land_in_hand),
                default=99
            )
            if min_cost > mana_available:
                dead_turns += 1

        # ── Record turn stats ────────────────────────────────────────────────
        final_mana = lands_in_play + mana_rock_bonus
        land_per_turn.append(lands_in_play)
        mana_per_turn.append(final_mana)

        # ── 9. Win condition check ───────────────────────────────────────────
        if check_win_condition(hand, graveyard, profile, classified, final_mana):
            win_turn = turn
            break

    # Threat deployment: earliest turn a high-CMC threat was in hand AND affordable
    # Used for parasitic decks where "win" can't be simulated but threat timing can
    threat_deploy_turn = None
    threat_cmc = profile.get("threat_cmc", 5)
    for turn_idx, mana in enumerate(mana_per_turn, start=1):
        if mana >= threat_cmc:
            threat_deploy_turn = turn_idx
            break

    # Stuck cards: drawn but never cast (excluding lands)
    stuck = [c for c in drawn_cards if c not in cast_cards and c not in land_set]

    return {
        "mulligans":        mulligans,
        "mull_reason":      mull_reason,
        "land_per_turn":    land_per_turn,
        "mana_per_turn":    mana_per_turn,
        "ramp_first_turn":  ramp_first_turn,
        "draw_first_turn":  draw_first_turn,
        "dead_turns":       dead_turns,
        "color_fails":      color_fails,
        "key_hand_seen":    key_hand_seen,
        "key_gy_seen":      key_gy_seen,
        "win_turn":            win_turn,
        "threat_deploy_turn":  threat_deploy_turn,
        "stuck_cards":         stuck,
    }


# ─── Aggregation ──────────────────────────────────────────────────────────────

def run_simulation(
    deck: List[str], profile: dict,
    classified: Dict[str, dict], card_data: Dict[str, dict],
    games: int,
) -> dict:
    """Run N games and aggregate results."""

    mull_dist         = defaultdict(int)
    screw_count       = 0
    flood_count       = 0
    total_mulligans   = 0
    land_acc          = defaultdict(float)
    mana_acc          = defaultdict(float)
    turn_reach        = defaultdict(int)
    ramp_turns        = []
    draw_turns        = []
    dead_turns_list   = []
    color_fails_total = 0
    win_turns_list    = []
    key_hand_turns    = defaultdict(list)
    key_gy_turns      = defaultdict(list)
    bottleneck_cnt    = defaultdict(int)
    stuck_cnt         = defaultdict(int)
    threat_turns      = []   # turns first threat was affordable (parasitic mode)

    for _ in range(games):
        r = simulate_game(deck, profile, classified, card_data)

        mulls = r["mulligans"]
        total_mulligans += mulls
        mull_dist[mulls] += 1
        rsn = r["mull_reason"]
        if rsn == "screw":  screw_count += 1
        elif rsn == "flood": flood_count += 1

        for t, (land, mana) in enumerate(zip(r["land_per_turn"], r["mana_per_turn"])):
            land_acc[t]  += land
            mana_acc[t]  += mana
            turn_reach[t] += 1

        if r["ramp_first_turn"] is not None: ramp_turns.append(r["ramp_first_turn"])
        if r["draw_first_turn"] is not None: draw_turns.append(r["draw_first_turn"])
        dead_turns_list.append(r["dead_turns"])
        color_fails_total += r["color_fails"]

        if r["win_turn"] is not None:
            win_turns_list.append(r["win_turn"])

        for k, t in r["key_hand_seen"].items():
            if t is not None: key_hand_turns[k].append(t)
        for k, t in r["key_gy_seen"].items():
            if t is not None: key_gy_turns[k].append(t)

        # Bottleneck: which piece was last to arrive in games that won?
        if r["win_turn"] is not None:
            all_seen = {**r["key_hand_seen"], **r["key_gy_seen"]}
            seen_list = [(k, t) for k, t in all_seen.items() if t is not None]
            if seen_list:
                bottleneck_cnt[max(seen_list, key=lambda x: x[1])[0]] += 1

        for c in r["stuck_cards"]:
            stuck_cnt[c] += 1

        if r["threat_deploy_turn"] is not None:
            threat_turns.append(r["threat_deploy_turn"])

    # Averages
    max_t_reached = max((t for t, n in turn_reach.items() if n > 0), default=0)
    avg_lands = [round(land_acc[t] / turn_reach[t], 2) for t in range(max_t_reached + 1)]
    avg_mana  = [round(mana_acc[t] / turn_reach[t], 2) for t in range(max_t_reached + 1)]

    won       = len(win_turns_list)
    avg_win_t = round(sum(win_turns_list) / won, 1) if won else None
    win_dist  = {t: round(sum(1 for x in win_turns_list if x <= t) / games * 100, 1)
                 for t in [5, 7, 9, 12, 15, MAX_TURNS]}

    # Bottleneck
    bottleneck_piece = None
    bottleneck_pct   = 0.0
    if won and bottleneck_cnt:
        bottleneck_piece = max(bottleneck_cnt, key=bottleneck_cnt.get)
        bottleneck_pct   = round(bottleneck_cnt[bottleneck_piece] / won * 100, 1)

    # Key stats
    key_stats = {}
    for k, turns in {**key_hand_turns, **key_gy_turns}.items():
        seen  = len(turns)
        avg_t = round(sum(turns) / seen, 1) if seen else None
        key_stats[k] = {
            "zone":     "gy" if k in set(profile["key_gy"]) else "hand",
            "pct_seen": round(seen / games * 100, 1),
            "avg_turn": avg_t,
            "by_turn":  {t: round(sum(1 for x in turns if x <= t) / games * 100, 1) for t in [5, 7, 10]},
        }

    top_stuck = sorted(stuck_cnt.items(), key=lambda x: -x[1])[:5]

    return {
        "games":               games,
        "natural_keep_pct":    round(mull_dist.get(0, 0) / games * 100, 1),
        "screw_pct":           round(screw_count / games * 100, 1),
        "flood_pct":           round(flood_count / games * 100, 1),
        "avg_mulligans":       round(total_mulligans / games, 2),
        "mull_dist":           dict(sorted(mull_dist.items())),
        "avg_lands_per_turn":  avg_lands,
        "avg_mana_per_turn":   avg_mana,
        "avg_ramp_turn":       round(sum(ramp_turns) / len(ramp_turns), 1) if ramp_turns else None,
        "avg_draw_turn":       round(sum(draw_turns) / len(draw_turns), 1) if draw_turns else None,
        "avg_dead_turns":      round(sum(dead_turns_list) / games, 2),
        "color_fail_pct":      round(color_fails_total / games * 100, 1),
        "won_games":           won,
        "win_pct":             round(won / games * 100, 1),
        "avg_win_turn":        avg_win_t,
        "win_dist":            win_dist,
        "bottleneck_piece":    bottleneck_piece,
        "bottleneck_pct":      bottleneck_pct,
        "key_stats":           key_stats,
        "top_stuck_cards":     top_stuck,
        "avg_threat_turn":     round(sum(threat_turns) / len(threat_turns), 1) if threat_turns else None,
        "threat_deploy_pct":   round(len(threat_turns) / games * 100, 1),
    }


# ─── Recommendations ──────────────────────────────────────────────────────────

def generate_recommendations(stats: dict, profile: dict, classified: Dict[str, dict], budget: int = 0) -> List[str]:
    recs = []
    land_count = profile["land_count"]
    avg_cmc    = profile["avg_cmc"]

    screw = stats["screw_pct"]
    flood = stats["flood_pct"]

    if screw > 15:
        deficit = max(1, round((screw - 10) / 5))
        recs.append(
            f"✗ SCREW {screw:.0f}% — add {deficit} land{'s' if deficit > 1 else ''} "
            f"(current {land_count} is low for avg CMC {avg_cmc:.1f})"
        )
    elif screw <= 8:
        recs.append(f"✓ LAND COUNT — screw {screw:.0f}%, land count looks right")

    if flood > 12:
        recs.append(f"✗ FLOOD {flood:.0f}% — cut 1-2 lands or add cycling/cantrips")

    ramp_t = stats.get("avg_ramp_turn")
    if ramp_t is not None:
        if ramp_t > 3.5:
            expensive = [n for n in profile["ramp"] if classified.get(n, {}).get("cmc", 0) >= 3]
            recs.append(
                f"✗ RAMP TIMING avg T{ramp_t:.1f} (target ≤T2.5)\n"
                f"  {len(expensive)} ramp spells cost 3+ mana — arriving too late\n"
                f"  Replace with 2-CMC rocks: Arcane Signet, Fellwar Stone, Thought Vessel"
            )
        elif ramp_t <= 2.5:
            recs.append(f"✓ RAMP — first ramp T{ramp_t:.1f} avg, package is fast")

    dead = stats["avg_dead_turns"]
    if dead > 1.2:
        draw_note = f"Draw arrives T{stats['avg_draw_turn']:.1f} avg — " if stats.get("avg_draw_turn") else ""
        recs.append(
            f"⚠ DEAD TURNS {dead:.1f}/game (target <0.5)\n"
            f"  {draw_note}hand empties before draw engine kicks in\n"
            f"  Add 2-3 CMC draw spells to maintain card flow"
        )
    elif dead <= 0.5:
        recs.append(f"✓ CARD FLOW — {dead:.1f} dead turns/game, hand stays full")

    if stats["bottleneck_piece"] and stats["bottleneck_pct"] > 50:
        recs.append(
            f"⚠ BOTTLENECK — '{stats['bottleneck_piece']}' is last piece in "
            f"{stats['bottleneck_pct']:.0f}% of winning games\n"
            f"  Add redundancy or a tutor that can find it"
        )

    is_parasitic = profile.get("is_parasitic", False)
    is_fun       = profile.get("deck_type") == DECK_TYPE_FUN

    if not is_parasitic and not is_fun:
        win_pct = stats["win_pct"]
        if win_pct < 60:
            recs.append(
                f"⚠ WIN CONSISTENCY {win_pct:.0f}% assembled by T{MAX_TURNS} — "
                f"needs more tutors or the win con is too fragile"
            )
        elif win_pct >= 85:
            recs.append(f"✓ WIN CONSISTENCY — {win_pct:.0f}% assembled by T{MAX_TURNS}")

    if is_parasitic and stats.get("avg_threat_turn"):
        threat_t = stats["avg_threat_turn"]
        if threat_t > 6:
            recs.append(
                f"⚠ THREAT TIMING avg T{threat_t:.1f} — threats are arriving late\n"
                f"  More ramp or lower-CMC threats would let you apply pressure earlier"
            )
        else:
            recs.append(f"✓ THREAT TIMING — threats affordable by T{threat_t:.1f} avg")

    if stats["color_fail_pct"] > 8:
        color_pct = stats["color_fail_pct"]
        all_colors = set()
        for c in classified.values():
            all_colors.update(c.get("colors_needed", []))
        num_colors = len(all_colors) or 2
        if budget > 0 and budget < 100 and num_colors >= 3:
            # At low budget, high color fail rate in 3+ color decks is expected
            # without fetches/duals/shocks — flag but suggest attainable fixes
            recs.append(
                f"⚠ COLOR {color_pct:.0f}% color fails — expected at this budget for {num_colors}-color\n"
                f"  Fetches and original duals are out of range, but budget fixes help:\n"
                f"  Command Tower, Exotic Orchard, pain lands, check lands, filter lands"
            )
        else:
            recs.append(
                f"⚠ COLOR {color_pct:.0f}% of turns had right mana but wrong colors\n"
                f"  Mana base needs more sources of the required colors"
            )

    high_stuck = [(n, c) for n, c in stats["top_stuck_cards"] if c > stats["games"] * 0.15]
    if high_stuck:
        names = ", ".join(f"{n} ({round(c/stats['games']*100):.0f}%)" for n, c in high_stuck[:3])
        recs.append(
            f"⚠ STUCK CARDS — drawn but rarely cast:\n"
            f"  {names}\n"
            f"  Too expensive for when they arrive — prime cut candidates"
        )

    return recs


# ─── Output Formatter ─────────────────────────────────────────────────────────

def _bar(value: float, max_val: float, width: int = 20) -> str:
    if max_val == 0:
        return "[" + "." * width + "]"
    filled = min(width, int(round(value / max_val * width)))
    return "[" + "#" * filled + "." * (width - filled) + "]"


def print_report(stats: dict, profile: dict, classified: Dict[str, dict], commander: str, budget: int = 0) -> None:
    W = 60
    is_parasitic = profile.get("is_parasitic", False)
    is_fun       = profile.get("deck_type") == DECK_TYPE_FUN

    print()
    print("=" * W)
    print(f"  Goldfish — {commander or 'Unknown Commander'}")
    if is_parasitic:
        mode = "Parasitic/theft"
    elif profile["gy_mode"]:
        mode = "GY assembly"
    else:
        mode = "Hand assembly"
    print(f"  {stats['games']} games · {mode} · max T{MAX_TURNS}")
    print("=" * W)

    # Parasitic disclaimer
    if is_parasitic:
        print()
        print(f"  ⚠  PARASITIC DECK ({profile['parasitic_count']} cards rely on opponents)")
        print( "     Win-turn metrics are not meaningful — this deck requires opponents")
        print( "     to have things worth stealing. Showing mana development and")
        print( "     threat deployment instead.")

    # Opening Hand
    print()
    print("── Opening Hand " + "─" * (W - 16))
    print(f"  Natural keep: {stats['natural_keep_pct']:>5.1f}%  "
          f"Screw: {stats['screw_pct']:.1f}%  Flood: {stats['flood_pct']:.1f}%")
    dist_str = "  ".join(f"{k}×:{v}" for k, v in stats["mull_dist"].items())
    print(f"  Avg mulligans: {stats['avg_mulligans']:.2f}   Distribution: {dist_str}")

    # Mana Development
    print()
    print("── Mana Development " + "─" * (W - 21))
    lands_list = stats["avg_lands_per_turn"][:12]
    mana_list  = stats["avg_mana_per_turn"][:12]
    max_m = max(mana_list) if mana_list else 7.0
    print(f"  {'T':<4} {'Lands':>6} {'Mana':>6}  Chart")
    for i, (land, mana) in enumerate(zip(lands_list, mana_list), start=1):
        b = _bar(mana, max_m)
        print(f"  T{i:<3} {land:>6.1f} {mana:>6.1f}  {b} {mana:.1f}")

    extras = []
    if stats["avg_ramp_turn"]: extras.append(f"First ramp: T{stats['avg_ramp_turn']:.1f}")
    if stats["avg_draw_turn"]: extras.append(f"First draw: T{stats['avg_draw_turn']:.1f}")
    extras.append(f"Dead turns: {stats['avg_dead_turns']:.2f}/game")
    if stats["color_fail_pct"]: extras.append(f"Color fails: {stats['color_fail_pct']:.1f}%")
    print(f"\n  {' | '.join(extras)}")

    # Key Pieces (skip for parasitic — they're not meaningful without opponents)
    if stats["key_stats"] and not is_parasitic:
        print()
        print("── Key Pieces " + "─" * (W - 14))
        for card, ks in stats["key_stats"].items():
            zone = "[GY]" if ks["zone"] == "gy" else "[hand]"
            avg_t = f"T{ks['avg_turn']:.1f}" if ks["avg_turn"] is not None else "never"
            print(f"  {card} {zone}")
            print(f"    Seen {ks['pct_seen']:.1f}% of games · avg {avg_t}")
            by = ks["by_turn"]
            print(f"    by T5: {by.get(5,0):.0f}%  by T7: {by.get(7,0):.0f}%  by T10: {by.get(10,0):.0f}%")

    # Threat Deployment (parasitic) vs Win Condition (combo/GY)
    print()
    if is_parasitic:
        print("── Threat Deployment " + "─" * (W - 21))
        threat_t = stats.get("avg_threat_turn")
        threat_pct = stats.get("threat_deploy_pct", 0)
        threat_cmc = profile.get("threat_cmc", 5)
        if threat_t:
            print(f"  First {threat_cmc}+ CMC threat affordable by T{threat_t:.1f} avg")
            print(f"  Threat online in {threat_pct:.0f}% of games within T{MAX_TURNS}")
            print()
            print(f"  This tells you: how fast can you start doing scary things?")
            print(f"  Whether those things win depends entirely on your opponents' boards.")
        else:
            print(f"  No {threat_cmc}+ CMC threats reachable in simulated games.")
            print(f"  Ramp may be insufficient to reliably cast your threats.")
    elif not is_fun:
        print("── Win Condition " + "─" * (W - 17))
        print(f"  Won {stats['won_games']}/{stats['games']} games ({stats['win_pct']:.1f}%)")
        if stats["avg_win_turn"]:
            print(f"  Average win turn: T{stats['avg_win_turn']:.1f}")
            dist = stats["win_dist"]
            print("  " + "  ".join(f"T{k}: {v:.0f}%" for k, v in sorted(dist.items())))
        else:
            print("  No games completed win condition in the simulation.")

        if stats["bottleneck_piece"]:
            print(f"\n  Bottleneck: '{stats['bottleneck_piece']}' "
                  f"was last piece in {stats['bottleneck_pct']:.0f}% of winning games")

    # Stuck Cards
    high_stuck = [(n, c) for n, c in stats["top_stuck_cards"] if c > stats["games"] * 0.15]
    if high_stuck:
        print()
        print("── Frequently Stuck " + "─" * (W - 21))
        for name, count in high_stuck:
            pct = round(count / stats["games"] * 100)
            print(f"  {name}: stuck in {pct}% of games")

    # Recommendations
    recs = generate_recommendations(stats, profile, classified, budget)
    if recs:
        print()
        print("── Recommendations " + "─" * (W - 20))
        for rec in recs:
            for line in rec.split("\n"):
                print(f"  {line}")

    print()


# ─── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scryfall-powered Monte Carlo goldfish simulator for Commander decks."
    )
    parser.add_argument("--file",      required=True,  metavar="PATH",  help="Path to .md decklist")
    parser.add_argument("--commander", default="",     metavar="NAME",  help="Commander (overrides file)")
    parser.add_argument("--key-cards", default="",     metavar="CARDS", help="Hand-tracked win pieces (auto if omitted)")
    parser.add_argument("--gy-cards",  default="",     metavar="CARDS", help="GY-tracked pieces (enables GY mode)")
    parser.add_argument("--keep-if",   default="",     metavar="CARDS", help="Cards that make 1-land hands keepable")
    parser.add_argument("--win-mana",  default=0,      type=int,        help="Mana to execute win con (auto if 0)")
    parser.add_argument("--games",     default=1000,   type=int,        help="Games to simulate (default: 1000)")
    parser.add_argument("--format",    default="text", choices=["text", "json"])
    parser.add_argument("--deck-type", default="auto",
                        choices=["auto", "combo", "gy", "parasitic", "fun"],
                        help="Override deck type detection (auto = detect from card data)")
    parser.add_argument("--budget",    default=0,      type=int,        help="Deck budget in USD (0 = no limit). Adjusts mana base recommendations.")
    args = parser.parse_args()

    deck, sections, commander = parse_decklist(args.file)
    if args.commander:
        commander = args.commander

    if len(deck) < 10:
        print(f"Error: only {len(deck)} cards parsed — check file format.")
        sys.exit(1)

    # Fetch Scryfall data
    unique = list(set(deck))
    print(f"Fetching card data ({len(unique)} unique cards)...", end="", flush=True)
    card_data = fetch_card_data(unique)
    print(f" done.")

    # Classify
    classified: Dict[str, dict] = {}
    for name in unique:
        section_role = None
        for role_key, names_list in sections.items():
            if name in names_list:
                section_role = role_key
                break
        classified[name] = classify_card(name, card_data.get(name, dict(_EMPTY_CARD)), section_role)

    # Parse CSV overrides
    def parse_csv(s: str) -> List[str]:
        return [x.strip() for x in s.split(",") if x.strip()] if s.strip() else []

    def match_names(raw_list: List[str]) -> List[str]:
        matched = []
        for raw in raw_list:
            found = [n for n in unique if raw.lower() in n.lower()]
            if found:
                matched.append(found[0])
            else:
                print(f"  Warning: '{raw}' not found in deck — skipping")
        return matched

    key_hand_override = match_names(parse_csv(args.key_cards))
    key_gy_override   = match_names(parse_csv(args.gy_cards))
    keep_if_override  = match_names(parse_csv(args.keep_if))

    profile = build_profile(
        deck, sections, card_data, classified,
        key_hand_override, key_gy_override, keep_if_override,
        args.win_mana if args.win_mana > 0 else None,
    )

    # Apply deck type override or auto-detection
    deck_type = args.deck_type
    if deck_type == "auto":
        if profile["gy_mode"]:
            deck_type = DECK_TYPE_GY
        elif profile.get("is_parasitic"):
            deck_type = DECK_TYPE_PARASITIC
        else:
            deck_type = DECK_TYPE_COMBO
    profile["deck_type"] = deck_type
    # Propagate explicit parasitic flag
    if deck_type == DECK_TYPE_PARASITIC:
        profile["is_parasitic"] = True
    elif deck_type == DECK_TYPE_FUN:
        profile["is_parasitic"] = False

    # Print profile summary
    print(f"\nDeck profile detected:")
    print(f"  Lands: {profile['land_count']}  Ramp: {len(profile['ramp'])}  "
          f"Draw: {len(profile['draw'])}  Tutors: {len(profile['tutors'])}  "
          f"Win cons: {len(profile['win_cons'])}")
    print(f"  Avg CMC: {profile['avg_cmc']:.1f}  Rocks: {profile['rock_count']}  "
          f"GY mode: {'yes' if profile['gy_mode'] else 'no'}  "
          f"Min lands to keep: {profile['min_lands_keep']}  "
          f"Win mana: {profile['win_mana']}")
    if profile["key_hand"]:
        print(f"  Tracking (hand): {', '.join(profile['key_hand'][:5])}")
    if profile["key_gy"]:
        print(f"  Tracking (GY):   {', '.join(profile['key_gy'][:5])}")
    if profile["keep_if"]:
        print(f"  Always keep if:  {', '.join(profile['keep_if'][:3])}")

    print(f"\nSimulating {args.games} games...", end="", flush=True)
    stats = run_simulation(deck, profile, classified, card_data, args.games)
    print(" done.")

    if args.format == "json":
        serializable = {k: v for k, v in stats.items()}
        # Convert defaultdict and tuple entries for JSON
        serializable["top_stuck_cards"] = [[n, c] for n, c in stats["top_stuck_cards"]]
        print(json.dumps(serializable, indent=2))
    else:
        print_report(stats, profile, classified, commander, args.budget)


if __name__ == "__main__":
    main()
