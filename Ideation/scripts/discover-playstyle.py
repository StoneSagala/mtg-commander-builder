#!/usr/bin/env python3
"""
discover-playstyle.py — Playstyle discovery questionnaire.

For players who don't know what they want to build. Asks personality-based
questions (no MTG jargon required), scores answers against the 3-layer
archetype taxonomy (engine + game plan + win condition), and outputs a
recommended profile in intake summary format.

Usage:
    python Ideation/scripts/discover-playstyle.py
    python Ideation/scripts/discover-playstyle.py --surprise-me
"""

import argparse
import io
import random
import sys

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


# ---------------------------------------------------------------------------
# Profile descriptions — shown in recommendations
# ---------------------------------------------------------------------------

ENGINE_DESCRIPTIONS = {
    "tokens":       "Flood the board with small creatures. Quantity beats quality.",
    "artifacts":    "Build a machine. Rocks, constructs, and synergistic permanents.",
    "graveyard":    "Use your discard pile as a second hand. Death is a resource.",
    "aristocrats":  "Sacrifice your own creatures for value. Every death does something.",
    "tribal":       "Pick a creature type and go deep. Shared buffs, shared mechanics.",
    "enchantress":  "Layer permanent enchantments that compound over time.",
    "spellslinger": "Cast a lot of instants and sorceries. Going off feels like a puzzle.",
    "counters":     "Grow creatures over time with +1/+1 counters. Patience pays off.",
    "lands":        "The land base is the engine. Lands do things beyond producing mana.",
    "blink-etb":    "Repeatedly enter-the-battlefield effects by blinking and bouncing.",
    "theft-chaos":  "Take opponents' things. Make the game unpredictable.",
}

GAMEPLAN_DESCRIPTIONS = {
    "go-wide":  "Win through numbers. Flood the board and attack with everything.",
    "go-tall":  "Build one massive threat and protect it. One card wins the game.",
    "combo":    "Assemble specific pieces for a deterministic win. It clicks, game over.",
    "burn":     "Deal damage through spells and triggers, not combat.",
    "stax":     "Slow everyone down with taxes and resource denial. Win from control.",
    "control":  "Answer threats reactively. Win from a position of total dominance.",
    "politics": "Make deals, leverage table dynamics. Win through relationships.",
}

WINCON_DESCRIPTIONS = {
    "life-depletion":    "Reduce all opponents to 0 life through combat, drain, or burn.",
    "commander-damage":  "Deal 21 combat damage with your commander specifically.",
    "mill":              "Empty opponents' libraries. Win when they can't draw.",
    "poison":            "Deal 10 poison counters. A completely separate damage track.",
    "alternate-win-cons": "Win with a specific card (Thassa's Oracle, Felidar Sovereign, etc.).",
}

INTERACTION_DESCRIPTIONS = {
    "Reactive":  "Answer threats as they appear. Removal, counterspells, board wipes.",
    "Balanced":  "Some interaction, but not the deck's identity.",
    "Proactive": "Focus on your plan. Let opponents deal with you.",
}


# ---------------------------------------------------------------------------
# Questionnaire
# Each question has options. Each option maps to score deltas across:
#   engine slugs, game-plan slugs, win-con slugs, interaction style
# ---------------------------------------------------------------------------

