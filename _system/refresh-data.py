#!/usr/bin/env python3
"""Refresh official data; accept a rule hash only after inspecting the cited source."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '_shared'))
import freshness


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--accept-rules-hash', help='Exact reviewed hash; never automatically accepted')
    parser.add_argument('--review-note', help='Record what a human/maintainer checked')
    parser.add_argument('--all', action='store_true', help='Also refresh optional theme and popularity caches')
    args = parser.parse_args()
    data = freshness.refresh_rules()
    if args.accept_rules_hash:
        if args.accept_rules_hash != data['rules_hash'] or not args.review_note:
            parser.error('Acceptance needs the current exact hash and a review note.')
        freshness.atomic_json(freshness.REVIEW, {'rules_hash': data['rules_hash'], 'reviewed_at': freshness.utcnow().isoformat(), 'note': args.review_note})
    caches = {}
    if args.all:
        import importlib.util
        def load(path):
            spec = importlib.util.spec_from_file_location(Path(path).stem, ROOT / path)
            module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
            return module
        themes = load('Ideation/scripts/match-themes.py').get_themes(refresh=True)
        popularity = load('Ideation/scripts/fetch-top-commanders.py').current_cache(refresh=True)
        caches = {'themes': len(themes), 'popularity': popularity['count']}
    print(json.dumps({'rules_hash': data['rules_hash'], 'checked_at': data['checked_at'], 'game_changers': sum(map(len, data['game_changers'].values())), 'banned_cards': len(data['banned_cards']), 'caches': caches}, indent=2))
    freshness.current_rules()


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError) as error:
        print(str(error), file=sys.stderr); sys.exit(1)
