#!/usr/bin/env python3
"""Refresh EDHREC's current yearly top-100 snapshot. No browser dependency."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / '_shared'))
from data_sources import edhrec_page
from freshness import atomic_json, is_fresh, utcnow

CACHE_FILE = Path(__file__).parent / '_cache/top-commanders-cache.json'
POLICY = ROOT / '_system/data-policy.json'


def fetch_top_commanders(target=100):
    if not 1 <= target <= 100:
        raise ValueError('The current JSON source provides at most 100 commanders. Choose --count 1..100; do not invent ranks beyond the source.')
    data = edhrec_page('commanders/year')
    lists = data['container']['json_dict']['cardlists']
    cards = [c for group in lists for c in group.get('cardviews', [])]
    if len(cards) < target:
        raise ValueError(f'Popularity source returned only {len(cards)} entries; requested {target}.')
    return [{'name': c['name'], 'decks': c.get('num_decks'), 'rank': i + 1} for i, c in enumerate(cards[:target])]


def save_cache(commanders):
    data = {'fetched_at': utcnow().isoformat(), 'source': 'https://json.edhrec.com/pages/commanders/year.json',
            'period': 'year', 'count': len(commanders), 'commanders': commanders}
    atomic_json(CACHE_FILE, data)
    return data


def load_cache():
    try:
        data = json.loads(CACHE_FILE.read_text())
        hours = json.loads(POLICY.read_text())['popularity_hours']
        return data if is_fresh(data.get('fetched_at'), hours) else None
    except (OSError, ValueError):
        return None


def current_cache(refresh=False, count=100):
    data = None if refresh else load_cache()
    if data is None or data['count'] < count:
        data = save_cache(fetch_top_commanders(count))
    return data


def check_commander(name):
    data = current_cache()
    # A short alias is ambiguous: use exact names for a popularity decision.
    match = next((c for c in data['commanders'] if c['name'].casefold() == name.casefold()), None)
    return (True, match['rank']) if match else (False, None)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--count', type=int, default=100)
    parser.add_argument('--refresh', action='store_true')
    parser.add_argument('--check')
    parser.add_argument('--list', action='store_true')
    args = parser.parse_args()
    data = current_cache(args.refresh, args.count)
    if args.check:
        found, rank = check_commander(args.check)
        print(f'{args.check}: rank {rank}' if found else f'{args.check}: absent from this current top-{data["count"]} snapshot; no existence or power-level inference')
        return
    print(json.dumps(data, indent=2))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError) as error:
        print(f'Popularity refresh failed: {error}. Expired data is not used.', file=sys.stderr)
        sys.exit(1)
