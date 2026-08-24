import os
import unittest

from django.conf import settings
from django.test import SimpleTestCase

from ..cadastre_import import (
    ParsedUnit,
    _guess_name_parts,
    _normalize_identifier,
    _split_co_owner_line,
    parse_cadastre_pdf,
)

REAL_SAMPLE_PATH = os.path.join(os.path.dirname(settings.BASE_DIR), 'vypis-z-katastru.pdf')


class GuessNamePartsTest(SimpleTestCase):
    def test_surname_given_name_and_titles(self):
        self.assertEqual(_guess_name_parts('Antošková Katarína Ing.'), ('Katarína', 'Antošková'))

    def test_single_word_name(self):
        self.assertEqual(_guess_name_parts('Novák'), ('', 'Novák'))

    def test_empty_name(self):
        self.assertEqual(_guess_name_parts(''), ('', ''))


class NormalizeIdentifierTest(SimpleTestCase):
    def test_rodne_cislo_with_semicolon(self):
        self.assertEqual(_normalize_identifier('535520/022;'), '535520/022')

    def test_ico(self):
        self.assertEqual(_normalize_identifier('27437558;'), '27437558')

    def test_special_state_code(self):
        self.assertEqual(_normalize_identifier('00000001-001'), '00000001-001')

    def test_not_an_identifier(self):
        self.assertIsNone(_normalize_identifier('Holešínský'))


class SplitCoOwnerLineTest(SimpleTestCase):
    def test_single_owner_line_stays_one_owner(self):
        owners = _split_co_owner_line('845727/3968', ['Roupcová', 'Eva', 'Mgr.'], None, None)
        self.assertEqual(len(owners), 1)
        self.assertEqual(owners[0].raw_name, 'Roupcová Eva Mgr.')
        self.assertEqual(owners[0].guessed_first_name, 'Eva')
        self.assertEqual(owners[0].guessed_last_name, 'Roupcová')

    def test_sjm_pair_is_split_into_two_owners(self):
        owners = _split_co_owner_line(
            '610614/0535 685421/0924',
            ['Holešínský', 'František', 'Ing.', 'a', 'Holešínská', 'Irena', 'Ing.'],
            None,
            None,
        )
        self.assertEqual(len(owners), 2)
        self.assertEqual(owners[0].identifier, '610614/0535')
        self.assertEqual(owners[0].raw_name, 'Holešínský František Ing.')
        self.assertEqual(owners[1].identifier, '685421/0924')
        self.assertEqual(owners[1].raw_name, 'Holešínská Irena Ing.')

    def test_sjm_pair_share_is_split_evenly(self):
        owners = _split_co_owner_line('1/1 2/2', ['A', 'a', 'B'], 1, 20)
        self.assertEqual((owners[0].share_numerator, owners[0].share_denominator), (1, 40))
        self.assertEqual((owners[1].share_numerator, owners[1].share_denominator), (1, 40))

    def test_two_identifiers_without_conjunction_stay_one_owner(self):
        # defensive: only split when the name text actually has " a " joining two names
        owners = _split_co_owner_line('1/1 2/2', ['Some', 'Company', 'Name'], None, None)
        self.assertEqual(len(owners), 1)


class ParsedUnitShareSumOkTest(SimpleTestCase):
    def test_single_line_is_always_ok_even_without_explicit_share(self):
        from ..cadastre_import import ParsedOwner

        u = ParsedUnit(unit_no='2919/11', owner_line_count=1)
        u.owners = [
            ParsedOwner('610614/0535', 'Holešínský František', 'František', 'Holešínský'),
            ParsedOwner('685421/0924', 'Holešínská Irena', 'Irena', 'Holešínská'),
        ]
        self.assertTrue(u.share_sum_ok)

    def test_multiple_lines_summing_to_one_is_ok(self):
        from ..cadastre_import import ParsedOwner

        u = ParsedUnit(unit_no='2919/17', owner_line_count=2)
        u.owners = [
            ParsedOwner('701215/3984', 'Joanidis Tomáš', 'Tomáš', 'Joanidis', 1, 2),
            ParsedOwner('695406/3974', 'Lacinová Lenka', 'Lenka', 'Lacinová', 1, 2),
        ]
        self.assertTrue(u.share_sum_ok)

    def test_multiple_lines_with_missing_share_is_not_ok(self):
        from ..cadastre_import import ParsedOwner

        u = ParsedUnit(unit_no='2919/1', owner_line_count=2)
        u.owners = [
            ParsedOwner('47114983', 'Česká pošta, s.p.', '', 'Česká pošta, s.p.'),
            ParsedOwner('00000001-001', 'Česká republika', '', 'Česká republika'),
        ]
        self.assertFalse(u.share_sum_ok)

    def test_multiple_lines_summing_to_more_than_one_is_not_ok(self):
        from ..cadastre_import import ParsedOwner

        u = ParsedUnit(unit_no='2919/x', owner_line_count=2)
        u.owners = [
            ParsedOwner('1', 'A', 'A', 'A', 2, 3),
            ParsedOwner('2', 'B', 'B', 'B', 2, 3),
        ]
        self.assertFalse(u.share_sum_ok)


@unittest.skipUnless(
    os.path.exists(REAL_SAMPLE_PATH),
    "Local-only sanity check against a real cadastre extract; the sample PDF contains personal "
    "data and is intentionally never committed to the repository (see .gitignore).",
)
class ParseRealSampleTest(SimpleTestCase):
    """Not run in CI - place a real 'vypis-z-katastru.pdf' at the repository root to run this
    locally as a smoke test against real-world layout quirks the synthetic unit tests can't cover."""

    def test_parses_all_units_with_no_warnings(self):
        with open(REAL_SAMPLE_PATH, 'rb') as f:
            result = parse_cadastre_pdf(f)
        self.assertEqual(result.warnings, [])
        self.assertGreater(len(result.units), 0)
        for unit in result.units:
            self.assertTrue(unit.owners, f'{unit.unit_no} has no owners')
