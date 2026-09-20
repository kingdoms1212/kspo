"""Program search, sorting and summaries shared by page and export."""
from collections import Counter

from . import models
from ..shared.regions import region_district_map

SORT_LABELS = {
    'name': '강좌명순',
    'facility': '시설명순',
    'region': '지역명순',
    'sport': '종목순',
    'fee': '수강료순',
}
WEEKDAYS = ('월', '화', '수', '목', '금', '토', '일')


BUDGET_UNIT_WON = 1_000


def _whole_number(value):
    """입력 문자열을 0 이상의 정수로 변환하고 빈 값은 None으로 유지한다."""
    text = str(value or '').strip().replace(',', '')
    if not text:
        return None
    number = int(text)
    if number < 0:
        raise ValueError
    return number


def program_budget_plan(params):
    """예산 범위를 검증하고 천원 입력값을 계산용 원 단위로 변환한다."""
    field_names = ('budget_min', 'budget_max')
    active = any(str(params.get(name, '')).strip() for name in field_names)
    plan = {
        'active': active,
        'valid': True,
        'error': '',
        'minimum_won': None,
        'maximum_won': None,
    }
    if not active:
        return plan

    try:
        minimum = _whole_number(params.get('budget_min'))
        maximum = _whole_number(params.get('budget_max'))
    except ValueError:
        plan.update(valid=False, error='예산 조건에는 0 이상의 정수만 입력해 주세요.')
        return plan

    errors = []
    if minimum is None and maximum is None:
        errors.append('최소 또는 최대 예산을 입력해 주세요.')
    if minimum is not None and maximum is not None and minimum > maximum:
        errors.append('최소 예산은 최대 예산보다 클 수 없습니다.')

    plan.update(
        valid=not errors,
        error=' '.join(errors),
        minimum_won=None if minimum is None else minimum * BUDGET_UNIT_WON,
        maximum_won=None if maximum is None else maximum * BUDGET_UNIT_WON,
    )
    return plan


def _filter_by_budget(rows, plan):
    """원본 수강료가 입력한 예산 범위에 포함되는 프로그램만 남긴다."""
    filtered = []
    for item in rows:
        # The repository already parsed the fee to an int, or None when absent.
        fee = item.fee
        if fee is None or fee < 0:
            continue
        if plan['minimum_won'] is not None and fee < plan['minimum_won']:
            continue
        if plan['maximum_won'] is not None and fee > plan['maximum_won']:
            continue
        filtered.append(item)
    return filtered


def deduplicate_programs(rows):
    """화면에 표시되는 여섯 항목이 모두 같은 강좌는 첫 행만 유지한다.

    원본 CSV와 저장소 스냅샷은 건드리지 않는다. 검색 정렬 뒤 이 함수를
    적용하므로 같은 그룹에서는 현재 정렬 결과상 첫 번째 강좌가 남는다.
    """
    seen = set()
    unique_rows = []
    for item in rows:
        key = (item.name, item.facility, item.region, item.sport, item.weekday, item.fee)
        if key in seen:
            continue
        seen.add(key)
        unique_rows.append(item)
    return unique_rows


def selected_weekdays(value):
    """요일 선택값을 월요일부터 일요일 순서의 고유 목록으로 정규화한다."""
    text = str(value or '').strip()
    return tuple(day for day in WEEKDAYS if day in text)


