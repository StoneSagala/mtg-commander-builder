"""Shared external-data contracts. Network failures are never evidence of absence."""
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request

USER_AGENT = 'MTGCommanderBuilder/0.2 (https://github.com/StoneSagala/mtg-commander-builder)'
TIMEOUT = 20


def request_json(url, payload=None):
    headers = {'User-Agent': USER_AGENT, 'Accept': 'application/json'}
    body = None
    if payload is not None:
        body = json.dumps(payload).encode('utf-8')
        headers['Content-Type'] = 'application/json'
    for attempt in range(3):
        time.sleep(0.12)
        try:
            with urllib.request.urlopen(urllib.request.Request(url, data=body, headers=headers), timeout=TIMEOUT) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            if error.code not in (429, 500, 502, 503, 504) or attempt == 2:
                raise
            try:
                delay = min(5, max(0, float(error.headers.get('Retry-After', 1))))
            except (ValueError, TypeError):
                delay = 1
            time.sleep(delay * (attempt + 1))


def slugify(name):
    return re.sub(r'[^a-z0-9]+', '-', re.sub(r"['’,.]", '', name.lower())).strip('-')


def edhrec_page(path):
    """EDHREC's public JSON feed; fail explicitly if its schema changes."""
    path = path.strip('/')
    if path.startswith('themes/'):
        path = 'tags/' + path[len('themes/'):]
    data = request_json('https://json.edhrec.com/pages/' + path + '.json')
    if not isinstance(data, dict) or not isinstance(data.get('container'), dict):
        raise ValueError('EDHREC schema changed: expected container object; this is not an unindexed commander.')
    return data


def commander_card(name):
    # Slugs are accepted at the CLI as well as full names.
    if ' ' not in name and '-' in name:
        name = name.replace('-', ' ')
    query = urllib.parse.urlencode({'fuzzy': name})
    card = request_json('https://api.scryfall.com/cards/named?' + query)
    text = card.get('oracle_text', '')
    if card.get('legalities', {}).get('commander') != 'legal':
        raise ValueError(f"{card.get('name', name)} is not legal in Commander.")
    types = card.get('type_line', '')
    if not ('Legendary' in types and ('Creature' in types or 'Vehicle' in types or 'Spacecraft' in types)) and 'can be your commander' not in text.lower():
        raise ValueError(f"{card.get('name', name)} needs a separate commander-eligibility review.")
    if 'color_identity' not in card:
        raise ValueError('Scryfall omitted color identity; refusing to assume colorless.')
    return card


def collection(names):
    """Deduplicate names, fetch at most 75 per POST, retain full card records."""
    names = list(dict.fromkeys(names))
    found = {}
    for start in range(0, len(names), 75):
        data = request_json('https://api.scryfall.com/cards/collection', {'identifiers': [{'name': n} for n in names[start:start + 75]]})
        for card in data.get('data', []):
            found[card['name'].casefold()] = card
            for face in card.get('card_faces', []):
                found[face['name'].casefold()] = card
    return found


def card_record(card, recommendation=None):
    recommendation = recommendation or {}
    possible = recommendation.get('potential_decks', 0)
    inclusion = recommendation.get('inclusion')
    if inclusion is None:
        inclusion = 100 * recommendation.get('num_decks', 0) / possible if possible else 0
    return {'name': card['name'], 'slug': slugify(card['name']),
            'deck_count': recommendation.get('num_decks', 0), 'inclusion_rate': inclusion,
            'synergy_score': recommendation.get('synergy', 0) or 0,
            'price_usd': card.get('prices', {}).get('usd'), 'cmc': card.get('cmc'),
            'type': card.get('type_line', ''), 'source': 'EDHREC + Scryfall' if recommendation else 'Scryfall fallback'}


