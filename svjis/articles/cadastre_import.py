"""Parse a Czech cadastre extract ("výpis z katastru nemovitostí") PDF for a
building whose units are defined under Act No. 72/1994 Coll., into a
structure of building units and their owners, ready for review before it is
turned into `BuildingUnit`/`User`/`BuildingUnitUser` records.

The PDF has no ruling lines around its unit table, so `pdfplumber`'s generic
table detection finds nothing - this module reconstructs rows from word
coordinates instead (grouping words by their vertical position, then
classifying each row by its horizontal position) and walks them as a small
state machine tracking the "current unit" and "current owner". See the
column position notes below; they were derived from, and verified against,
a real extract for a multi-unit building and are expected to be stable
across extracts of this same document type, since it is a fixed ČÚZK
template - but are not guaranteed for other extract layouts (e.g. a single
family house with no units table).
"""

import re
from dataclasses import dataclass, field
from fractions import Fraction

import pdfplumber
from django.utils.translation import gettext_lazy as _

FRACTION_RE = re.compile(r'^\d+/\d+$')
RC_RE = re.compile(r'^\d{6}/\d{3,4}$')  # rodné číslo
ICO_RE = re.compile(r'^\d{8}(-\d{3})?$')  # IČO, or the special state code 00000001-001

UNIT_NO_X0_MAX = 80
USAGE_X0_MIN, USAGE_X0_MAX = 95, 270
LV_X0_MIN, LV_X0_MAX = 270, 310
BUILDING_SHARE_X0_MIN = 430
IDENTIFIER_X0_MIN, IDENTIFIER_X0_MAX = 125, 175
NAME_CONTINUATION_X0_MIN, NAME_CONTINUATION_X0_MAX = 125, 430
OWNER_SHARE_X0_MIN = 500
HEADER_TOP_MARGIN = 3
CONTENT_TOP_FLOOR = 95  # skips the repeated per-page Okres/Obec/List vlastnictví boilerplate
FOOTER_TOP_MARGIN = 2

TITLE_WORDS = {'Ing.', 'Mgr.', 'MUDr.', 'RNDr.', 'PhD.', 'DiS.', 'doc.', 'prof.', "Bc.", "MBA", "LL.M."}


def _normalize_identifier(text: str) -> str | None:
    core = text.rstrip(';')
    if RC_RE.match(core) or ICO_RE.match(core):
        return core
    return None


@dataclass
class ParsedOwner:
    identifier: str
    raw_name: str
    guessed_first_name: str
    guessed_last_name: str
    share_numerator: int | None = None
    share_denominator: int | None = None


@dataclass
class ParsedUnit:
    unit_no: str
    usage: str = ''
    unit_lv: str | None = None
    building_share_numerator: int | None = None
    building_share_denominator: int | None = None
    owners: list[ParsedOwner] = field(default_factory=list)
    # Number of distinct ownership lines in the source document, i.e. before a
    # joint-owner (SJM) line is split into two ParsedOwner records. A single
    # line implies the sole owner(s) hold 1/1 even with no printed share.
    owner_line_count: int = 0

    @property
    def share_sum_ok(self) -> bool:
        if self.owner_line_count <= 1:
            return True
        total = Fraction(0)
        for o in self.owners:
            if o.share_numerator is None or o.share_denominator is None:
                return False
            total += Fraction(o.share_numerator, o.share_denominator)
        return total == 1


@dataclass
class ParsedCadastreExtract:
    lv_number: str | None = None
    cadastral_area: str | None = None
    building_label: str | None = None
    units: list[ParsedUnit] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _guess_name_parts(raw_name: str) -> tuple[str, str]:
    """Best-effort split of "Příjmení Jméno [tituly]" into (first_name, last_name).

    This is intentionally simple (surname = 1st word, given name = 2nd word,
    everything else assumed to be an academic title) and will misparse
    foreign/compound names - callers must let a human confirm/correct it,
    never create records from it unattended.
    """
    words = raw_name.split()
    if not words:
        return '', ''
    if len(words) == 1:
        return '', words[0]
    return words[1], words[0]


