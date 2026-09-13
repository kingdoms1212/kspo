"""Model layer.

The MVP reads published CSV snapshots directly without copying them into the
DB, so there are no Django ORM models. These functions are the data-access
boundary instead: they read the raw CSV snapshots and shape each row into a
plain dict "entity" that the rest of the app treats as its model layer.

Business rules and query logic (filtering, sorting, aggregating) do not
belong here — see `services.py` for that.
"""
import csv
from collections import Counter
from functools import lru_cache
from pathlib import Path

from django.conf import settings


DATA_DIR = Path(getattr(settings, 'DATA_DIR', Path.cwd() / 'data'))
FACILITY_FILE = '스포츠강좌이용권 시설 데이터.csv'
PROGRAM_FILE = '청소년 유아동 이용가능 체육시설 프로그램 정보.csv'
COVERAGE_FILE = '지역별스포츠강좌이용권활용정보.csv'
USAGE_FILE = '스포츠강좌이용권 이용현황 정보.csv'


def clean(value):
    return (value or '').strip()


def to_number(value):
    try:
        return int(float(value)) if value else None
    except (TypeError, ValueError):
        return None


def _read_rows(filename, limit=None):
    path = DATA_DIR / filename
    if not path.exists():
        return []
    with path.open('r', encoding='utf-8-sig', newline='') as source:
        reader = csv.DictReader(source)
        rows = []
        for row in reader:
            rows.append({key: clean(value) for key, value in row.items()})
            if limit and len(rows) >= limit:
                break
        return rows


@lru_cache(maxsize=1)
def facilities():
    result = []
    for index, row in enumerate(_read_rows(FACILITY_FILE)):
        result.append({
            'id': f'facility-{index}',
            'name': row.get('FCLTY_NM') or '시설명 미제공',
            'region': row.get('CTPRVN_NM') or '지역 미제공',
            'district': row.get('SIGNGU_NM'),
            'address': ' '.join(filter(None, [row.get('FCLTY_ADDR'), row.get('DETAIL_ADDR')])),
            'phone': row.get('RPRSNTV_TEL_NO'),
            'sport': row.get('ITEM_NM') or '종목 미제공',
            'voucher': '스포츠 이용권 등록',
            'source': FACILITY_FILE,
        })
    return result


@lru_cache(maxsize=1)
def programs():
    result = []
    # This source is very large. The service keeps the first verified snapshot
    # slice available for the MVP and labels it as a partial source load.
    for index, row in enumerate(_read_rows(PROGRAM_FILE, limit=15000)):
        result.append({
            'id': f'program-{index}',
            'facility': row.get('FCLTY_NM') or '시설 연결 미확인',
            'region': row.get('CTPRVN_NM') or '지역 미제공',
            'district': row.get('SIGNGU_NM'),
            'name': row.get('PROGRM_NM') or '강좌명 미제공',
            'sport': row.get('PROGRAM_TY_NM') or row.get('INDUTY_NM') or '종목 미제공',
            'target': row.get('PROGRM_TRGET_NM') or '대상 미제공',
            'weekday': row.get('PROGRM_ESTBL_WKDAY_NM') or '요일 미제공',
            'period': ' ~ '.join(filter(None, [row.get('PROGRM_BEGIN_DE'), row.get('PROGRM_END_DE')])),
            'fee': row.get('PROGRM_PRC'),
            'fee_unit': row.get('PROGRM_PRC_TY_NM') or '단위 미확인',
            'source': PROGRAM_FILE,
        })
    return result


@lru_cache(maxsize=1)
def coverage():
    rows = _read_rows(COVERAGE_FILE)
    regions = []
    for row in rows:
        target = to_number(row.get('CRRSPND_FLAG_TRGET_NMPR_CO'))
        beneficiary = to_number(row.get('CRRSPND_FLAG_RECIPT_NMPR_CO'))
        regions.append({
            'region': row.get('CTPRVN_NM') or '지역 미제공',
            'district': row.get('SIGNGU_NM'),
            'target': target,
            'beneficiary': beneficiary,
            'facility_count': to_number(row.get('SIGNGU_ACCTO_FCLTY_CO')),
            'period': row.get('BASE_YEAR'),
            'definition': row.get('RECIPT_FLAG_NM'),
        })
    return regions


@lru_cache(maxsize=1)
def usage_by_sport():
    counts = Counter()
    for row in _read_rows(USAGE_FILE, limit=50000):
        sport = row.get('ITEM_NM') or '종목 미제공'
        value = to_number(row.get('COURSE_REQST_NMPR_CO'))
        if value is not None:
            counts[sport] += value
    return counts
