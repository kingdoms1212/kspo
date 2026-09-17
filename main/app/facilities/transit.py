"""Nearby public transport for a facility.

Source: the adjacent-transport register, one row per facility and stop pair.

Matching is geometric, not textual. The two registers write addresses in
different systems -- this file gives a road name where the facility register
gives a lot number -- so an address join lands only 16% of the time. Names
alone are worse: within a single district the same name (야외운동기구,
게이트볼장) belongs to many different places, and 4,978 name-and-district keys
cover more than one address in this file. Coordinates rounded to six decimals
plus the facility name identify one physical site and match 30,806 facilities,
86.7% of the public ones in the register.

The file holds 1.6 million rows, so the index is built on first use rather than
at start-up: only a reader who opens a facility detail pays for it, once.
"""
import csv
import heapq

from django.conf import settings

from ..common.data import columns_present, data_path, normalize, read_columns
from ..common.sources import TRANSIT
from ..common.versioned_csv import VersionedCsvCache

TRANSIT_FILE = settings.DATA_FILES['transit']

COLUMNS = ('ALSFC_NM', 'ALSFC_LA', 'ALSFC_LO', 'PBTRNSP_FCLTY_SDIV_NM',
           'STRT_DSTNC_VALUE', 'WLKG_DSTNC_VALUE', 'WLKG_MVMN_TIME', 'BSTP_SUBWAYST_NM')
(NM, LA, LO, MODE, STRT_DSTNC, WLKG_DSTNC, WLKG_TIME, STOP_NM) = range(len(COLUMNS))

SUBWAY = '지하철'
# Enough for the detail panel and its export; the register runs to 1,120 stops
# for one facility, which is a list nobody reads.
KEEP = 10
# Ordering uses straight-line distance, which every row carries, rather than
# walk time, which 53.9% of rows leave blank. Mixing the two would rank a stop
# 20m away below one that happens to record a fifteen minute walk.
FAR = float('inf')

MISSING_SOURCE = '대중교통 자료를 읽을 수 없습니다. 자료 파일을 확인해 주세요.'
NO_POSITION = '시설 좌표가 없어 인접 대중교통을 확인할 수 없습니다.'

# [SG001] - 시설 현황 데이터 예외처리 보완
# 정류장이 보이지 않는 이유는 넷이고 성격이 서로 다르다. 앞의 둘은 자료나 설비의
# 문제이고, 뒤의 둘은 이 자료의 수록 범위다. 화면이 같은 문구로 뭉뚱그리면 담당자가
# 범위 밖인 시설을 자료 누락으로 오해한다.
REASON_SOURCE = 'source'          # 파일이 없거나 읽히지 않거나 열 구조가 바뀜
REASON_NO_POSITION = 'no_position'  # 시설 등록부에 좌표가 없음
REASON_NOT_PUBLIC = 'not_public'    # 민간 신고·등록 시설 — 이 자료의 대상이 아님
REASON_NOT_LISTED = 'not_listed'    # 공공시설인데 이 자료에 수록되지 않음
PUBLIC_FLAG = '공공'


def geo_key(name, latitude, longitude):
    """One physical site: its name plus its position to six decimals.

    Returns None unless all three are usable, so a facility without a position
    reports as unmatched instead of being joined on its name alone.
    """
    name = normalize(name)
    if not name:
        return None
    try:
        latitude = round(float(latitude), 6)
        longitude = round(float(longitude), 6)
    except (TypeError, ValueError):
        return None
    if not latitude or not longitude:
        return None
    return name, latitude, longitude


def _seconds(value):
    return int(value) if value.isdigit() else None


