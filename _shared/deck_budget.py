"""A player's optional total-deck budget. No shared default spending limit."""
from decimal import Decimal, InvalidOperation, ROUND_UP
import urllib.parse
from data_sources import collection, request_json


def cents(value):
    if value is None:
        return None
    try:
        amount = Decimal(str(value))
        if not amount.is_finite() or amount < 0:
            return None
        return int((amount * 100).quantize(Decimal('1'), rounding=ROUND_UP))
    except (InvalidOperation, ValueError):
        return None


def price_cards(names):
    """Use live Scryfall USD estimates; try a priced paper printing for null USD."""
    names = list(dict.fromkeys(names))
    records = collection(names)
    prices = {}
    for name in names:
        card = records.get(name.casefold(), {})
        amount = cents(card.get('prices', {}).get('usd'))
        if amount is None:
            escaped = name.replace('"', '\\"')
            query = urllib.parse.urlencode({'q': f'!"{escaped}" game:paper usd>=0', 'order': 'usd', 'dir': 'asc', 'unique': 'prints'})
            try:
                result = request_json('https://api.scryfall.com/cards/search?' + query)
                amount = next((p for c in result.get('data', []) if (p := cents(c.get('prices', {}).get('usd'))) is not None), None)
            except Exception:
                # Unknown stays unknown. Never use an assumed zero price.
                amount = None
        prices[name] = amount
    return prices


def constrain_deck(sections, basics, commanders, limit, prices):
    """Keep a complete land base and choose affordable spell candidates.

    Existing selected spells are processed cheapest first, then output in original
    section order. Missing slots remain explicit; a partial deck never claims complete.
    """
    if limit is None:
        return sections, {'limit_usd': None, 'status': 'unrestricted'}
    ceiling = cents(limit)
    if ceiling is None:
        raise ValueError('Budget must be a finite nonnegative USD amount, or omitted for no limit.')
    base = [(name, 1) for name in commanders] + list(basics.items())
    base += [(name, 1) for name in sections['Utility Lands']]
    missing = [name for name, _ in base if prices.get(name) is None]
    if missing:
        raise ValueError('Cannot verify total budget: missing commander/land prices: ' + ', '.join(missing))
    spent = sum(prices[name] * quantity for name, quantity in base)
    # Expensive nonbasic lands can be replaced with their already-priced basic slots
    # by the caller before this function; never silently claim a forced land cost fits.
    if spent > ceiling:
        raise ValueError(f'Commander and mana base cost ${spent / 100:.2f}, above the player budget ${ceiling / 100:.2f}. Choose cheaper lands/commander or change this deck\'s budget.')
    spells = [(name, section, i) for section, names in sections.items() if section != 'Utility Lands' for i, name in enumerate(names)]
    accepted = set()
    omitted = []
    for name, section, index in sorted(spells, key=lambda row: (prices.get(row[0]) is None, prices.get(row[0]) or 0, row[0])):
        amount = prices.get(name)
        if amount is not None and spent + amount <= ceiling:
            accepted.add(name); spent += amount
        else:
            omitted.append({'name': name, 'reason': 'price unknown' if amount is None else 'total budget exceeded'})
    result = {section: list(names) if section == 'Utility Lands' else [n for n in names if n in accepted] for section, names in sections.items()}
    return result, {'limit_usd': ceiling / 100, 'estimated_total_usd': spent / 100, 'status': 'within supplied total budget', 'omitted': omitted, 'price_basis': 'live Scryfall USD paper estimates; not a purchase quote'}