def _split_co_owner_line(identifier: str, name_words: list[str], share_numerator, share_denominator):
    """A line with two identifiers (space-separated) is a pair of co-owners
    (typically spouses) sharing this single ownership line, joined by " a "
    in the name text, e.g. "Holešínský František Ing. a Holešínská Irena
    Ing.". Split it into two ParsedOwner records. When the line carries a
    share (e.g. "1/20"), it is split evenly between the two - the source
    document records the share for the pair as a whole, not per person, but
    our model needs one row per (unit, user); splitting evenly keeps the
    per-unit share sum meaningful without inventing a joint-ownership
    concept in the schema.
    """
    identifiers = identifier.split(' ')
    name_text = ' '.join(name_words)
    if len(identifiers) != 2 or ' a ' not in name_text:
        first, last = _guess_name_parts(name_text)
        return [ParsedOwner(identifier, name_text, first, last, share_numerator, share_denominator)]

    left, _sep, right = name_text.partition(' a ')
    if share_numerator is not None and share_denominator is not None:
        n1, d1 = share_numerator, share_denominator * 2
    else:
        n1 = d1 = None
    owners = []
    for ident, raw in ((identifiers[0], left.strip()), (identifiers[1], right.strip())):
        first, last = _guess_name_parts(raw)
        owners.append(ParsedOwner(ident, raw, first, last, n1, d1))
    return owners


def _most_common_unit_prefix(pages_words) -> str | None:
    from collections import Counter

    counts: Counter[str] = Counter()
    for words in pages_words:
        for w in words:
            if w['x0'] < UNIT_NO_X0_MAX and FRACTION_RE.match(w['text']):
                left, _right = w['text'].split('/')
                counts[left] += 1
    return counts.most_common(1)[0][0] if counts else None


def _group_rows(words):
    from collections import defaultdict

    rows: dict[int, list] = defaultdict(list)
    for w in words:
        rows[round(w['top'])].append(w)
    return [sorted(rows[top], key=lambda w: w['x0']) for top in sorted(rows)]


def _extract_header_info(first_page_text: str, unit_prefix: str | None) -> tuple[str | None, str | None, str | None]:
    lv_match = re.search(r'List vlastnictví:\s*(\d+)', first_page_text)
    area_match = re.search(r'Kat\.území:\s*\d+\s+(.+?)(?:\s+List\b|\n|$)', first_page_text)
    building_match = None
    if unit_prefix:
        building_match = re.search(rf'([^\n,]+,\s*č\.p\.\s*{re.escape(unit_prefix)})\b', first_page_text)
    return (
        lv_match.group(1) if lv_match else None,
        area_match.group(1).strip() if area_match else None,
        building_match.group(1).strip() if building_match else None,
    )


