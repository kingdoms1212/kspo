"""Facility snapshot data access (CSV repository, not Django ORM)."""
from functools import lru_cache
from ..common.data import _read_rows

FACILITY_FILE = '스포츠강좌이용권 시설 데이터.csv'

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
