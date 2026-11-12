"""Current facts, explicit expiration, and a review gate for semantic rules changes."""
from datetime import datetime, timezone
import hashlib
import html
import json
from pathlib import Path
import re
import tempfile
import urllib.request

from data_sources import USER_AGENT

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / '_shared/current/commander.json'
POLICY = ROOT / '_system/data-policy.json'
REVIEW = ROOT / '_system/rules-review.json'


class FreshnessError(ValueError):
    pass


def utcnow():
    return datetime.now(timezone.utc)


def atomic_json(path, data):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent, delete=False) as stream:
        json.dump(data, stream, indent=2, ensure_ascii=False); stream.write('\n')
        temporary = Path(stream.name)
    temporary.replace(path)


def is_fresh(timestamp, hours, now=None):
    try:
        checked = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        age = ((now or utcnow()) - checked).total_seconds()
        return 0 <= age < hours * 3600
    except (ValueError, TypeError, AttributeError):
        return False


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def parse_official_page(body):
    # Parse only JSON string literals in the site's serialized topic/copy entries.
    # No JavaScript execution; missing sections fail the schema contract.
    pattern = r'topic:("(?:\\.|[^"\\])*"),copy:("(?:\\.|[^"\\])*")'
    entries = {json.loads(title): json.loads(copy) for title, copy in re.findall(pattern, body)}
    colors = ('White', 'Blue', 'Black', 'Red', 'Green', 'Multicolor', 'Colorless')
    groups = {}
    for color in colors:
        names = re.findall(r'<auto-card[^>]*>(.*?)</auto-card>', entries.get(color, ''), re.S)
        if not names:
            raise FreshnessError(f'Official Game Changers schema changed: missing {color}.')
        groups[color] = [html.unescape(re.sub('<[^>]+>', '', name)).strip() for name in names]
    names = [name for group in groups.values() for name in group]
    if not 20 <= len(names) <= 200 or len(set(names)) != len(names):
        raise FreshnessError('Official card-list size/duplicates failed validation; retain previous snapshot.')
    overview = entries.get('What are Game Changers?', '')
    if not all(fragment in overview for fragment in ('Bracket 1 and 2', 'up to three', 'unlimited')):
        raise FreshnessError('Official bracket caps changed; update parser after review.')
    words = {'four': 4, 'six': 6, 'eight': 8, 'nine': 9}
    brackets = {}
    review_content = {}
    for n in range(1, 6):
        matches = [(title, copy) for title, copy in entries.items() if title.startswith(f'Bracket {n}:')]
        if len(matches) != 1:
            raise FreshnessError(f'Official bracket {n} section missing/ambiguous.')
        title, copy = matches[0]
        turns = re.search(r'at least (\w+) turns', copy)
        expected = words.get(turns.group(1)) if turns else None
        if n < 5 and expected is None:
            raise FreshnessError('Official turn expectations changed; review required.')
        brackets[str(n)] = {'name': title.split(': ', 1)[1], 'expected_min_turns': expected,
                            'game_changers_max': 0 if n <= 2 else 3 if n == 3 else None}
        review_content[title] = copy
    # Include core rules, not surrounding product advertising, in the review hash.
    core_match = re.search(r'Play Rules/Modifiers(.*?)Different Ways to Play', body, re.S)
    if not core_match:
        raise FreshnessError('Official core rules section missing.')
    core = html.unescape(re.sub('<[^>]+>', ' ', core_match.group(1)))
    review_content['core'] = re.sub(r'\s+', ' ', core).strip()
    review_content['caps'] = overview
    return {'game_changers': groups, 'brackets': brackets, 'rules_hash': digest(review_content),
            'data_hash': digest({'groups': groups, 'brackets': brackets})}


def parse_official_bans(body):
    match = re.search(r'<h3>Commander Banned Cards</h3>(.*?)</article>', body, re.S)
    if not match:
        raise FreshnessError('Official Commander ban section missing.')
    section = match.group(1)
    lists = re.findall(r'<ul[^>]*class="list-links"[^>]*>(.*?)</ul>', section, re.S)
    if len(lists) != 1:
        raise FreshnessError('Official Commander named ban list schema changed.')
    clean = lambda value: html.unescape(re.sub('<[^>]+>', '', value)).strip()
    names = [clean(name) for name in re.findall(r'<li[^>]*>(.*?)</li>', lists[0], re.S)]
    if not 10 < len(names) < 200 or 'Black Lotus' not in names:
        raise FreshnessError('Official named ban list failed sanity checks.')
    conditions = [clean(item) for item in re.findall(r'<li[^>]*>(.*?)</li>', section[:section.index(lists[0])], re.S)]
    companion_bans = [item.split(' - ')[0] for item in conditions if 'only banned as a companion' in item]
    return {'banned_cards': names, 'companion_only_bans': companion_bans,
            'special_ban_categories': ['Conspiracy type', 'Playing for ante', 'Offensive depictions identified by Wizards'],
            'conditions_hash': digest(conditions)}


