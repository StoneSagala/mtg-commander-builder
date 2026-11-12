import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '_shared'))
import data_sources as sources


def load(relative):
    spec = importlib.util.spec_from_file_location(Path(relative).stem, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def card(name='Test Commander', colors=None, text='', types='Legendary Creature — Human'):
    return {'name': name, 'color_identity': ['B', 'G', 'U'] if colors is None else colors,
            'legalities': {'commander': 'legal'}, 'type_line': types, 'oracle_text': text, 'prices': {'usd': '1.00'}}


class DataSourceTests(unittest.TestCase):
    def test_json_feed_replaces_page_html(self):
        with patch.object(sources, 'request_json', return_value={'container': {}}) as request:
            sources.edhrec_page('/commanders/kotis-the-fangkeeper')
        self.assertEqual(request.call_args.args[0], 'https://json.edhrec.com/pages/commanders/kotis-the-fangkeeper.json')

    def test_schema_drift_is_not_absence(self):
        with patch.object(sources, 'request_json', return_value={'changed': True}):
            with self.assertRaisesRegex(ValueError, 'schema changed'):
                sources.edhrec_page('tags')

    def test_scryfall_failure_does_not_assume_colorless(self):
        with patch.object(sources, 'request_json', side_effect=URLError('offline')):
            with self.assertRaises(URLError):
                sources.commander_pool('Kotis')

    def test_edhrec_404_and_outage_use_labelled_legal_fallback(self):
        for error in (HTTPError('url', 404, 'Not Found', {}, None), URLError('offline')):
            warnings = []
            with patch.object(sources, 'commander_card', return_value=card()), patch.object(sources, 'edhrec_page', side_effect=error), patch.object(sources, 'request_json', return_value={'data': [card('Good', text='Draw two cards.'), card('Off-color', ['R']), card()]}):
                pool, commander, source = sources.commander_pool('Kotis', warnings.append)
            self.assertEqual(source, 'Scryfall fallback')
            self.assertEqual([c['name'] for c in pool['Card Draw']], ['Good'])
            self.assertEqual(pool['Card Draw'][0]['synergy_score'], 0)
            self.assertIn('does not establish', warnings[0])

    def test_empty_edhrec_pool_uses_fallback(self):
        with patch.object(sources, 'commander_card', return_value=card()), patch.object(sources, 'edhrec_page', return_value={'container': {}}), patch.object(sources, 'request_json', return_value={'data': [card('Good')]}):
            self.assertEqual(sources.commander_pool('Kotis')[2], 'Scryfall fallback')

    def test_nonlegal_and_off_color_cards_removed(self):
        banned = card('Banned'); banned['legalities']['commander'] = 'banned'
        records = {c['name'].casefold(): c for c in [card('Good'), banned, card('Red', ['R'])]}
        page = {'container': {'json_dict': {'cardlists': [{'tag': 'creatures', 'cardviews': [{'name': n} for n in ['Good', 'Banned', 'Red']]}]}}}
        with patch.object(sources, 'commander_card', return_value=card()), patch.object(sources, 'edhrec_page', return_value=page), patch.object(sources, 'collection', return_value=records):
            pool, _, _ = sources.commander_pool('Kotis')
        self.assertEqual([c['name'] for c in pool['Theme Candidates']], ['Good'])

    def test_batch_deduplication_and_limit(self):
        with patch.object(sources, 'request_json', return_value={'data': []}) as request:
            sources.collection([f'Card {n}' for n in range(76)] + ['Card 0'])
        self.assertEqual([len(c.args[1]['identifiers']) for c in request.call_args_list], [75, 1])

    def test_roles_avoid_treasure_reminder_false_positive(self):
        offer = card(text='Counter target noncreature spell. Its controller creates two Treasure tokens. (They are artifacts with “{T}, Sacrifice this artifact: Add one mana of any color.”)')
        self.assertNotIn('Ramp', sources.functional_categories(offer))
        self.assertIn('Ramp', sources.functional_categories(card(text='Search your library for a Forest card, put that card onto the battlefield, then shuffle.')))

    def test_inclusion_derived_from_counts(self):
        self.assertEqual(sources.card_record(card(), {'num_decks': 5, 'potential_decks': 20})['inclusion_rate'], 25)

    def test_timeout_and_retry_429(self):
        response = io.StringIO(json.dumps({'ok': True}))
        with patch.object(sources.urllib.request, 'urlopen', side_effect=[HTTPError('url', 429, 'rate', {'Retry-After': '0'}, None), response]) as request, patch.object(sources.time, 'sleep'):
            self.assertTrue(sources.request_json('https://example.com')['ok'])
            self.assertEqual(request.call_args.kwargs['timeout'], 20)


class WorkflowTests(unittest.TestCase):
    def test_interaction_target_includes_wipes_once(self):
        module = load('deckbuilding/scripts/generate-starter-deck.py')
        targets = module.calculate_targets(3, 'graveyard', 'control', 'mill')
        pool = {'Board Wipes': [{'name': f'Wipe {n}'} for n in range(4)], 'Removal': [{'name': f'Removal {n}'} for n in range(20)]}
        sections, _ = module.build_deck('Commander', targets, pool, ['G'])
        self.assertEqual(len(sections['Interaction']), targets['interaction'])

    def test_generator_refuses_existing_brief_before_network(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / 'brief.md'; output.write_text('approved brief')
            result = subprocess.run([sys.executable, str(ROOT / 'deckbuilding/scripts/generate-starter-deck.py'), '--commander', 'Kotis', '--bracket', '3', '--engine', 'theft-chaos', '--game-plan', 'go-tall', '--win-con', 'commander-damage', '--output', str(output)], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(output.read_text(), 'approved brief')
            self.assertIn('Output already exists', result.stderr)

    def test_archidekt_search_contract(self):
        module = load('deckbuilding/scripts/fetch-reference-lists.py')
        with patch.object(module, 'http_get', return_value={'results': []}) as request:
            module.archidekt_search('Kotis, the Fangkeeper')
        self.assertTrue(request.call_args.args[0].endswith('/decks/v3/'))
        self.assertEqual(request.call_args.kwargs['params']['deckFormat'], 3)

    def test_optional_moxfield_timeout_does_not_block_archidekt(self):
        module = load('deckbuilding/scripts/fetch-reference-lists.py')
        with patch.object(module, 'moxfield_search', side_effect=TimeoutError('offline')), patch.object(module, 'archidekt_search', return_value=[]):
            self.assertEqual(module.fetch_all('Kotis', 'all', 'views', 1, False), [])

    def test_spellbook_endpoint(self):
        module = load('deckbuilding/scripts/validate-combos.py')
        with patch.object(module, 'find_cards', return_value={'complete': True, 'variants': []}) as request:
            module.search_combos_by_card('Sol Ring')
        self.assertEqual(request.call_args.args[0], ['Sol Ring'])

class ValidationRegressionTests(unittest.TestCase):
    def test_tutors_header_ends_commander_section(self):
        validator = load('deckbuilding/scripts/validate-deck.py')
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'deck.md'
            path.write_text('Commander:\n1 Kotis, the Fangkeeper\n\nTutors (1):\n1 Demonic Tutor\nLands (2):\n2 Forest\n')
            self.assertEqual(validator.parse_decklist(path), ['Demonic Tutor', 'Forest', 'Forest'])

    def test_optimizer_parser_accepts_generated_sections(self):
        validator = load('optimization/scripts/validate-decklist.py')
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'deck.md'
            path.write_text('# Deck\nCommander:\n1 Kotis, the Fangkeeper\n\nLands (2):\n2 Forest\nRamp (1):\n1 Sol Ring\n## Draft Coverage\n- Total: 4/100\n')
            main, side, commander = validator.parse_decklist(path)
            self.assertEqual(commander, 'Kotis, the Fangkeeper')
            self.assertEqual(dict(main), {'Forest': 2, 'Sol Ring': 1})

    def test_budget_unknown_is_not_pass(self):
        validator = load('deckbuilding/scripts/validate-deck.py')
        self.assertFalse(validator.check_budget([{'name': 'Unknown', 'prices': {'usd': None}}], 100)['pass'])

    def test_unreleased_commander_rejected(self):
        validator = load('deckbuilding/scripts/validate-deck.py')
        commander = card(); commander['legalities']['commander'] = 'not_legal'
        self.assertFalse(validator.check_commander_legality(commander)['pass'])

    def test_text_report_fails_unresolved_cards(self):
        validator = load('deckbuilding/scripts/validate-deck.py')
        keys = ('card_count', 'singleton', 'commander_legality', 'color_identity', 'ban_list', 'game_changers', 'extra_turns', 'mass_land_denial', 'house_rules', 'budget')
        results = {k: {'pass': True, 'detail': 'ok'} for k in keys}
        results['card_resolution'] = {'pass': False, 'detail': 'unresolved'}
        with patch('sys.stdout', new=io.StringIO()):
            self.assertFalse(validator.print_report('Kotis', 3, results, ['Unknown']))

    def test_moxfield_v3_uses_names_in_nested_boards(self):
        module = load('optimization/scripts/fetch-deck.py')
        data = {'boards': {'commanders': {'cards': {'id1': {'card': {'name': 'Kotis, the Fangkeeper'}, 'quantity': 1}}}, 'mainboard': {'cards': {'id2': {'card': {'name': 'Sol Ring'}, 'quantity': 1}}}}}
        with patch.object(module, 'fetch_json', return_value=data):
            deck = module.fetch_moxfield('example')
        self.assertEqual(deck['mainboard'], [(1, 'Sol Ring')])
        self.assertEqual(deck['commanders'], [(1, 'Kotis, the Fangkeeper')])


if __name__ == '__main__':
    unittest.main()