def functional_categories(card):
    """Conservative text heuristics, not authoritative role or combo validation."""
    text = card.get('oracle_text', '').lower()
    if card.get('card_faces'):
        text += ' ' + ' '.join(f.get('oracle_text', '').lower() for f in card['card_faces'])
    text = re.sub(r'\([^)]*\)', '', text)
    types = card.get('type_line', '').split(' // ')[0]
    if 'Land' in types:
        return ['Lands'] if 'Basic' not in types else []
    categories = ['Theme Candidates']
    if re.search(r'add (?:\{|one mana|two mana|three mana|an amount|mana)', text) or ('search your library' in text and any(t in text for t in ('land', 'forest', 'plains', 'island', 'swamp', 'mountain')) and 'battlefield' in text):
        categories.append('Ramp')
    if re.search(r'draw (?:a|an|one|two|three|four|x|that many|cards)', text):
        categories.append('Card Draw')
    if re.search(r'(?:destroy|exile) all (?:creatures|nonland|permanents|artifacts)', text) or 'each creature gets -' in text:
        categories.append('Board Wipes')
    elif re.search(r'(?:destroy|exile|return) target', text):
        categories.append('Removal')
    if 'counter target' in text:
        categories.append('Counterspells')
    if 'search your library' in text and 'Ramp' not in categories:
        categories.append('Tutors')
    # Win conditions require strategy review; never infer a winning combo from text.
    return categories


def commander_pool(name, warn=None, strategies=(), partner=None):
    """Return (categories, authoritative commander, source). EDHREC is optional."""
    warn = warn or (lambda message: None)
    commander_cards = commander_group(name, partner)
    commander = dict(commander_cards[0])
    commander["commanders"] = commander_cards
    commander["color_identity"] = sorted({c for card in commander_cards for c in card["color_identity"]})
    identity = set(commander["color_identity"])
    recommendations = {}
    source = 'EDHREC + Scryfall'
    try:
        data = edhrec_page('commanders/' + slugify(commander['name']))
        lists = data['container'].get('json_dict', {}).get('cardlists', data.get('cardlists', []))
        for group in lists:
            if group.get('tag') in {'similarcommanders', 'topcommanders', 'newcommanders', 'partners', 'companions'}:
                continue
            for card in group.get('cardviews', []):
                if card.get('name'):
                    recommendations.setdefault(card['name'], card)
        if not recommendations:
            raise ValueError('EDHREC returned no recommendation cards (empty pool or schema change).')
    except (urllib.error.URLError, TimeoutError, ValueError, KeyError) as error:
        source = 'Scryfall fallback'
        warn(f'EDHREC unavailable: {error}. This does not establish that the commander is too new. Using a generic legal-color pool; strategy review is required.')
    if recommendations:
        cards = collection(recommendations)
        missing = [n for n in recommendations if n.casefold() not in cards]
        if missing:
            warn(f'Scryfall could not resolve {len(missing)} recommendations; omitted them.')
    else:
        colors = ''.join(commander['color_identity']).lower() or 'c'
        # Bounded, reproducible fallback; no invented EDHREC synergy scores.
        query = urllib.parse.urlencode({'q': f'legal:commander id<={colors} -t:basic', 'order': 'edhrec', 'unique': 'cards'})
        data = request_json('https://api.scryfall.com/cards/search?' + query)
        cards = {c['name'].casefold(): c for c in data.get('data', [])}
    if strategies:
        try:
            for card in strategy_cards(identity, strategies):
                cards.setdefault(card['name'].casefold(), card)
        except (urllib.error.URLError, ValueError, TimeoutError) as error:
            warn(f'Strategy search unavailable: {error}. Continue with the verified existing pool and review gaps.')
    categorized = {}
    seen = set()
    for card in cards.values():
        if card['name'] in seen or card['name'] in {c['name'] for c in commander_cards}:
            continue
        seen.add(card['name'])
        if card.get('legalities', {}).get('commander') != 'legal' or not set(card.get('color_identity', [])).issubset(identity):
            continue
        record = card_record(card, recommendations.get(card['name']))
        for category in functional_categories(card):
            categorized.setdefault(category, []).append(record)
    if not categorized:
        raise ValueError('No verified legal cards available. Check Scryfall connectivity; do not generate an unverified draft.')
    warn('Card roles use Scryfall text heuristics. Review roles, win conditions, bracket and total budget before finalizing.')
    return categorized, commander, source