def _distance(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return FAR


def _load_index(wanted):
    """Nearest stops per facility, keyed by position.

    `wanted` is the set of facility keys the register actually holds, passed in
    so the index skips rows for sites the screen can never show.
    """
    # [SG001] - 시설 현황 데이터 예외처리 보완
    # 열 구조가 바뀌면 read_columns는 조용히 빈 결과를 낸다. 미리 확인해 두면
    # '자료를 읽을 수 없음'과 '이 시설에 기록이 없음'이 섞이지 않는다.
    if not columns_present(TRANSIT_FILE, COLUMNS):
        return None
    index = {}
    try:
        _fill(index, wanted)
    except (OSError, UnicodeError, csv.Error):
        # [SG001] - 읽다 만 색인은 쓸 수 없다. 반쯤 채워진 결과를 정상처럼
        # 돌려주면 수록된 시설조차 '기록 없음'으로 보인다.
        return None
    return index


# 교통 CSV 세대와 시설 좌표 집합이 같을 때만 색인을 재사용한다.
_index_cache = VersionedCsvCache(TRANSIT_FILE, _load_index)


def _index(wanted):
    # 최초 적재에서 원본이 없으면 기존 오류 사유 형식을 그대로 반환한다.
    if not data_path(TRANSIT_FILE).exists():
        return None
    return _index_cache.get(wanted)


_index.cache_clear = _index_cache.clear


def _fill(index, wanted):
    """[SG001] - 시설 현황 데이터 예외처리 보완 : 실제 적재. 실패는 호출부가 잡는다."""
    for row in read_columns(TRANSIT_FILE, COLUMNS):
        key = geo_key(row[NM], row[LA], row[LO])
        if key is None or key not in wanted:
            continue
        record = index.get(key)
        if record is None:
            index[key] = record = [0, 0, []]
        if row[MODE] == SUBWAY:
            record[1] += 1
        else:
            record[0] += 1
        # A bounded max-heap keeps the nearest KEEP without holding 1.6M rows.
        entry = (-_distance(row[STRT_DSTNC]), row[MODE], row[STOP_NM],
                 row[WLKG_DSTNC], row[STRT_DSTNC], _seconds(row[WLKG_TIME]))
        stops = record[2]
        if len(stops) < KEEP:
            heapq.heappush(stops, entry)
        elif entry[0] > stops[0][0]:
            heapq.heapreplace(stops, entry)


def stops_for(facility, wanted):
    """Nearest stops for one facility, or the reason none can be shown.

    [SG001] - 시설 현황 데이터 예외처리 보완
    비어 있는 결과에도 사유 코드를 담는다. 화면이 '문구가 있는가'로 갈리면
    범위 밖인 시설과 실제 결손을 구분할 수 없다.
    """
    # [SG001] 좌표가 없으면 색인이 필요 없다. 먼저 걸러 1.6M행 적재를 건너뛴다.
    if facility.geo_key is None:
        return _result(error=NO_POSITION, reason=REASON_NO_POSITION)
    index = _index(wanted)
    if index is None:
        return _result(error=MISSING_SOURCE, reason=REASON_SOURCE)
    listed = len(index)
    record = index.get(facility.geo_key)
    if record is None:
        # 민간 신고·등록 시설은 이 자료의 대상이 아니다. 같은 '기록 없음'이라도
        # 공공시설이 빠진 것과는 뜻이 다르므로 갈라서 알린다.
        reason = REASON_NOT_LISTED if facility.flag == PUBLIC_FLAG else REASON_NOT_PUBLIC
        return _result(reason=reason, listed=listed)
    bus, subway, heap = record
    stops = [{'mode': mode or '미제공',
              'name': stop or '정류장명 미제공',
              'seconds': seconds,
              'minutes': round(seconds / 60) if seconds is not None else None,
              'walk_distance': walk,
              'straight_distance': straight,
              'metres': None if -far == FAR else round(-far)}
             for far, mode, stop, walk, straight, seconds in sorted(heap, reverse=True)]
    return _result(stops=stops, bus=bus, subway=subway, listed=listed)


def _result(stops=(), bus=0, subway=0, error='', reason='', listed=0):
    """Stops are ordered by straight-line distance; walk time is shown where recorded.

    [SG001] - 시설 현황 데이터 예외처리 보완
    `reason`은 비어 있는 이유, `listed`는 이 자료가 담고 있는 시설 수다. 화면이
    '왜 없는지'와 '자료가 원래 얼마나 담고 있는지'를 함께 말할 수 있게 한다.
    """
    walks = [stop['minutes'] for stop in stops if stop['minutes'] is not None]
    metres = [stop['metres'] for stop in stops if stop['metres'] is not None]
    return {'stops': stops, 'bus': bus, 'subway': subway, 'total': bus + subway,
            'shown': len(stops), 'keep': KEEP,
            'nearest_metres': min(metres) if metres else None,
            'nearest_minutes': min(walks) if walks else None,
            'walk_known': len(walks), 'reason': reason, 'listed': listed,
            'error': error, 'has_records': bool(stops), 'source': TRANSIT_FILE}


def cache_clear():
    _index.cache_clear()
