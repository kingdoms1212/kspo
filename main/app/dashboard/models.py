"""Facility usage snapshot from the sports-voucher ledger.

The ledger stores one row per course per opening month. Everything the
dashboard shows is a count over that ledger: how many facilities and courses
appear, and how many applications were recorded. The regional target and
recipient counts the dashboard used to show came from a coverage file that is
no longer in `data/`, so those figures are not computed from another source.
"""
from collections import Counter

from ..common.data import course_month, read_columns, to_number
from ..common.sources import USAGE
from ..common.versioned_csv import VersionedCsvCache

USAGE_FILE = USAGE.final_filename

COLUMNS = ('CTPRVN_CD', 'CTPRVN_NM', 'SIGNGU_CD', 'SIGNGU_NM', 'FCLTY_NM',
           'FCLTY_ADDR', 'FCLTY_DETAIL_ADDR', 'ITEM_NM', 'COURSE_NO',
           'COURSE_ESTBL_YEAR', 'COURSE_ESTBL_MT', 'COURSE_REQST_NMPR_CO')
(CTPRVN_CD, CTPRVN_NM, SIGNGU_CD, SIGNGU_NM, FCLTY_NM, FCLTY_ADDR, FCLTY_DETAIL_ADDR,
 ITEM_NM, COURSE_NO, ESTBL_YEAR, ESTBL_MT, REQST_CO) = range(len(COLUMNS))


def usage_key(row):
    """Conservative facility identity; the same rule the course grouping uses."""
    values = tuple(' '.join(row[column].split()).casefold() for column in
                   (CTPRVN_CD, SIGNGU_CD, FCLTY_NM, FCLTY_ADDR, FCLTY_DETAIL_ADDR))
    return values if all(values[:4]) else None


def _area():
    return {'facilities': set(), 'courses': set(), 'requests': None,
            'months': set(), 'sports': Counter(), 'sport_details': {}}


def _load_usage_snapshot():
    """One pass over the ledger, aggregated per district.

    District keys are disjoint, so a region total is the sum of its districts
    and no facility or course is counted twice across regions.
    """
    areas = {}
    months = set()
    ledger_rows = 0
    unidentified = 0
    for row in read_columns(USAGE_FILE, COLUMNS):
        if row[CTPRVN_NM].strip() not in ("서울", "서울시", "서울특별시"):
            continue
        row = list(row)
        row[CTPRVN_NM] = "서울"
        ledger_rows += 1
        key = usage_key(row)
        if key is None:
            unidentified += 1
            continue
        area = areas.get((row[CTPRVN_NM], row[SIGNGU_NM]))
        if area is None:
            areas[(row[CTPRVN_NM], row[SIGNGU_NM])] = area = _area()
        area['facilities'].add(key)
        course_key = (*key, row[COURSE_NO])
        area['courses'].add(course_key)
        sport_name = row[ITEM_NM] or '종목 미제공'
        sport = area['sport_details'].setdefault(
            sport_name, {'facilities': set(), 'courses': set(), 'requests': None})
        sport['facilities'].add(key)
        sport['courses'].add(course_key)
        month = course_month(row[ESTBL_YEAR], row[ESTBL_MT])
        if month != 'unknown':
            area['months'].add(month)
            months.add(month)
        requested = to_number(row[REQST_CO])
        if requested is not None:
            area['requests'] = (area['requests'] or 0) + requested
            area['sports'][sport_name] += requested
            sport['requests'] = (sport['requests'] or 0) + requested
    return {
        'areas': [_finish(region, district, area)
                  for (region, district), area in sorted(areas.items())],
        'months': sorted(months),
        'ledger_rows': ledger_rows,
        'unidentified': unidentified,
        'source': USAGE_FILE,
    }


# 일요일 배치 세대가 바뀌면 이 프로세스의 집계를 다시 만든다.
_usage_cache = VersionedCsvCache(USAGE_FILE, _load_usage_snapshot)


def usage_snapshot():
    return _usage_cache.get()


usage_snapshot.cache_clear = _usage_cache.clear


def _finish(region, district, area):
    observed = sorted(area['months'])
    return {
        'region': region or '지역 미제공',
        'district': district or '시군구 미제공',
        'facilities': len(area['facilities']),
        'courses': len(area['courses']),
        'requests': area['requests'],
        'sports': area['sports'],
        # Keep missing application counts distinct from zero, including sports
        # that have facilities/courses but no reported application count.
        'sport_details': [
            {'name': name, 'facilities': len(sport['facilities']),
             'courses': len(sport['courses']), 'requests': sport['requests']}
            for name, sport in sorted(area['sport_details'].items())
        ],
        'first_month': observed[0] if observed else '',
        'last_month': observed[-1] if observed else '',
    }
