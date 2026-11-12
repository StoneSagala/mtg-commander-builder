#!/usr/bin/env python3
"""Live provider and freshness checks. JSON stdout; nonzero if required providers fail."""
import argparse
import datetime
import importlib.util
import json
from pathlib import Path
import sys
import urllib.error
import urllib.parse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '_shared'))
from data_sources import request_json, edhrec_page, commander_card, collection


def module(relative):
    spec = importlib.util.spec_from_file_location(Path(relative).stem, ROOT / relative)
    result = importlib.util.module_from_spec(spec); spec.loader.exec_module(result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--commander', default='Kotis, the Fangkeeper')
    parser.add_argument('--archidekt-deck', default='21089859', help='Public known-positive deck ID')
    parser.add_argument('--moxfield-deck', help='Optional public ID for a real direct-import check')
    args = parser.parse_args()
    results = []

    def check(name, required, run, summarize):
        try:
            data = run()
            detail = summarize(data)
            results.append({'name': name, 'required': required, 'status': 'pass', 'detail': detail})
        except Exception as error:
            results.append({'name': name, 'required': required, 'status': 'blocked' if getattr(error, 'code', None) == 403 else 'fail', 'detail': str(error)})

    from freshness import current_rules
    check("Current official rules", True, current_rules, lambda d: {"checked_at": d["checked_at"], "named_bans": len(d["banned_cards"]), "game_changers": sum(map(len, d["game_changers"].values()))})
    check('Scryfall commander', True, lambda: commander_card(args.commander), lambda d: {k: d[k] for k in ('name', 'released_at', 'color_identity')})
    check('Scryfall collection POST', True, lambda: collection(['Sol Ring', 'Command Tower']), lambda d: {'resolved': len(d)} if len(d) == 2 else (_ for _ in ()).throw(ValueError('Missing expected collection records')))
    check('Scryfall search', True, lambda: request_json('https://api.scryfall.com/cards/search?' + urllib.parse.urlencode({'q': 'legal:commander id<=bug -t:basic', 'order': 'edhrec'})), lambda d: {'cards': len(d['data']), 'total': d['total_cards']})
    from data_sources import slugify
    def page_summary(d):
        lists = d['container']['json_dict']['cardlists']
        if not lists or not any(c.get('cardviews') for c in lists):
            raise ValueError('No cardviews in EDHREC response')
        return {'lists': len(lists), 'entries': sum(len(c.get('cardviews', [])) for c in lists)}
    for path in ['commanders/' + slugify(args.commander), 'commanders/meren-of-clan-nel-toth', 'tags', 'tags/graveyard', 'tags/graveyard/golgari', 'cards/sol-ring', 'commanders/year']:
        check('EDHREC ' + path, False, lambda path=path: edhrec_page(path), page_summary)
    def import_summary(d):
        if not d.get('mainboard') or not d.get('commanders'):
            raise ValueError('Imported deck has no mainboard or commander; inspect the provider schema.')
        return {'name': d['name'], 'mainboard_entries': len(d['mainboard']), 'commanders': d['commanders']}

    refs = module('deckbuilding/scripts/fetch-reference-lists.py')
    check('Archidekt search', False, lambda: refs.archidekt_search(args.commander, top_n=1), lambda d: {'results': len(d), 'first_id': d[0]['id']} if d else (_ for _ in ()).throw(ValueError('Known-positive search empty')))
    check('Archidekt import', False, lambda: module('optimization/scripts/fetch-deck.py').fetch_archidekt(args.archidekt_deck), import_summary)
    check('Moxfield search', False, lambda: refs.moxfield_search(args.commander, top_n=1), lambda d: {'results': len(d)})
    if args.moxfield_deck:
        check('Moxfield import', False, lambda: module('optimization/scripts/fetch-deck.py').fetch_moxfield(args.moxfield_deck), import_summary)
    else:
        results.append({'name': 'Moxfield import', 'required': False, 'status': 'not-tested', 'detail': 'No known-positive public deck ID supplied; no fabricated ID used.'})
    check('Commander Spellbook', False, lambda: request_json('https://backend.commanderspellbook.com/variants/?' + urllib.parse.urlencode({'q': 'card:"Sol Ring"', 'limit': 1})), lambda d: {'variants': len(d['results'])} if d.get('results') else (_ for _ in ()).throw(ValueError('Known combo search empty')))
    from combos import find_deck
    def combo_summary(report):
        if not report['complete'] or not report['variants']:
            raise ValueError('Known-positive deck combo check incomplete/empty: ' + str(report['errors']))
        return {'complete': report['complete'], 'variants': len(report['variants']), 'pages': report['pages']}
    check('Spellbook deck search POST', False, lambda: find_deck(["Thassa's Oracle", 'Demonic Consultation'], [args.commander]), combo_summary)
    print(json.dumps({'checked_at': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'commander': args.commander, 'checks': results}, indent=2))
    return int(any(r['required'] and r['status'] != 'pass' for r in results))


if __name__ == '__main__':
    sys.exit(main())
