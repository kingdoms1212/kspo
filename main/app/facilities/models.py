"""Facility snapshot data access (CSV repository, not Django ORM).

Source: the national sports facility register, which covers public facilities
alongside the far larger set of private ones filed under 신고 and 등록.

Two things about this register need care.

Rows flagged deleted (`DEL_AT = Y`) are excluded and counted rather than shown,
because the register keeps them for history. Closed facilities (`폐업`) are
kept and filtered on screen instead, since mixing them into a policy view would
overstate what is actually operating.

Districts come from `FCLTY_MANAGE_SIGNGU_NM`, not the plain `SIGNGU_NM`. The
plain field sits at city level or disagrees with the address outright -- 7,503
rows name a different district than their own road address.

The key that links a facility to its nearby transport is geometric; see
app.facilities.transit for why an address or a name cannot carry that join.
"""
from collections import namedtuple

from ..common.data import read_columns, to_number
from ..common.sources import FACILITY
from ..common.versioned_csv import VersionedCsvCache
from .transit import geo_key

FACILITY_FILE = FACILITY.final_filename

COLUMNS = ('FCLTY_NM', 'FCLTY_FLAG_NM', 'INDUTY_NM', 'FCLTY_TY_NM', 'FCLTY_STATE_VALUE',
           'RDNMADR_ONE_NM', 'RDNMADR_TWO_NM', 'FCLTY_ADDR_ONE_NM', 'CTPRVN_NM', 'SIGNGU_NM',
           'FCLTY_MANAGE_CTPRVN_CD', 'FCLTY_MANAGE_SIGNGU_CD', 'FCLTY_MANAGE_SIGNGU_NM',
           'FCLTY_MANAGE_EMD_NM', 'FCLTY_OPER_STLE_VALUE', 'POSESN_MBY_NM', 'RSPNSBLTY_NM',
           'RSPNSBLTY_TEL_NO', 'FCLTY_TEL_NO', 'FCLTY_HMPG_URL', 'NDOR_SDIV_NM',
           'ACMD_NMPR_CO', 'FCLTY_AR_CO', 'NATION_ALSFC_AT', 'FCLTY_LA', 'FCLTY_LO', 'DEL_AT')
(FCLTY_NM, FLAG_NM, INDUTY_NM, FCLTY_TY_NM, STATE_VALUE, RDNMADR_ONE, RDNMADR_TWO,
 ADDR_ONE, CTPRVN_NM, SIGNGU_NM, MANAGE_CTPRVN_CD, MANAGE_SIGNGU_CD, MANAGE_SIGNGU_NM,
 MANAGE_EMD_NM, OPER_STLE, POSESN_MBY_NM, DEPT_NM, DEPT_TEL, FCLTY_TEL, HMPG_URL,
 NDOR_SDIV, ACMD_CO, AR_CO, NATION_AT, FCLTY_LA, FCLTY_LO, DEL_AT) = range(len(COLUMNS))

OPERATING = '정상운영'

Facility = namedtuple('Facility', (
    'id', 'geo_key', 'name', 'flag', 'state', 'region', 'district', 'emd', 'address',
    'industry', 'facility_type', 'owner', 'operation', 'indoor', 'department', 'phone',
    'area', 'capacity', 'homepage', 'national'))


def _address(row):
    """Road address preferred, lot address next, administrative names last."""
    road = ' '.join(filter(None, [row[RDNMADR_ONE], row[RDNMADR_TWO]]))
    if road:
        return road
    names = [row[CTPRVN_NM], row[MANAGE_SIGNGU_NM] or row[SIGNGU_NM], row[MANAGE_EMD_NM]]
    return row[ADDR_ONE] or ' '.join(filter(None, names)) or '주소 미제공'


def _load_snapshot():
    rows = []
    register_rows = 0
    deleted = 0
    closed = 0
    unlinked = 0
    for row in read_columns(FACILITY_FILE, COLUMNS):
        register_rows += 1
        if row[DEL_AT] == 'Y':
            deleted += 1
            continue
        key = geo_key(row[FCLTY_NM], row[FCLTY_LA], row[FCLTY_LO])
        if key is None:
            unlinked += 1
        if row[STATE_VALUE] and row[STATE_VALUE] != OPERATING:
            closed += 1
        rows.append(Facility(
            id=f'facility-{len(rows)}',
            geo_key=key,
            name=row[FCLTY_NM] or '시설명 미제공',
            flag=row[FLAG_NM] or '구분 미제공',
            state=row[STATE_VALUE] or '운영상태 미제공',
            region=row[CTPRVN_NM] or '지역 미제공',
            # The management district is the one that agrees with the address.
            district=row[MANAGE_SIGNGU_NM] or row[SIGNGU_NM] or '시군구 미제공',
            emd=row[MANAGE_EMD_NM],
            address=_address(row),
            industry=row[INDUTY_NM] or '업종 미제공',
            facility_type=row[FCLTY_TY_NM] or '유형 미제공',
            owner=row[POSESN_MBY_NM] or '보유주체 미제공',
            operation=row[OPER_STLE] or '운영형태 미제공',
            indoor=row[NDOR_SDIV] or '미제공',
            department=row[DEPT_NM] or '미제공',
            phone=row[FCLTY_TEL] or row[DEPT_TEL] or '미제공',
            area=to_number(row[AR_CO]),
            capacity=to_number(row[ACMD_CO]),
            homepage=row[HMPG_URL],
            national=row[NATION_AT] == 'Y',
        ))
    report = {
        'register_rows': register_rows,
        'facilities': len(rows),
        'deleted': deleted,
        'closed': closed,
        'unlinked': unlinked,
        'source': FACILITY_FILE,
    }
    return rows, report


# 시설 CSV 세대별로 프로세스 내부 목록을 한 번만 만든다.
_snapshot_cache = VersionedCsvCache(FACILITY_FILE, _load_snapshot)


def _snapshot():
    return _snapshot_cache.get()


_snapshot.cache_clear = _snapshot_cache.clear


def facilities():
    """Every facility the register does not flag as deleted, closed ones included."""
    return _snapshot()[0]


def load_report():
    """Row accounting shown with the results so the page states its own coverage."""
    return _snapshot()[1]
