#!/usr/bin/env python3
"""
fetch-edhrec-data.py — Fetch theme and commander data from EDHREC.

Usage:
  # Flow A: Theme -> Colors -> Commanders
  python fetch-edhrec-data.py --themes
  python fetch-edhrec-data.py --theme graveyard
  python fetch-edhrec-data.py --theme graveyard --color golgari

  # Flow B: Commander -> Themes
  python fetch-edhrec-data.py --commander "meren-of-clan-nel-toth"
"""

import sys
import json
import re
import time
import argparse
import urllib.request
import urllib.parse
import urllib.error

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

EDHREC_BASE = "https://edhrec.com"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


def fetch_page(path):
    """Fetch an EDHREC page and extract __NEXT_DATA__."""
    time.sleep(0.2)
    url = f"{EDHREC_BASE}{path}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req) as resp:
        html = resp.read().decode("utf-8")
    match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
    if not match:
        raise ValueError(f"No NEXT_DATA found at {url}")
    return json.loads(match.group(1))["props"]["pageProps"]["data"]


def get_all_themes():
    """
    Get all available tags (themes + typal) from EDHREC's /tags page,
    sorted by deck count. Slug is extracted from each entry's url field.
    """
    data = fetch_page("/tags")
    cardlists = data["container"]["json_dict"]["cardlists"]
    tags_list = next(
        (cl for cl in cardlists if cl.get("tag") == "tagsbypopularitysort"), None
    )
    if not tags_list:
        raise ValueError("Could not find tags list in /tags page")
    results = []
    for t in tags_list["cardviews"]:
        # url is "/tags/tokens" — extract slug from path
        slug = t["url"].rsplit("/", 1)[-1]
        results.append({"slug": slug, "name": t["name"], "count": t["num_decks"]})
    return results


def get_theme_colors(theme_slug):
    """
    Given a theme slug, return all color combinations that support it,
    sorted by deck count (most popular first).
    """
    data = fetch_page(f"/themes/{theme_slug}")
    results = []
    for section in data.get("related_info", []):
        for item in section["items"]:
            results.append({
                "color_name": item["textLeft"],
                "colors": item["colors"],
                "deck_count": item["count"],
                "url": item["url"],
                "section": section["header"],
            })
    return sorted(results, key=lambda x: x["deck_count"], reverse=True)


def get_theme_commanders(theme_slug, color_slug):
    """
    Given a theme slug and color slug (e.g. 'golgari'), return top commanders.
    """
    data = fetch_page(f"/tags/{theme_slug}/{color_slug}")
    cardlists = data.get("container", {}).get("json_dict", {}).get("cardlists", [])
    top = []
    new = []
    for cl in cardlists:
        if cl.get("tag") == "topcommanders":
            top = cl.get("cardviews", [])
        elif cl.get("tag") == "newcommanders":
            new = cl.get("cardviews", [])
    return {
        "top_commanders": [
            {"name": c["name"], "slug": c["sanitized"], "deck_count": c["num_decks"]}
            for c in top
        ],
        "new_commanders": [
            {"name": c["name"], "slug": c["sanitized"], "deck_count": c["num_decks"]}
            for c in new
        ],
    }


def get_commander_themes(commander_slug):
    """
    Given a commander slug, return their associated themes (taglinks)
    sorted by deck count.
    """
    data = fetch_page(f"/commanders/{commander_slug}")
    taglinks = data.get("panels", {}).get("taglinks", [])
    return [
        {"slug": t["slug"], "name": t["value"], "deck_count": t["count"]}
        for t in taglinks
    ]


def slugify(name):
    """Convert a commander name to an EDHREC slug."""
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def print_themes(themes):
    print(f"\n{'='*50}")
    print(f"  EDHREC Strategy Themes ({len(themes)} total)")
    print(f"{'='*50}")
    for t in themes:
        print(f"  {t['name']:<30} ({t['count']:,} decks)  slug: {t['slug']}")


def print_theme_colors(theme_slug, colors):
    print(f"\n{'='*50}")
    print(f"  Color Options for Theme: {theme_slug}")
    print(f"{'='*50}")
    for c in colors[:15]:  # Show top 15 by popularity
        color_str = "/".join(c["colors"]).upper() if c["colors"] else "Colorless"
        print(f"  {c['color_name']:<20} {c['deck_count']:>6,} decks  ({color_str})")


def print_commanders(theme_slug, color_slug, data):
    print(f"\n{'='*50}")
    print(f"  Top Commanders: {theme_slug} / {color_slug}")
    print(f"{'='*50}")
    for c in data["top_commanders"][:10]:
        print(f"  {c['name']:<40} {c['deck_count']:>5,} decks")
    if data["new_commanders"]:
        print(f"\n  New Commanders:")
        for c in data["new_commanders"][:5]:
            print(f"  {c['name']:<40} {c['deck_count']:>5,} decks")


def print_commander_themes(commander_slug, themes):
    print(f"\n{'='*50}")
    print(f"  Themes for Commander: {commander_slug}")
    print(f"{'='*50}")
    for t in themes:
        print(f"  {t['name']:<30} {t['deck_count']:>5,} decks")


def main():
    parser = argparse.ArgumentParser(description="Fetch EDHREC theme and commander data.")
    parser.add_argument("--themes", action="store_true",
                        help="List all available strategy themes")
    parser.add_argument("--theme", metavar="SLUG",
                        help="Show color options for a theme (e.g. 'graveyard')")
    parser.add_argument("--color", metavar="SLUG",
                        help="Show commanders for a theme+color (e.g. 'golgari'). Use with --theme.")
    parser.add_argument("--commander", metavar="SLUG",
                        help="Show themes for a specific commander (e.g. 'meren-of-clan-nel-toth')")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args()

    try:
        if args.themes:
            themes = get_all_themes()
            if args.format == "json":
                print(json.dumps(themes, indent=2))
            else:
                print_themes(themes)

        elif args.theme and args.color:
            data = get_theme_commanders(args.theme, args.color)
            if args.format == "json":
                print(json.dumps(data, indent=2))
            else:
                print_commanders(args.theme, args.color, data)

        elif args.theme:
            colors = get_theme_colors(args.theme)
            if args.format == "json":
                print(json.dumps(colors, indent=2))
            else:
                print_theme_colors(args.theme, colors)

        elif args.commander:
            slug = slugify(args.commander) if " " in args.commander else args.commander
            themes = get_commander_themes(slug)
            if args.format == "json":
                print(json.dumps(themes, indent=2))
            else:
                print_commander_themes(slug, themes)

        else:
            parser.print_help()

    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code}: {e.reason}")
        sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
