"""Program search, sorting and summaries shared by page and export."""
from collections import Counter
from . import models
from ..common.data import to_number

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
        fee = to_number(item.get('fee'))
        if fee is None or fee < 0:
            continue
        if plan['minimum_won'] is not None and fee < plan['minimum_won']:
            continue
        if plan['maximum_won'] is not None and fee > plan['maximum_won']:
            continue
        filtered.append(item)
    return filtered


def filter_programs(params, budget_plan=None):
    """검색 조건과 유효한 예산 조건을 적용하고 요청한 기준으로 정렬한다."""
    result = list(models.programs())
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
    plan = budget_plan if budget_plan is not None else program_budget_plan(params)
    if plan['active'] and plan['valid']:
        result = _filter_by_budget(result, plan)
    sort_key = params.get('sort', 'name')
    if sort_key == 'fee':
        result.sort(key=lambda item: (to_number(item['fee']) is None, to_number(item['fee']) or 0, item['name'], item['id']))
    else:
        result.sort(key=lambda item: (item['name'], item['id']))
    return result

def program_regions(programs_rows):
    """Distinct regions present in a set of program rows, excluding the 'unknown' placeholder."""
    return sorted({item['region'] for item in programs_rows if item['region'] != '지역 미제공'})

def program_region_district_map(programs_rows):
    """Return sorted district options grouped by region from the loaded CSV rows."""
    region_districts = {}
    for item in programs_rows:
        region = item.get('region')
        district = item.get('district')
        if not region or region == '지역 미제공' or not district:
            continue
        region_districts.setdefault(region, set()).add(district)
    return {
        region: sorted(districts)
        for region, districts in sorted(region_districts.items())
    }

def program_districts(programs_rows, region):
    """Return the district options available for one selected region."""
    if not region:
        return []
    return program_region_district_map(programs_rows).get(region, [])

def program_seoul_district_distribution(results):
    """Count filtered program rows for each Seoul district used by the drill-down map."""
    seoul_names = {'서울', '서울특별시'}
    return Counter(
        item['district']
        for item in results
        if item.get('region') in seoul_names and item.get('district')
    ).most_common()

def program_summary(results):
    """Aggregate counts shown on the programs page summary strip."""
    return {
        'region_distribution': Counter(item['region'] for item in results).most_common(),
        'fee_count': sum(1 for item in results if item['fee']),
        'facility_count': len({item['facility'] for item in results if item['facility'] != '시설 연결 미확인'}),
    }