def parse_cadastre_pdf(file_obj) -> ParsedCadastreExtract:
    with pdfplumber.open(file_obj) as pdf:
        if not pdf.pages:
            return ParsedCadastreExtract(warnings=[str(_("The PDF has no pages."))])

        pages_words = [p.extract_words(use_text_flow=False, keep_blank_chars=False) for p in pdf.pages]
        unit_prefix = _most_common_unit_prefix(pages_words)
        all_text = '\n'.join(p.extract_text() or '' for p in pdf.pages)
        lv_number, cadastral_area, building_label = _extract_header_info(all_text, unit_prefix)

        result = ParsedCadastreExtract(
            lv_number=lv_number, cadastral_area=cadastral_area, building_label=building_label
        )

        if unit_prefix is None:
            result.warnings.append(str(_("Could not find a unit table (section B1 - Jednotky) in this PDF.")))
            return result

        units: list[ParsedUnit] = []
        current_unit: ParsedUnit | None = None
        current_owner_ctx: dict | None = None  # {'identifier': str, 'name_words': list[str]}

        def flush_owner():
            nonlocal current_owner_ctx
            if current_owner_ctx is not None and current_unit is not None:
                current_unit.owner_line_count += 1
                current_unit.owners.extend(
                    _split_co_owner_line(
                        current_owner_ctx['identifier'],
                        current_owner_ctx['name_words'],
                        current_owner_ctx['share_numerator'],
                        current_owner_ctx['share_denominator'],
                    )
                )
            current_owner_ctx = None

        def flush_unit():
            nonlocal current_unit
            flush_owner()
            if current_unit is not None:
                units.append(current_unit)
            current_unit = None

        for words in pages_words:
            header_tops = [
                w['top'] for w in words if w['text'] in ('Č.p./', 'Č.jednotky') and w['x0'] < UNIT_NO_X0_MAX
            ]
            footer_tops = [w['top'] for w in words if w['text'] in ('Nemovitosti', 'Věcná')]
            lo = max(header_tops) + HEADER_TOP_MARGIN if header_tops else CONTENT_TOP_FLOOR
            lo = max(lo, CONTENT_TOP_FLOOR)
            hi = min(footer_tops) - FOOTER_TOP_MARGIN if footer_tops else 10**6

            page_words = [w for w in words if lo <= w['top'] < hi and w['text'] != 'Spoluvlastníci']
            rows = _group_rows(page_words)

            for row in rows:
                share_tokens = [w for w in row if w['x0'] >= OWNER_SHARE_X0_MIN and FRACTION_RE.match(w['text'])]
                if share_tokens:
                    row = [w for w in row if w not in share_tokens]

                if row:
                    first = row[0]
                    x0, text = first['x0'], first['text']

                    if x0 < UNIT_NO_X0_MAX and FRACTION_RE.match(text) and text.split('/')[0] == unit_prefix:
                        flush_unit()
                        current_unit = ParsedUnit(unit_no=text)
                        usage_words = []
                        for w in row[1:]:
                            wx = w['x0']
                            if USAGE_X0_MIN <= wx < USAGE_X0_MAX:
                                usage_words.append(w['text'])
                            elif LV_X0_MIN <= wx < LV_X0_MAX and w['text'].isdigit():
                                current_unit.unit_lv = w['text']
                            elif wx >= BUILDING_SHARE_X0_MIN and FRACTION_RE.match(w['text']):
                                n, d = w['text'].split('/')
                                current_unit.building_share_numerator = int(n)
                                current_unit.building_share_denominator = int(d)
                        current_unit.usage = ' '.join(usage_words)
                    elif current_unit is not None:
                        ident = _normalize_identifier(text) if IDENTIFIER_X0_MIN <= x0 < IDENTIFIER_X0_MAX else None
                        if ident is not None:
                            remaining = row[1:]
                            if not text.endswith(';') and remaining:
                                ident2 = _normalize_identifier(remaining[0]['text'])
                                if ident2 is not None:
                                    ident = f'{ident} {ident2}'
                                    remaining = remaining[1:]
                            flush_owner()
                            current_owner_ctx = {
                                'identifier': ident,
                                'name_words': [w['text'] for w in remaining],
                                'share_numerator': None,
                                'share_denominator': None,
                            }
                        elif (
                            current_owner_ctx is not None and NAME_CONTINUATION_X0_MIN <= x0 < NAME_CONTINUATION_X0_MAX
                        ):
                            current_owner_ctx['name_words'].extend(w['text'] for w in row)
                        elif current_owner_ctx is None and USAGE_X0_MIN <= x0 < USAGE_X0_MAX:
                            current_unit.usage = (current_unit.usage + ' ' + ' '.join(w['text'] for w in row)).strip()

                if share_tokens and current_owner_ctx is not None and current_owner_ctx['share_numerator'] is None:
                    n, d = share_tokens[0]['text'].split('/')
                    current_owner_ctx['share_numerator'] = int(n)
                    current_owner_ctx['share_denominator'] = int(d)

        flush_unit()
        result.units = units
        if not units:
            result.warnings.append(str(_("No units were recognized in this PDF.")))
        return result
