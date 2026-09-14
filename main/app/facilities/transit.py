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
import heapq
from functools import lru_cache

from ..common.data import data_path, normalize, read_columns

TRANSIT_FILE = '체육시설 인접 대중교통 정보.csv'

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


@lru_cache(maxsize=1)
def _index(wanted):
    """Nearest stops per facility, keyed by position.

    `wanted` is the set of facility keys the register actually holds, passed in
    so the index skips rows for sites the screen can never show.
    """
    if not data_path(TRANSIT_FILE).exists():
        return None
    index = {}
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
    return index


def stops_for(facility, wanted):
    """Nearest stops for one facility, or the reason none can be shown."""
    if facility.geo_key is None:
        return _result(error=NO_POSITION)
    index = _index(wanted)
    if index is None:
        return _result(error=MISSING_SOURCE)
    record = index.get(facility.geo_key)
    if record is None:
        return _result()
    bus, subway, heap = record
    stops = [{'mode': mode or '미제공',
              'name': stop or '정류장명 미제공',
              'seconds': seconds,
              'minutes': round(seconds / 60) if seconds is not None else None,
              'walk_distance': walk,
              'straight_distance': straight,
              'metres': None if -far == FAR else round(-far)}
             for far, mode, stop, walk, straight, seconds in sorted(heap, reverse=True)]
    return _result(stops=stops, bus=bus, subway=subway)


def _result(stops=(), bus=0, subway=0, error=''):
    """Stops are ordered by straight-line distance; walk time is shown where recorded."""
    walks = [stop['minutes'] for stop in stops if stop['minutes'] is not None]
    metres = [stop['metres'] for stop in stops if stop['metres'] is not None]
    return {'stops': stops, 'bus': bus, 'subway': subway, 'total': bus + subway,
            'shown': len(stops), 'keep': KEEP,
            'nearest_metres': min(metres) if metres else None,
            'nearest_minutes': min(walks) if walks else None,
            'walk_known': len(walks),
            'error': error, 'has_records': bool(stops), 'source': TRANSIT_FILE}


def cache_clear():
    _index.cache_clear()
