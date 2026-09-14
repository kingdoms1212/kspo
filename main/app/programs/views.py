"""Program page and export controllers."""
from urllib.parse import urlencode
from django.core.paginator import Paginator
from django.shortcuts import render
from ..common.exports import excel_response
from . import models
from . import services

# Keep the existing controller patch point while importing the service module.
filter_programs = services.filter_programs

def _search_params(request):
    """Use one query contract for both the page and its export."""
    fields = (
        'region', 'district', 'sport', 'target', 'query', 'sort',
        'budget_min', 'budget_max',
    )
    return {key: request.GET.get(key, '') for key in fields}

def programs(request):
    params = _search_params(request)
    program_rows = models.programs()
    region_district_map = services.program_region_district_map(program_rows)
    districts = region_district_map.get(params['region'], [])

    # 다른 지역으로 변경했는데 이전 시군구가 남아 있는 경우 초기화
    if params['district'] not in districts:
        params['district'] = ''

    # 입력이 유효할 때만 프로그램별 예상 총비용 필터를 적용한다.
    budget_plan = services.program_budget_plan(params)
    results = filter_programs(params, budget_plan=budget_plan)
    context = {
        'page': 'programs',
        'results': results,
        'top_results': results[:3],
        'result_count': len(results),
        'regions': services.program_regions(program_rows),
        'districts': districts,
        'region_district_map': region_district_map,
        'seoul_district_distribution': services.program_seoul_district_distribution(results),
        'budget_plan': budget_plan,
        'scroll_position': request.GET.get('_scroll', ''),
        'params': params,
        'page_obj': Paginator(results, 20).get_page(request.GET.get('page')),
        'page_query': urlencode(params),
        'export_query': urlencode(params),
        **services.program_summary(results),
    }
    return render(request, 'programs/index.html', context)

def export_programs(request):
    params = _search_params(request)
    rows = filter_programs(params)
    return excel_response('SPORT_INSIGHT_programs.xlsx', ['프로그램 ID', '강좌명', '시설', '지역', '종목', '대상', '요일', '기간', '수강료', '단위'], [
        [row['id'], row['name'], row['facility'], row['region'], row['sport'], row['target'], row['weekday'], row['period'], row['fee'], row['fee_unit']] for row in rows
    ])