QUESTIONS = [
    {
        "prompt": "The perfect win looks like...",
        "options": [
            {
                "text": "Sending an unstoppable army across the table",
                "scores": {"tokens": 3, "go-wide": 3, "tribal": 2, "life-depletion": 3, "commander-damage": 1},
            },
            {
                "text": "Two cards clicking together and everyone scoops",
                "scores": {"combo": 3, "spellslinger": 1, "alternate-win-cons": 2},
            },
            {
                "text": "Having so many resources nobody can stop you anymore",
                "scores": {"control": 3, "enchantress": 2, "graveyard": 2, "life-depletion": 1},
            },
            {
                "text": "Pulling off something unexpected that nobody saw coming",
                "scores": {"theft-chaos": 3, "politics": 2, "alternate-win-cons": 2},
            },
        ],
    },
    {
        "prompt": "In a 4-player game, you want to be...",
        "options": [
            {
                "text": "The obvious threat everyone has to answer",
                "scores": {"go-wide": 2, "go-tall": 2, "tribal": 1, "life-depletion": 1},
            },
            {
                "text": "The one nobody attacks until it's too late",
                "scores": {"combo": 3, "control": 2, "enchantress": 1, "alternate-win-cons": 1},
            },
            {
                "text": "The dealmaker — alliances, favors, and leverage",
                "scores": {"politics": 3, "theft-chaos": 1},
            },
            {
                "text": "The wildcard — everyone's nervous but unsure why",
                "scores": {"theft-chaos": 3, "stax": 1, "combo": 1, "burn": 1},
            },
        ],
    },
    {
        "prompt": "When you think about opponents' cards, you...",
        "options": [
            {
                "text": "Ignore them — I'm focused on my own plan",
                "scores": {"go-tall": 2, "combo": 2, "spellslinger": 1, "Proactive": 3},
            },
            {
                "text": "Answer the biggest threat when it matters",
                "scores": {"control": 2, "Balanced": 3},
            },
            {
                "text": "Want to take their best stuff and use it against them",
                "scores": {"theft-chaos": 4, "Balanced": 1},
            },
            {
                "text": "Want to destroy everything — I want a clean board",
                "scores": {"stax": 2, "control": 2, "burn": 1, "Reactive": 3},
            },
        ],
    },
    {
        "prompt": "A perfect turn looks like...",
        "options": [
            {
                "text": "Playing 4-5 things and flooding the board",
                "scores": {"tokens": 3, "go-wide": 2, "spellslinger": 2, "enchantress": 1},
            },
            {
                "text": "Playing one card that changes the entire game",
                "scores": {"go-tall": 3, "artifacts": 2, "blink-etb": 1},
            },
            {
                "text": "Setting up something that pays off next turn",
                "scores": {"combo": 3, "graveyard": 2, "aristocrats": 1},
            },
            {
                "text": "Watching opponents suffer from something I played two turns ago",
                "scores": {"stax": 4, "aristocrats": 2, "enchantress": 1},
            },
        ],
    },
    {
        "prompt": "How complex do you want your turns to be?",
        "options": [
            {
                "text": "Simple — one plan, execute it well",
                "scores": {"go-tall": 2, "tribal": 2, "life-depletion": 1, "commander-damage": 1},
            },
            {
                "text": "Some decisions, but not overwhelming",
                "scores": {"tokens": 1, "enchantress": 1, "blink-etb": 1, "Balanced": 2},
            },
            {
                "text": "Complex — I want interesting choices every turn",
                "scores": {"combo": 2, "stax": 2, "control": 2, "politics": 2},
            },
            {
                "text": "I want the most powerful thing, complexity be damned",
                "scores": {"combo": 2, "graveyard": 1, "artifacts": 1, "alternate-win-cons": 1},
            },
        ],
    },
    {
        "prompt": "Creatures in your deck are...",
        "options": [
            {
                "text": "My army — I want a full board at all times",
                "scores": {"tokens": 3, "tribal": 3, "go-wide": 2, "life-depletion": 1},
            },
            {
                "text": "A few powerful threats I protect",
                "scores": {"go-tall": 3, "artifacts": 1, "commander-damage": 2},
            },
            {
                "text": "Resources to sacrifice, recycle, or exploit",
                "scores": {"aristocrats": 4, "graveyard": 3, "tokens": 1},
            },
            {
                "text": "Barely relevant — I win another way",
                "scores": {"spellslinger": 3, "enchantress": 2, "combo": 2, "control": 1, "mill": 1},
            },
        ],
    },
    {
        "prompt": "How long do you want games to last?",
        "options": [
            {
                "text": "Short — if I'm not winning by turn 8 something went wrong",
                "scores": {"combo": 2, "go-wide": 2, "burn": 2, "tokens": 1},
            },
            {
                "text": "Medium — develop a board, then close it out",
                "scores": {"go-tall": 2, "tribal": 2, "artifacts": 1, "life-depletion": 1},
            },
            {
                "text": "Long — I'm happy grinding if I end up on top",
                "scores": {"control": 3, "stax": 2, "graveyard": 2, "enchantress": 1, "mill": 2},
            },
            {
                "text": "Doesn't matter — I want a memorable finish",
                "scores": {"politics": 3, "theft-chaos": 2, "alternate-win-cons": 2},
            },
        ],
    },
    {
        "prompt": "Your commander gets removed. Your reaction is...",
        "options": [
            {
                "text": "Recast immediately — this is the plan, I'm built for it",
                "scores": {"go-tall": 2, "commander-damage": 3, "artifacts": 1},
            },
            {
                "text": "Adapt — I have other ways to win",
                "scores": {"control": 2, "graveyard": 1, "combo": 1, "Balanced": 2},
            },
            {
                "text": "Barely notice — the deck runs without them",
                "scores": {"tokens": 2, "enchantress": 2, "spellslinger": 2, "go-wide": 1},
            },
            {
                "text": "Make my opponent regret it",
                "scores": {"politics": 2, "stax": 1, "theft-chaos": 1, "Reactive": 1},
            },
        ],
    },
    {
        "prompt": "Which of these sounds most fun?",
        "options": [
            {
                "text": "Casting 10 spells in one turn and going completely off",
                "scores": {"spellslinger": 4, "combo": 2, "burn": 2},
            },
            {
                "text": "Building a massive token army and overrunning everyone",
                "scores": {"tokens": 4, "go-wide": 3, "life-depletion": 2},
            },
            {
                "text": "Using the graveyard as an extra hand full of threats",
                "scores": {"graveyard": 4, "aristocrats": 2, "life-depletion": 1},
            },
            {
                "text": "Locking the game down while you slowly pull ahead",
                "scores": {"stax": 3, "control": 3, "mill": 1},
            },
        ],
    },
    {
        "prompt": "After a great game, you say...",
        "options": [
            {
                "text": "\"Did you see that? I swung for 40 in one attack.\"",
                "scores": {"go-wide": 2, "tokens": 2, "tribal": 1, "commander-damage": 1, "life-depletion": 2},
            },
            {
                "text": "\"Turn 7, perfect. I hit every piece exactly when I needed them.\"",
                "scores": {"combo": 3, "artifacts": 1, "alternate-win-cons": 1},
            },
            {
                "text": "\"I had everyone exactly where I wanted them all game.\"",
                "scores": {"control": 2, "stax": 2, "politics": 2},
            },
            {
                "text": "\"I have no idea how that worked but it was incredible.\"",
                "scores": {"theft-chaos": 3, "politics": 1, "graveyard": 1},
            },
        ],
    },
]

