"""Coverage and sport usage snapshot data access."""
from functools import lru_cache
from ..common.data import _read_rows
from collections import Counter
from ..common.data import to_number

COVERAGE_FILE = '지역별스포츠강좌이용권활용정보.csv'
USAGE_FILE = '스포츠강좌이용권 이용현황 정보.csv'

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
