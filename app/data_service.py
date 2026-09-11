import csv
import os
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path

from django.conf import settings


DATA_DIR = Path(getattr(settings, 'DATA_DIR', Path.cwd() / 'data'))
FACILITY_FILE = '스포츠강좌이용권 시설 데이터.csv'
PROGRAM_FILE = '청소년 유아동 이용가능 체육시설 프로그램 정보.csv'
COVERAGE_FILE = '지역별스포츠강좌이용권활용정보.csv'
USAGE_FILE = '스포츠강좌이용권 이용현황 정보.csv'


def _clean(value):
    return (value or '').strip()


def _read_rows(filename, limit=None):
    path = DATA_DIR / filename
    if not path.exists():
        return []
    with path.open('r', encoding='utf-8-sig', newline='') as source:
        reader = csv.DictReader(source)
        rows = []
        for row in reader:
            rows.append({key: _clean(value) for key, value in row.items()})
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
        target = _number(row.get('CRRSPND_FLAG_TRGET_NMPR_CO'))
        beneficiary = _number(row.get('CRRSPND_FLAG_RECIPT_NMPR_CO'))
        regions.append({
            'region': row.get('CTPRVN_NM') or '지역 미제공',
            'district': row.get('SIGNGU_NM'),
            'target': target,
            'beneficiary': beneficiary,
            'facility_count': _number(row.get('SIGNGU_ACCTO_FCLTY_CO')),
            'period': row.get('BASE_YEAR'),
            'definition': row.get('RECIPT_FLAG_NM'),
        })
    return regions


@lru_cache(maxsize=1)
def usage_by_sport():
    counts = Counter()
    for row in _read_rows(USAGE_FILE, limit=50000):
        sport = row.get('ITEM_NM') or '종목 미제공'
        value = _number(row.get('COURSE_REQST_NMPR_CO'))
        if value is not None:
            counts[sport] += value
    return counts


def _number(value):
    try:
        return int(float(value)) if value else None
    except (TypeError, ValueError):
        return None


def dashboard_data(region=''):
    region_rows = [item for item in coverage() if not region or item['region'] == region]
    target = _sum_known(item['target'] for item in region_rows)
    beneficiary = _sum_known(item['beneficiary'] for item in region_rows)
    facilities_count = _sum_known(item['facility_count'] for item in region_rows)
    return {
        'regions': region_rows,
        'target': target,
        'beneficiary': beneficiary,
        'facilities': facilities_count,
        'programs': len(programs()),
        'sports': usage_by_sport().most_common(5),
        'region_options': sorted({item['region'] for item in coverage() if item['region'] != '지역 미제공'}),
        'period': sorted({item['period'] for item in region_rows if item['period']})[-1:] or ['기준일 미확인'],
    }


def _sum_known(values):
    values = [value for value in values if value is not None]
    return sum(values) if values else None


def filter_programs(params):
    result = programs()
    if params.get('region'):
        result = [item for item in result if item['region'] == params['region']]
    if params.get('district'):
        result = [item for item in result if item['district'] == params['district']]
    if params.get('sport'):
        result = [item for item in result if params['sport'].lower() in item['sport'].lower()]
    if params.get('target'):
        result = [item for item in result if params['target'].lower() in item['target'].lower()]
    if params.get('query'):
        query = params['query'].lower()
        result = [item for item in result if query in item['name'].lower() or query in item['facility'].lower()]
    sort_key = params.get('sort', 'name')
    if sort_key == 'fee':
        result.sort(key=lambda item: (_number(item['fee']) is None, _number(item['fee']) or 0, item['name'], item['id']))
    else:
        result.sort(key=lambda item: (item['name'], item['id']))
    return result


def benefit_rate(target_count, beneficiary_count):
    """Return a ratio only when both counts are known and the denominator is valid."""
    if target_count is None or beneficiary_count is None or target_count <= 0:
        return None
    return beneficiary_count / target_count


def nearest_stop_minutes(walking_seconds):
    """Return the minimum observed facility-to-stop walk time, preserving missing data."""
    valid = [value for value in walking_seconds if value is not None and value >= 0]
    return min(valid) / 60 if valid else None


def calculate_budget(budget, planned_people, months, fee):
    """Calculate a monthly, per-person fee scenario without inferring other fee units."""
    if budget is None:
        return {'status': 'not_requested', 'cost': None, 'supported_people': None}
    if planned_people is None or planned_people < 1 or months is None or months < 1:
        return {'status': 'invalid_plan', 'cost': None, 'supported_people': None}
    if fee is None or fee < 0:
        return {'status': 'unverified_fee', 'cost': None, 'supported_people': None}
    cost = fee * planned_people * months
    supported = None if fee == 0 else budget // (fee * months)
    return {
        'status': 'within_budget' if cost <= budget else 'over_budget',
        'cost': cost,
        'supported_people': supported,
    }