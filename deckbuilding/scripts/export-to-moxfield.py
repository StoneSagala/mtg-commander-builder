#!/usr/bin/env python3
"""
export-to-moxfield.py — Copy a brew file to clipboard in Moxfield import format.

Parses a brew/draft file and copies all cards as a plain list to the clipboard,
ready to paste directly into Moxfield's deck import. No section headers — just
"quantity CardName" per line, one card per line.

Usage:
    python deckbuilding/scripts/export-to-moxfield.py \
        --file deckbuilding/brews/deck-draft.md \
        --commander "Commander Name"

    python deckbuilding/scripts/export-to-moxfield.py \
        --file deckbuilding/brews/deck-draft.md \
        --commander "Commander Name" \
        --print
"""

import sys
import re
import argparse
import subprocess
import platform

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')


def parse_decklist(filepath):
    """
    Parse a brew file. Returns list of (qty, name) tuples, excluding the commander section.
    Commander is supplied separately via --commander.
    """
    entries = []

    with open(filepath, encoding="utf-8") as f:
        lines = f.readlines()

    in_commander_section = False
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#") or stripped.startswith("//") or stripped.startswith("<!--"):
            continue

        if re.match(r"^Commander\s*:", stripped, re.IGNORECASE):
            in_commander_section = True
            continue
        if re.match(r"^(Lands|Creatures|Spells|Ramp|Card Draw|Utility|Win|Theme|Theft|Synergy|Interaction|Protection)\b", stripped, re.IGNORECASE):
            in_commander_section = False

        parts = stripped.split(None, 1)
        if len(parts) == 2:
            qty_str = parts[0].rstrip("x")
            if qty_str.isdigit() and not in_commander_section:
                entries.append((int(qty_str), parts[1].strip()))

    return entries


def copy_to_clipboard(text):
    """Copy text to system clipboard. Returns True on success."""
    system = platform.system()
    try:
        if system == "Windows":
            subprocess.run(["clip"], input=text.encode("utf-8"), check=True)
        elif system == "Darwin":
            subprocess.run(["pbcopy"], input=text.encode("utf-8"), check=True)
        else:
            try:
                subprocess.run(["xclip", "-selection", "clipboard"],
                               input=text.encode("utf-8"), check=True)
            except FileNotFoundError:
                subprocess.run(["xsel", "--clipboard", "--input"],
                               input=text.encode("utf-8"), check=True)
        return True
    except Exception as e:
        print(f"  Clipboard error: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Export a brew file to Moxfield clipboard format."
    )
    parser.add_argument("--file", required=True, metavar="PATH",
                        help="Path to the brew file")
    parser.add_argument("--commander", required=True, metavar="NAME",
                        help="Commander card name")
    parser.add_argument("--print", action="store_true", dest="print_list",
                        help="Print the list to stdout instead of copying to clipboard")
    args = parser.parse_args()

    entries = parse_decklist(args.file)

    # Commander goes first
    all_entries = [(1, args.commander)] + entries
    lines = [f"{qty} {name}" for qty, name in all_entries]
    text = "\n".join(lines)
    total = sum(qty for qty, _ in all_entries)

    if args.print_list:
        print(text)
        return

    print(f"  {total} cards ready for Moxfield.")
    success = copy_to_clipboard(text)
    if success:
        print(f"  Copied to clipboard — paste into Moxfield's deck import.")
    else:
        print(f"\n  Clipboard unavailable. Copy this manually:\n")
        print(text)


if __name__ == "__main__":
    main()
