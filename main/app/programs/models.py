"""Program snapshot data access; retains the existing 15,000-row limit."""
from functools import lru_cache
from ..common.data import _read_rows

PROGRAM_FILE = '공공체육시설 프로그램 정보.csv'

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
            'sport': row.get('PROGRM_TY_NM') or row.get('INDUTY_NM') or '종목 미제공',
            'target': row.get('PROGRM_TRGET_NM') or '대상 미제공',
            'weekday': row.get('PROGRM_ESTBL_WKDAY_NM') or '요일 미제공',
            'period': ' ~ '.join(filter(None, [row.get('PROGRM_BEGIN_DE'), row.get('PROGRM_END_DE')])),
            'fee': row.get('PROGRM_PRC'),
            'fee_unit': row.get('PROGRM_PRC_TY_NM') or '단위 미확인',
            'source': PROGRAM_FILE,
        })
    return result