def refresh_rules():
    policy = json.loads(POLICY.read_text())
    req = urllib.request.Request(policy['source'], headers={'User-Agent': USER_AGENT, 'Accept': 'text/html'})
    with urllib.request.urlopen(req, timeout=20) as response:
        parsed = parse_official_page(response.read().decode('utf-8'))
    banned_req = urllib.request.Request(policy['banned_source'], headers={'User-Agent': USER_AGENT, 'Accept': 'text/html'})
    with urllib.request.urlopen(banned_req, timeout=20) as response:
        bans = parse_official_bans(response.read().decode('utf-8'))
    parsed['rules_hash'] = digest({'commander_rules': parsed['rules_hash'], 'conditional_bans': bans.pop('conditions_hash')})
    parsed.update(bans)
    parsed['banned_source'] = policy['banned_source']
    parsed.update(source=policy['source'], checked_at=utcnow().isoformat(), schema_version=1)
    # Only replace the previous good snapshot after all parsing succeeds.
    atomic_json(SNAPSHOT, parsed)
    generate_references(parsed)
    return parsed


def generate_references(data):
    stamp = f"Source: {data['source']}\nChecked: {data['checked_at']}\nGenerated by `_system/refresh-data.py`; do not hand-edit.\n"
    lines = ['# Current Game Changers', '', stamp]
    for color, names in data['game_changers'].items():
        lines += ['', f'## {color}'] + ['- ' + name for name in names]
    (ROOT / 'deckbuilding/docs/game-changers.md').write_text('\n'.join(lines) + '\n')
    lines = ['# Current Commander brackets', '', stamp,
             'Brackets are optional matchmaking guidance. Budget does not determine bracket.',
             'These facts do not certify strategy, combo timing or table expectations.', '',
             '| Bracket | Name | Game Changer limit | Expected minimum turns |', '|---|---|---|---|']
    for n, bracket in data['brackets'].items():
        limit = bracket['game_changers_max']
        lines.append(f"| {n} | {bracket['name']} | {limit if limit is not None else 'Unlimited'} | {bracket['expected_min_turns'] or 'Any turn'} |")
    lines += ['', 'Before building or validating, run `_system/refresh-data.py` or let the',
              'generator/validator check freshness. Expired data cannot support a current-rules claim.',
              'Review the linked official guidance for playstyle, extra turns, land denial and combos.']
    (ROOT / 'Ideation/docs/brackets.md').write_text('\n'.join(lines) + '\n')
    banned = ['# Current Commander named bans', '', f"Source: {data['banned_source']}", f"Checked: {data['checked_at']}", 'Generated by `_system/refresh-data.py`; do not hand-edit.', '']
    banned += ['- ' + name for name in data['banned_cards']]
    banned += ['', 'Additional category bans: Conspiracy cards, cards referring to playing for ante,', 'and offensive-depiction cards identified by Wizards. Live Scryfall legality is also checked.', 'Companion-only bans: ' + ', '.join(data['companion_only_bans']) + '. These are not blanket bans on the card.']
    (ROOT / 'deckbuilding/docs/banned-cards.md').write_text('\n'.join(banned) + '\n')


def current_rules(refresh=False):
    policy = json.loads(POLICY.read_text())
    try:
        data = json.loads(SNAPSHOT.read_text())
    except (OSError, ValueError):
        data = {}
    if refresh or not is_fresh(data.get('checked_at'), policy['commander_rules_hours']):
        try:
            data = refresh_rules()
        except Exception as error:
            raise FreshnessError(f'Rules are unavailable/expired; refresh failed: {error}. No current compliance claim is permitted.') from error
    try:
        reviewed = json.loads(REVIEW.read_text())
    except (OSError, ValueError):
        reviewed = {}
    if reviewed.get('rules_hash') != data.get('rules_hash'):
        raise FreshnessError('Official rules changed or have not been reviewed. Inspect the source and snapshot, then run refresh-data.py --accept-rules-hash HASH --review-note "what was checked".')
    return data