# Interaction style keys mixed into scores
INTERACTION_KEYS = {"Reactive", "Balanced", "Proactive"}

ENGINE_KEYS = set(ENGINE_DESCRIPTIONS.keys())
GAMEPLAN_KEYS = set(GAMEPLAN_DESCRIPTIONS.keys())
WINCON_KEYS = set(WINCON_DESCRIPTIONS.keys())


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def ask_numbered(prompt: str, options: list) -> int:
    print()
    print(prompt)
    for i, opt in enumerate(options, 1):
        print(f"  {i}) {opt['text']}")
    while True:
        resp = input("> ").strip()
        if resp.isdigit() and 1 <= int(resp) <= len(options):
            return int(resp) - 1
        print(f"  Enter a number 1-{len(options)}.")


def score_answers(answers: list[dict]) -> tuple[dict, dict, dict, dict]:
    engines = {k: 0 for k in ENGINE_KEYS}
    gameplans = {k: 0 for k in GAMEPLAN_KEYS}
    wincons = {k: 0 for k in WINCON_KEYS}
    interaction = {"Reactive": 0, "Balanced": 0, "Proactive": 0}

    for option in answers:
        for key, val in option["scores"].items():
            if key in engines:
                engines[key] += val
            elif key in gameplans:
                gameplans[key] += val
            elif key in wincons:
                wincons[key] += val
            elif key in interaction:
                interaction[key] += val

    return engines, gameplans, wincons, interaction


def top_n(scores: dict, n: int) -> list[tuple[str, int]]:
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)[:n]


def dominant_interaction(interaction: dict) -> str:
    # Add base Balanced weight so it's the default when not strongly signaled
    adjusted = dict(interaction)
    adjusted["Balanced"] += 2
    return max(adjusted, key=adjusted.get)


