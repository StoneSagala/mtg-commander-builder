from datetime import datetime, timedelta, timezone
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import URLError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '_shared'))
import combos
import data_sources
import deck_budget
import freshness


def load(relative):
    spec = importlib.util.spec_from_file_location(Path(relative).stem, ROOT / relative)
    result = importlib.util.module_from_spec(spec); spec.loader.exec_module(result)
    return result


def commander(name, text='Partner', colors=None, types='Legendary Creature — Human'):
    return {'name': name, 'oracle_text': text, 'color_identity': colors or ['U'], 'type_line': types, 'legalities': {'commander': 'legal'}}


class BudgetTests(unittest.TestCase):
    def test_no_budget_means_no_price_requirement(self):
        sections = {'Utility Lands': ['Expensive'], 'Ramp': ['Unknown']}
        result, report = deck_budget.constrain_deck(sections, {}, ['Commander'], None, {})
        self.assertEqual(result, sections)
        self.assertEqual(report['status'], 'unrestricted')

    def test_total_includes_commander_and_each_basic_copy(self):
        result, report = deck_budget.constrain_deck({'Utility Lands': ['Tower'], 'Ramp': ['Cheap', 'Costly']}, {'Forest': 3}, ['Commander'], 10, {'Commander': 200, 'Forest': 100, 'Tower': 100, 'Cheap': 200, 'Costly': 400})
        self.assertEqual(result['Ramp'], ['Cheap'])
        self.assertEqual(report['estimated_total_usd'], 8)

    def test_unknown_spell_omitted_for_a_bounded_build(self):
        result, report = deck_budget.constrain_deck({'Utility Lands': [], 'Ramp': ['Unknown']}, {}, ['Commander'], 20, {'Commander': 100})
        self.assertEqual(result['Ramp'], [])
        self.assertEqual(report['omitted'][0]['reason'], 'price unknown')

    def test_unpriced_base_cannot_claim_within_budget(self):
        with self.assertRaisesRegex(ValueError, 'missing commander/land prices'):
            deck_budget.constrain_deck({'Utility Lands': [], 'Ramp': []}, {'Forest': 20}, ['Commander'], 200, {'Commander': 100})

    def test_impossible_budget_fails(self):
        with self.assertRaisesRegex(ValueError, 'above the player budget'):
            deck_budget.constrain_deck({'Utility Lands': []}, {}, ['Commander'], 0, {'Commander': 100})

    def test_invalid_values_not_unlimited(self):
        for value in ('nan', 'inf', -1):
            self.assertIsNone(deck_budget.cents(value))
        self.assertEqual(deck_budget.cents('1.001'), 101)

    def test_partner_costs_both_count(self):
        _, report = deck_budget.constrain_deck({'Utility Lands': []}, {}, ['A', 'B'], 10, {'A': 100, 'B': 200})
        self.assertEqual(report['estimated_total_usd'], 3)

    def test_cheaper_alternatives_refill_budget_gaps(self):
        module = load('deckbuilding/scripts/generate-starter-deck.py')
        sections = {'Utility Lands': ['Luxury'], 'Ramp': ['Expensive'], 'Card Draw': [], 'Interaction': [], 'Tutors': [], 'Win Conditions': [], 'Theme / Synergy': []}
        pool = {'Ramp': [{'name': 'Expensive', 'price_usd': '30'}, {'name': 'Cheap', 'price_usd': '1'}]}
        prices = {'Commander': 100, 'Forest': 10, 'Luxury': 5000, 'Expensive': 3000}
        with patch.object(module, 'price_cards', return_value=prices):
            result, basics, report = module.apply_total_budget(sections, {'Forest': 1}, ['Commander'], {'lands': 2}, ['G'], pool, 10)
        self.assertEqual(result['Utility Lands'], [])
        self.assertEqual(basics, {'Forest': 2})
        self.assertEqual(result['Ramp'], ['Cheap'])
        self.assertLessEqual(report['estimated_total_usd'], 10)

    def test_validator_exact_budget_uses_integer_cents(self):
        module = load('deckbuilding/scripts/validate-deck.py')
        result = module.check_budget([{'name': 'A', 'prices': {'usd': '0.10'}}, {'name': 'B', 'prices': {'usd': '0.20'}}], 0.30)
        self.assertTrue(result['pass'])
        self.assertEqual(result['total'], 0.30)

    def test_effect_screen_uses_fresh_text_not_old_card_name_lists(self):
        module = load('deckbuilding/scripts/validate-deck.py')
        records = [{'name': 'New Time Spell', 'oracle_text': 'Take an extra turn after this one.'}, {'name': 'Wandering Archaic', 'oracle_text': 'Whenever an opponent casts an instant or sorcery spell, you may copy that spell unless that player pays {2}.'}]
        result = module.check_extra_turns([c['name'] for c in records], 3, records)
        self.assertEqual(result['found'], ['New Time Spell'])


