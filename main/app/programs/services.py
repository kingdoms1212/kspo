"""Program search, sorting and summaries shared by page and export."""
from collections import Counter

from . import models

SORT_LABELS = {'name': '강좌명순', 'fee': '수강료순 · 단위 미확인',
               'walk': '정류장 도보 가까운 순', 'capacity': '모집인원순'}


def filter_programs(params):
    result = list(models.programs())
    if params.get('region'):
        result = [item for item in result if item.region == params['region']]
    if params.get('district'):
        result = [item for item in result if item.district == params['district']]
    if params.get('facility_type'):
        result = [item for item in result if item.facility_type == params['facility_type']]
    if params.get('sport'):
        sport = params['sport'].lower()
        result = [item for item in result if sport in item.sport.lower()]
    if params.get('target'):
        target = params['target'].lower()
        result = [item for item in result if target in item.target.lower()]
    if params.get('weekday'):
        result = [item for item in result if params['weekday'] in item.weekday]
    if params.get('query'):
        query = params['query'].lower()
        result = [item for item in result if query in item.name.lower() or query in item.facility.lower()]
    sort_key = params.get('sort', 'name')
    if sort_key == 'fee':
        result.sort(key=lambda item: (item.fee is None, item.fee or 0, item.name, item.id))
    elif sort_key == 'walk':
        result.sort(key=lambda item: (item.walk_minutes is None, item.walk_minutes or 0, item.name, item.id))
    elif sort_key == 'capacity':
        result.sort(key=lambda item: (item.capacity is None, -(item.capacity or 0), item.name, item.id))
    else:
        result.sort(key=lambda item: (item.name, item.id))
    return result


def program_regions(programs_rows):
    """Distinct regions present in a set of program rows, excluding the 'unknown' placeholder."""
    return sorted({item.region for item in programs_rows if item.region != '지역 미제공'})


def program_facility_types(programs_rows):
    """The register's facility industry code is a short controlled list, so offer it as a choice."""
    return sorted({item.facility_type for item in programs_rows
                   if item.facility_type != '시설유형 미제공'})


def program_summary(results):
    """Aggregate counts shown on the programs page summary strip."""
    walks = [item.walk_minutes for item in results if item.walk_minutes is not None]
    return {
        'region_distribution': Counter(item.region for item in results).most_common(),
        'fee_count': sum(1 for item in results if item.fee is not None),
        'facility_count': len({(item.facility, item.address) for item in results
                               if item.facility != '시설명 미제공'}),
        'walk_median': sorted(walks)[len(walks) // 2] if walks else None,
    }