def build_profile_description(engine: str, gameplan: str, wincon: str) -> str:
    lines = [
        f"  Engine:    {engine} — {ENGINE_DESCRIPTIONS[engine]}",
        f"  Game plan: {gameplan} — {GAMEPLAN_DESCRIPTIONS[gameplan]}",
        f"  Win con:   {wincon} — {WINCON_DESCRIPTIONS[wincon]}",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_questionnaire() -> tuple[dict, dict, dict, dict]:
    print()
    print("=" * 60)
    print("  What kind of Commander player are you?")
    print("=" * 60)
    print()
    print("10 questions. No MTG knowledge required.")
    print("Pick the answer that feels most like you.")

    answers = []
    for i, q in enumerate(QUESTIONS, 1):
        print(f"\n--- Question {i} of {len(QUESTIONS)} ---")
        idx = ask_numbered(q["prompt"], q["options"])
        answers.append(q["options"][idx])

    return score_answers(answers)


def present_recommendations(
    engines: dict,
    gameplans: dict,
    wincons: dict,
    interaction: dict,
    surprise_mode: bool = False,
) -> dict:
    top_engines = top_n(engines, 3)
    top_gameplans = top_n(gameplans, 3)
    top_wincons = top_n(wincons, 3)
    top_interaction = dominant_interaction(interaction)

    # Build top 3 combos: combine rank scores
    candidates = []
    for e, es in top_engines:
        for g, gs in top_gameplans:
            for w, ws in top_wincons:
                candidates.append((e, g, w, es + gs + ws))

    candidates.sort(key=lambda x: x[3], reverse=True)
    top3 = candidates[:3]

    print()
    print("=" * 60)
    print("  Your Results")
    print("=" * 60)

    if surprise_mode:
        # Weighted random from top 3
        weights = [c[3] for c in top3]
        chosen = random.choices(top3, weights=weights, k=1)[0]
        engine, gameplan, wincon, _ = chosen

        print()
        print("SURPRISE PICK:")
        print()
        print(build_profile_description(engine, gameplan, wincon))
        print(f"  Interaction: {top_interaction} — {INTERACTION_DESCRIPTIONS[top_interaction]}")

        return {
            "engine": engine,
            "game_plan": gameplan,
            "win_con": wincon,
            "interaction": top_interaction,
        }

    # Show top 3 options
    print()
    print("Based on your answers, here are your top 3 deck profiles:")

    for rank, (engine, gameplan, wincon, _) in enumerate(top3, 1):
        print()
        print(f"  Option {rank}:")
        print(build_profile_description(engine, gameplan, wincon))
        print(f"  Interaction: {top_interaction} — {INTERACTION_DESCRIPTIONS[top_interaction]}")

    # Let them pick or go random
    print()
    print("Pick one, or let us choose:")
    print("  1) Option 1")
    print("  2) Option 2")
    print("  3) Option 3")
    print("  4) Surprise me — pick one randomly")

    while True:
        resp = input("\n> ").strip()
        if resp in ("1", "2", "3"):
            engine, gameplan, wincon, _ = top3[int(resp) - 1]
            break
        elif resp == "4":
            weights = [c[3] for c in top3]
            engine, gameplan, wincon, _ = random.choices(top3, weights=weights, k=1)[0]
            print(f"\nPicked: Option {top3.index((engine, gameplan, wincon, _) if (engine, gameplan, wincon, _) in top3 else top3[0]) + 1}")
            break
        print("  Enter 1, 2, 3, or 4.")

    print()
    print("Selected profile:")
    print(build_profile_description(engine, gameplan, wincon))

    return {
        "engine": engine,
        "game_plan": gameplan,
        "win_con": wincon,
        "interaction": top_interaction,
    }


def print_intake_summary(profile: dict) -> None:
    engine = profile["engine"]
    gameplan = profile["game_plan"]
    wincon = profile["win_con"]
    interaction = profile["interaction"]

    # Map win-con slug to intake.py win condition short form
    wincon_map = {
        "life-depletion":     "Life depletion",
        "commander-damage":   "Commander damage",
        "mill":               "Library depletion",
        "poison":             "Poison counters",
        "alternate-win-cons": "Alternate win condition",
    }
    gameplan_map = {
        "go-wide":  "Go Wide",
        "go-tall":  "Go Tall",
        "combo":    "Combo",
        "burn":     "Burn",
        "stax":     "Stax",
        "control":  "Control",
        "politics": "Politics",
    }

    print()
    print("=" * 60)
    print("  PLAYSTYLE PROFILE — paste this to the AI")
    print("=" * 60)
    print()
    print("## Playstyle Profile")
    print()
    print(f"- **Engine:** {engine}")
    print(f"- **Game plan:** {gameplan_map.get(gameplan, gameplan)}")
    print(f"- **Win condition:** {wincon_map.get(wincon, wincon)}")
    print(f"- **Interaction style:** {interaction}")
    print()
    print("Paste this block alongside your other intake answers (bracket, budget,")
    print("color preferences) when starting the ideation session.")
    print("The AI will use these as the starting point for commander recommendations.")
    print()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Playstyle discovery questionnaire for new Commander deck projects."
    )
    parser.add_argument(
        "--surprise-me",
        action="store_true",
        help="Skip the questionnaire entirely and pick a random profile.",
    )
    args = parser.parse_args()

    if args.surprise_me:
        # Full random — pick one valid combo at random
        engine = random.choice(list(ENGINE_KEYS))
        gameplan = random.choice(list(GAMEPLAN_KEYS))
        wincon = random.choice(list(WINCON_KEYS))
        interaction = random.choice(["Reactive", "Balanced", "Proactive"])

        print()
        print("=" * 60)
        print("  SURPRISE PICK")
        print("=" * 60)
        print()
        print(build_profile_description(engine, gameplan, wincon))
        print(f"  Interaction: {interaction} — {INTERACTION_DESCRIPTIONS[interaction]}")

        profile = {
            "engine": engine,
            "game_plan": gameplan,
            "win_con": wincon,
            "interaction": interaction,
        }
    else:
        engines, gameplans, wincons, interaction = run_questionnaire()
        profile = present_recommendations(engines, gameplans, wincons, interaction)

    print_intake_summary(profile)


if __name__ == "__main__":
    main()