def filter_programs(params, budget_plan=None):
    """검색 조건과 유효한 예산 조건을 적용하고 요청한 기준으로 정렬한다."""
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
    weekday_value = str(params.get('weekday') or '').strip()
    weekdays = selected_weekdays(weekday_value)
    if len(weekdays) == 1:
        # 한 요일 선택은 해당 요일이 운영 요일에 포함된 강좌를 모두 표시한다.
        result = [item for item in result if weekdays[0] in selected_weekdays(item.weekday)]
    elif len(weekdays) >= 2:
        # 여러 요일 선택은 선택한 요일 구성과 정확히 같은 강좌만 표시한다.
        result = [item for item in result if selected_weekdays(item.weekday) == weekdays]
    elif weekday_value:
        # 기존 북마크나 직접 입력한 비표준 값은 이전의 부분 일치 방식을 유지한다.
        result = [item for item in result if weekday_value in item.weekday]
    program_query = str(params.get('program_query') or '').strip().lower()
    facility_query = str(params.get('facility_query') or '').strip().lower()
    if program_query:
        result = [item for item in result if program_query in item.name.lower()]
    if facility_query:
        result = [item for item in result if facility_query in item.facility.lower()]
    if params.get('query') and not program_query and not facility_query:
        # 기존 주소의 통합 검색어는 예전 북마크 호환을 위해 유지한다.
        query = str(params['query']).strip().lower()
        result = [item for item in result if query in item.name.lower() or query in item.facility.lower()]
    plan = budget_plan if budget_plan is not None else program_budget_plan(params)
    if plan['active'] and plan['valid']:
        result = _filter_by_budget(result, plan)
    sort_value = params.get('sort') or 'name_asc'
    if sort_value.endswith('_desc'):
        sort_key, descending = sort_value[:-5], True
    elif sort_value.endswith('_asc'):
        sort_key, descending = sort_value[:-4], False
    else:
        # 기존 정렬 주소의 sort와 sort_direction 조합도 계속 지원한다.
        sort_key = sort_value
        descending = params.get('sort_direction') == 'desc'
    if sort_key == 'fee':
        # 수강료 미제공 강좌는 정렬 방향과 관계없이 마지막에 배치한다.
        priced = [item for item in result if item.fee is not None]
        unpriced = [item for item in result if item.fee is None]
        priced.sort(key=lambda item: (item.fee, item.name, item.id), reverse=descending)
        unpriced.sort(key=lambda item: (item.name, item.id), reverse=descending)
        result = priced + unpriced
    elif sort_key == 'facility':
        result.sort(key=lambda item: (item.facility, item.name, item.id), reverse=descending)
    elif sort_key == 'region':
        result.sort(
            key=lambda item: (item.region, item.district, item.facility, item.name, item.id),
            reverse=descending,
        )
    elif sort_key == 'sport':
        result.sort(key=lambda item: (item.sport, item.name, item.facility, item.id), reverse=descending)
    elif sort_key == 'walk':
        result.sort(key=lambda item: (item.walk_minutes is None, item.walk_minutes or 0, item.name, item.id))
    elif sort_key == 'capacity':
        result.sort(key=lambda item: (item.capacity is None, -(item.capacity or 0), item.name, item.id))
    else:
        result.sort(key=lambda item: (item.name, item.id), reverse=descending)
    return deduplicate_programs(result)


def program_regions(programs_rows):
    """Distinct regions present in a set of program rows, excluding the 'unknown' placeholder."""
    return sorted({item.region for item in programs_rows if item.region != '지역 미제공'})


def program_facility_types(programs_rows):
    """The register's facility industry code is a short controlled list, so offer it as a choice."""
    return sorted({item.facility_type for item in programs_rows
                   if item.facility_type != '시설유형 미제공'})


def program_region_district_map(programs_rows):
    """Return sorted district options grouped by region from the loaded CSV rows."""
    return region_district_map(programs_rows)

def program_districts(region_district_map, region):
    """District options for one selected region, from an already built map."""
    return region_district_map.get(region, []) if region else []

def program_district_distribution(results):
    """검색된 프로그램을 지역별 시군구 분포로 집계한다.

    공통 지도 모듈이 사용하는 ``{지역: [(시군구, 프로그램 수), ...]}``
    구조를 반환한다. 대시보드 집계와 독립적으로 현재 프로그램 검색
    결과만 계산 대상으로 삼는다.
    """
    totals = {}
    for item in results:
        if item.region == '지역 미제공' or item.district == '시군구 미제공':
            continue
        totals.setdefault(item.region, Counter())[item.district] += 1
    return {
        region: counts.most_common()
        for region, counts in sorted(totals.items())
    }

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
