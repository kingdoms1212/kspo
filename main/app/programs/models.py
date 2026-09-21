"""Program snapshot data access.

Source: the public sports facility programme register. One row is one offering
at one facility for one period. The register repeats an identical offering many
times over (107,000+ byte-identical rows), so this repository collapses rows
whose every displayed field matches and reports how many it removed.

Records are namedtuples rather than dicts on purpose: at 294,000 rows the same
data costs about 80MB as tuples and about 320MB as dicts. Django templates
resolve `item.name` through attribute access, so the page code is unchanged.
"""
from collections import namedtuple

from django.conf import settings

from ..common.calculations import nearest_stop_minutes
from ..common.data import facility_key, iso_date, read_columns, strip_markup, to_number
from ..common.sources import PROGRAM
from ..common.versioned_csv import VersionedCsvCache

PROGRAM_FILE = settings.DATA_FILES['programs']

WALK_COLUMNS = tuple(f'WLKG_MVMN_{rank}R_TIME' for rank in range(1, 6))
COLUMNS = ('CTPRVN_CD', 'CTPRVN_NM', 'SIGNGU_CD', 'SIGNGU_NM', 'FCLTY_NM', 'FCLTY_ADDR',
           'FCLTY_TEL_NO', 'INDUTY_NM', 'PROGRM_TY_NM', 'PROGRM_NM', 'PROGRM_TRGET_NM',
           'PROGRM_BEGIN_DE', 'PROGRM_END_DE', 'PROGRM_ESTBL_WKDAY_NM',
           'PROGRM_ESTBL_TIZN_VALUE', 'PROGRM_RCRIT_NMPR_CO', 'PROGRM_PRC',
           'PROGRM_PRC_TY_NM', 'HMPG_URL', 'BSTP_SUBWAYST_1R_NM') + WALK_COLUMNS
(CTPRVN_CD, CTPRVN_NM, SIGNGU_CD, SIGNGU_NM, FCLTY_NM, FCLTY_ADDR, FCLTY_TEL_NO,
 INDUTY_NM, PROGRM_TY_NM, PROGRM_NM, PROGRM_TRGET_NM, BEGIN_DE, END_DE, WKDAY_NM,
 TIZN, RCRIT_CO, PRC, PRC_TY_NM, HMPG_URL, STOP_NM) = range(20)
WALK = range(20, 25)

Program = namedtuple('Program', (
    'id', 'facility', 'region', 'district', 'address', 'phone', 'facility_type',
    'name', 'sport', 'target', 'weekday', 'time', 'period', 'capacity',
    'fee', 'fee_unit', 'homepage', 'walk_minutes', 'stop'))


def _period(row):
    begin, end = row[BEGIN_DE], row[END_DE]
    return ' ~ '.join(filter(None, [iso_date(begin) if begin else '', iso_date(end) if end else '']))


def _walk(row):
    """Nearest of the five ranked stops; the register ranks by distance, not walk time."""
    return nearest_stop_minutes([to_number(row[column]) for column in WALK])

def _load_snapshot():
    seen = set()
    records = []
    facilities = set()
    register_rows = 0
    duplicates = 0
    for row in read_columns(PROGRAM_FILE, COLUMNS):
        register_rows += 1
        if row in seen:
            duplicates += 1
            continue
        seen.add(row)
        key = facility_key(row[CTPRVN_CD], row[SIGNGU_CD], row[FCLTY_NM], row[FCLTY_ADDR])
        if key is not None:
            facilities.add(key)
        walk = _walk(row)
        record = Program(
            id=f'program-{len(records)}',
            facility=row[FCLTY_NM] or '시설명 미제공',
            region=row[CTPRVN_NM] or '지역 미제공',
            district=row[SIGNGU_NM] or '시군구 미제공',
            address=row[FCLTY_ADDR] or '주소 미제공',
            phone=row[FCLTY_TEL_NO] or '미제공',
            facility_type=row[INDUTY_NM] or '시설유형 미제공',
            name=row[PROGRM_NM] or '강좌명 미제공',
            # The register's own programme type is free text and blank on a third
            # of the rows; the facility industry code fills in without inventing one.
            sport=row[PROGRM_TY_NM] or row[INDUTY_NM] or '종목 미제공',
            target=strip_markup(row[PROGRM_TRGET_NM]) or '대상 미제공',
            weekday=row[WKDAY_NM] or '요일 미제공',
            time=row[TIZN] or '시간 미제공',
            period=_period(row),
            capacity=to_number(row[RCRIT_CO]),
            fee=to_number(row[PRC]),
            fee_unit=row[PRC_TY_NM] or '단위 미확인',
            homepage=row[HMPG_URL],
            walk_minutes=round(walk) if walk is not None else None,
            stop=row[STOP_NM] or '',
        )
        records.append(record)
    report = {
        'register_rows': register_rows,
        'programs': len(records),
        'duplicates': duplicates,
        'facilities': len(facilities),
        'source': PROGRAM_FILE,
    }
    return records, report


# 각 웹 프로세스가 manifest 세대 변경을 직접 감지한다.
_snapshot_cache = VersionedCsvCache(PROGRAM_FILE, _load_snapshot)


def _snapshot():
    return _snapshot_cache.get()


_snapshot.cache_clear = _snapshot_cache.clear


def refresh_snapshot():
    """웹 실행 관리용 공개 진입점. 목록 조회 API와 캐시 구현을 분리한다."""
    return _snapshot_cache.refresh()


def set_background_refresh(enabled):
    _snapshot_cache.set_background_refresh(enabled)


def snapshot_loaded():
    """[SG002] 최초 적재 완료 여부. 준비 상태 판정이 캐시 내부를 보지 않게 한다."""
    return _snapshot_cache.is_loaded


def programs():
    """Every distinct offering in the register, not a leading slice of the file."""
    return _snapshot()[0]


def load_report():
    """Row accounting shown with the results so the page states its own coverage."""
    return _snapshot()[1]