def commander_group(name, partner=None):
    """Resolve a single commander or a verified Partner/Background pair."""
    first = commander_card(name)
    if not partner:
        return [first]
    # Backgrounds aren't individually commanders; the pair grants eligibility.
    query = urllib.parse.urlencode({'fuzzy': partner})
    second = request_json('https://api.scryfall.com/cards/named?' + query)
    if second.get('legalities', {}).get('commander') != 'legal' or 'color_identity' not in second:
        raise ValueError('Second commander is not verified legal or lacks color identity.')
    if first['name'] == second['name']:
        raise ValueError('Two commanders must be different cards.')
    texts = [c.get('oracle_text', '') for c in (first, second)]
    plain_partner = lambda text: bool(re.search(r'(?:^|\n)Partner(?:\s*\(|\s*$)', text))
    pair = (plain_partner(texts[0]) and plain_partner(texts[1]))
    pair |= all('Friends forever' in t for t in texts)
    pair |= all(('Partner with ' + other['name']) in text for text, other in zip(texts, (second, first)))
    pair |= ('choose a background' in texts[0].lower() and 'Legendary' in second.get('type_line', '') and 'Background' in second.get('type_line', ''))
    if not pair:
        raise ValueError('This commander pair is not a supported legal Partner/Friends forever/Background combination. Verify special pairing rules separately.')
    if 'Background' not in second.get('type_line', ''):
        # Don't let ordinary Partner text on a non-commander card grant eligibility.
        commander_card(second['name'])
    return [first, second]


STRATEGY_QUERIES = {
    'graveyard': '(o:"return target" o:graveyard OR o:mill)',
    'aristocrats': '(o:sacrifice o:"creature dies")',
    'artifacts': 'o:artifact', 'enchantress': 'o:enchantment',
    'spellslinger': '(o:"instant or sorcery" OR o:magecraft)',
    'tokens': 'o:"create" o:token', 'counters': 'o:"+1/+1 counter"',
    'lands': '(o:landfall OR o:"land enters")',
    'blink-etb': '(o:"enters" o:"exile")',
    'theft-chaos': '(o:"opponent" o:"cast" OR o:"combat damage" o:player)',
    'commander-damage': '(o:"can’t be blocked" OR o:"can\'t be blocked" OR o:"double strike")',
    'poison': '(o:toxic OR o:infect OR o:proliferate)',
    'mill': 'o:mill', 'life-depletion': '(o:"loses life" OR o:"lose life")',
    'alternate-win-cons': 'o:"win the game"',
    'control': '(o:"counter target" OR o:"destroy target")',
    'go-wide': '(o:token OR o:"creatures you control get")',
    'go-tall': '(o:equipment OR o:"enchanted creature")',
    'burn': 'o:"deals" o:damage', 'politics': '(o:monarch OR o:vote)',
    'stax': '(o:"can’t" OR o:"costs" o:"more")',
}


def strategy_cards(identity, strategies, max_pages=2):
    """Bounded targeted discovery; no fake synergy or claim of verified win lines."""
    terms = list(dict.fromkeys(STRATEGY_QUERIES[s] for s in strategies if s in STRATEGY_QUERIES))
    if not terms:
        return []
    colors = ''.join(identity).lower() or 'c'
    query = urllib.parse.urlencode({'q': f'legal:commander id<={colors} -t:basic (' + ' OR '.join(terms) + ')', 'order': 'edhrec', 'unique': 'cards'})
    url = 'https://api.scryfall.com/cards/search?' + query
    cards = []
    for _ in range(max_pages):
        data = request_json(url)
        if not isinstance(data.get('data'), list):
            raise ValueError('Scryfall strategy search schema changed.')
        cards += data['data']
        if not data.get('has_more'):
            break
        url = data['next_page']
    return cards
