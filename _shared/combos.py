"""Bounded Commander Spellbook searches with explicit completion status."""
from collections import Counter
from datetime import datetime, timezone
import urllib.parse
from data_sources import request_json

BASE = 'https://backend.commanderspellbook.com'


def paged(path, payload=None, max_pages=10):
    url = BASE + path
    found = {}
    report = {'complete': False, 'pages': 0, 'errors': [], 'checked_at': datetime.now(timezone.utc).isoformat()}
    seen = set()
    for _ in range(max_pages):
        if url in seen or urllib.parse.urlparse(url).netloc != urllib.parse.urlparse(BASE).netloc or not url.startswith('https://'):
            report['errors'].append('Unexpected or looping pagination URL'); break
        seen.add(url)
        try:
            data = request_json(url, payload)
            results = data['results']
            variants = results.get('included') if isinstance(results, dict) else results
            if not isinstance(variants, list):
                raise ValueError('Spellbook schema changed; included variants missing')
            for variant in variants:
                found[variant['id']] = variant
            report['pages'] += 1
            url = data.get('next')
            if not url:
                report['complete'] = True; break
        except Exception as error:
            report['errors'].append(str(error)); break
    if url and not report['complete'] and not report['errors']:
        report['errors'].append(f'Pagination stopped at {max_pages} pages; results incomplete')
    report['variants'] = list(found.values())
    report['scope'] = 'Known database variants, not a proof of all possible interactions'
    return report


def find_deck(main, commanders=(), max_pages=10):
    payload = {'main': [{'card': name, 'quantity': quantity} for name, quantity in Counter(main).items()],
               'commanders': [{'card': name, 'quantity': quantity} for name, quantity in Counter(commanders).items()]}
    return paged('/find-my-combos?limit=100', payload, max_pages)


def find_cards(names, max_pages=10):
    query = urllib.parse.urlencode({'q': ' '.join('card:"' + n.replace('"', '\\"') + '"' for n in names), 'limit': 100})
    return paged('/variants/?' + query, max_pages=max_pages)


def parse_deck(path):
    main, commanders = [], []
    destination = main
    import re
    from pathlib import Path
    for line in Path(path).read_text().splitlines():
        line = line.strip()
        if line.startswith('## '):
            break
        if line.lower() == 'commander:':
            destination = commanders; continue
        if line.endswith(':'):
            destination = main; continue
        match = re.match(r'^(\d+)[xX]?\s+(.+)$', line)
        if match:
            destination.extend([match[2]] * int(match[1]))
    return main, commanders