class FreshnessTests(unittest.TestCase):
    def test_expiry_boundary_and_future_times(self):
        now = datetime(2026, 11, 12, tzinfo=timezone.utc)
        self.assertTrue(freshness.is_fresh((now - timedelta(hours=23)).isoformat(), 24, now))
        self.assertFalse(freshness.is_fresh((now - timedelta(hours=24)).isoformat(), 24, now))
        self.assertFalse(freshness.is_fresh((now + timedelta(hours=1)).isoformat(), 24, now))
        self.assertFalse(freshness.is_fresh(None, 24, now))

    def test_expired_refresh_failure_cannot_reuse_old_data(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'snapshot.json'; path.write_text(json.dumps({'checked_at': '2020-01-01T00:00:00Z'}))
            with patch.object(freshness, 'SNAPSHOT', path), patch.object(freshness, 'refresh_rules', side_effect=URLError('offline')):
                with self.assertRaisesRegex(freshness.FreshnessError, 'No current compliance claim'):
                    freshness.current_rules()

    def test_new_rules_hash_requires_review_even_when_recent(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'snapshot.json'; review = Path(folder) / 'review.json'
            path.write_text(json.dumps({'checked_at': freshness.utcnow().isoformat(), 'rules_hash': 'new'})); review.write_text(json.dumps({'rules_hash': 'old'}))
            with patch.object(freshness, 'SNAPSHOT', path), patch.object(freshness, 'REVIEW', review):
                with self.assertRaisesRegex(freshness.FreshnessError, 'Official rules changed'):
                    freshness.current_rules()

    def test_broken_source_does_not_replace_last_good_snapshot(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'snapshot.json'; path.write_text('last-good')
            with patch.object(freshness, 'SNAPSHOT', path), patch.object(freshness.urllib.request, 'urlopen', return_value=io.BytesIO(b'<html>changed</html>')):
                with self.assertRaises(freshness.FreshnessError):
                    freshness.refresh_rules()
            self.assertEqual(path.read_text(), 'last-good')

    def test_missing_official_color_section_detected(self):
        with self.assertRaisesRegex(freshness.FreshnessError, 'missing White'):
            freshness.parse_official_page('topic:"Blue",copy:"Changed"')

    def test_popularity_cache_expiry(self):
        module = load('Ideation/scripts/fetch-top-commanders.py')
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'cache.json'; path.write_text(json.dumps({'fetched_at': '2020-01-01T00:00:00Z'}))
            with patch.object(module, 'CACHE_FILE', path):
                self.assertIsNone(module.load_cache())


class ComboTests(unittest.TestCase):
    def test_pagination_collects_all_included_not_almost(self):
        pages = [{'results': {'included': [{'id': '1'}], 'almostIncluded': [{'id': 'near'}]}, 'next': combos.BASE + '/find-my-combos?offset=1'}, {'results': {'included': [{'id': '2'}]}, 'next': None}]
        with patch.object(combos, 'request_json', side_effect=pages) as request:
            report = combos.find_deck(['A', 'A'], ['Commander'])
        self.assertTrue(report['complete'])
        self.assertEqual([v['id'] for v in report['variants']], ['1', '2'])
        self.assertEqual(request.call_args_list[0].args[1]['main'], [{'card': 'A', 'quantity': 2}])
        self.assertEqual(request.call_args_list[0].args[1], request.call_args_list[1].args[1])

    def test_partial_network_failure_keeps_confirmed_variants(self):
        with patch.object(combos, 'request_json', side_effect=[{'results': [{'id': '1'}], 'next': combos.BASE + '/variants/?offset=1'}, URLError('offline')]):
            report = combos.find_cards(['A'])
        self.assertFalse(report['complete'])
        self.assertEqual(len(report['variants']), 1)
        self.assertTrue(report['errors'])

    def test_request_cap_reports_incomplete(self):
        with patch.object(combos, 'request_json', return_value={'results': [], 'next': combos.BASE + '/variants/?offset=1'}):
            report = combos.find_cards(['A'], max_pages=1)
        self.assertFalse(report['complete'])

    def test_parse_deck_keeps_commanders_and_quantities(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'deck.md'; path.write_text('Commander:\n1 A\n1 B\nLands (3):\n3 Forest\n## Notes\n1 Do not parse\n')
            self.assertEqual(combos.parse_deck(path), (['Forest'] * 3, ['A', 'B']))

    def test_combo_legality_uses_current_schema(self):
        module = load('deckbuilding/scripts/validate-combos.py')
        self.assertFalse(module.extract_combo_details({'legalities': {'commander': False}})['legal_commander'])


class PartnerTests(unittest.TestCase):
    def test_partner_union(self):
        first, second = commander('A', colors=['U']), commander('B', colors=['R'])
        with patch.object(data_sources, 'commander_card', side_effect=[first, second]), patch.object(data_sources, 'request_json', return_value=second):
            group = data_sources.commander_group('A', 'B')
        self.assertEqual({c for card in group for c in card['color_identity']}, {'U', 'R'})

    def test_arbitrary_two_legends_not_a_legal_pair(self):
        with patch.object(data_sources, 'commander_card', return_value=commander('A', '')), patch.object(data_sources, 'request_json', return_value=commander('B', '')):
            with self.assertRaisesRegex(ValueError, 'not a supported legal'):
                data_sources.commander_group('A', 'B')

    def test_choose_background_pair(self):
        background = commander('B', '', ['G'], 'Legendary Enchantment — Background')
        with patch.object(data_sources, 'commander_card', return_value=commander('A', 'Choose a Background')), patch.object(data_sources, 'request_json', return_value=background):
            self.assertEqual(len(data_sources.commander_group('A', 'B')), 2)

    def test_two_commanders_change_deck_slot_count(self):
        module = load('deckbuilding/scripts/validate-deck.py')
        self.assertTrue(module.check_card_count(['A', 'B'], ['Card'] * 98)['pass'])


class MulliganTests(unittest.TestCase):
    def test_free_mulligan_and_bottom_conserve_cards(self):
        module = load('optimization/scripts/goldfish.py')
        deck = [f'Card {n}' for n in range(99)]
        profile = {'lands': [], 'key_hand': [], 'key_gy': [], 'keep_if': [], 'ramp': []}
        with patch.object(module, 'evaluate_hand', side_effect=[(False, 'screw'), (False, 'screw'), (True, 'keep')]):
            hand, library, redraws, reason = module.london_mulligan(deck, profile, {})
        self.assertEqual(len(hand), 6)
        self.assertEqual(redraws, 2)
        self.assertEqual(sorted(hand + library), sorted(deck))

    def test_first_redraw_is_free_seven(self):
        module = load('optimization/scripts/goldfish.py')
        profile = {'lands': [], 'key_hand': [], 'key_gy': [], 'keep_if': [], 'ramp': []}
        with patch.object(module, 'evaluate_hand', side_effect=[(False, 'screw'), (True, 'keep')]):
            hand, library, redraws, _ = module.london_mulligan([str(n) for n in range(99)], profile, {})
        self.assertEqual(len(hand), 7)
        self.assertEqual(len(library), 92)

    def test_seeded_simulation_repeats_and_all_land_deck_has_four_lands_on_t4(self):
        module = load('optimization/scripts/goldfish.py')
        deck = ['Forest'] * 99
        records = {'Forest': {'name': 'Forest', 'type_line': 'Basic Land — Forest', 'cmc': 0, 'oracle_text': '', 'color_identity': ['G'], 'produced_mana': ['G'], 'mana_cost': ''}}
        classified = {'Forest': module.classify_card('Forest', records['Forest'], 'lands')}
        profile = module.build_profile(deck, {'lands': ['Forest']}, records, classified, [], [], [], None)
        profile['deck_type'] = module.DECK_TYPE_FUN
        first = module.run_simulation(deck, profile, classified, records, 10, seed=42)
        second = module.run_simulation(deck, profile, classified, records, 10, seed=42)
        self.assertEqual(first, second)
        self.assertEqual(first['avg_lands_per_turn'][:4], [1, 2, 3, 4])
        self.assertEqual(first['games'], 10)

    def test_seeded_mixed_deck_is_reproducible(self):
        module = load('optimization/scripts/goldfish.py')
        deck = ['Forest'] * 36 + ['Grizzly Bears'] * 63
        records = {'Forest': {'name': 'Forest', 'type_line': 'Basic Land — Forest', 'cmc': 0, 'oracle_text': '', 'color_identity': ['G'], 'produced_mana': ['G'], 'mana_cost': ''}, 'Grizzly Bears': {'name': 'Grizzly Bears', 'type_line': 'Creature — Bear', 'cmc': 2, 'oracle_text': '', 'color_identity': ['G'], 'mana_cost': '{1}{G}'}}
        sections = {'lands': ['Forest']}
        classified = {name: module.classify_card(name, card, 'lands' if name == 'Forest' else None) for name, card in records.items()}
        profile = module.build_profile(deck, sections, records, classified, [], [], [], None)
        profile['deck_type'] = module.DECK_TYPE_FUN
        self.assertEqual(module.run_simulation(deck, profile, classified, records, 20, seed=9), module.run_simulation(deck, profile, classified, records, 20, seed=9))
