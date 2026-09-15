"""Program page and export controllers."""
from urllib.parse import urlencode
from django.core.paginator import Paginator
from ..common.partials import render_screen
from ..common.exports import EXPORT_ROW_LIMIT, excel_response, over_export_limit
from . import models
from .services import (SORT_LABELS, WEEKDAYS, filter_programs, program_budget_plan,
                       program_district_distribution, program_districts,
                       program_facility_types, program_regions,
                       program_region_district_map,
                       program_summary, selected_weekdays)

SEARCH_KEYS = ('region', 'district', 'facility_type', 'sport', 'target', 'weekday',
               'program_query', 'facility_query', 'query', 'sort',
               'sort_direction', 'budget_min', 'budget_max')

# Keep the existing controller patch point while importing the service module.

def _search_params(request):
    """Use one query contract for both the page and its export."""
    return {key: request.GET.get(key, '') for key in SEARCH_KEYS}


def _scroll_position(request):
    """Echo back the position the search form recorded, digits only."""
    value = request.GET.get('_scroll', '')
    return value if value.isdigit() else ''

def programs(request):
    params = _search_params(request)
    budget_plan = program_budget_plan(params)
    results = filter_programs(params, budget_plan)
    catalogue = models.programs()
    weekday_selection = selected_weekdays(params['weekday'])
    page_obj = Paginator(results, 20).get_page(request.GET.get('page'))
    jump_previous_page = max(1, page_obj.number - 10) if page_obj.has_previous() else None
    jump_next_page = min(page_obj.paginator.num_pages, page_obj.number + 10) if page_obj.has_next() else None
    # One pass over the catalogue feeds both the cascading select and its JSON copy.
    region_district_map = program_region_district_map(catalogue)
    context = {
        'page': 'programs',
        'results': results,
        'result_count': len(results),
        'regions': program_regions(catalogue),
        'facility_types': program_facility_types(catalogue),
        'region_district_map': region_district_map,
        'districts': program_districts(region_district_map, params['region']),
        # 현재 검색 결과를 시군구 지도에 표시할 프로그램 건수로 집계한다.
        'district_distribution': program_district_distribution(results),
        'budget_plan': budget_plan,
        'scroll_position': _scroll_position(request),
        'sort_labels': SORT_LABELS,
        'weekdays': WEEKDAYS,
        'selected_weekdays': weekday_selection,
        'weekday_label': ', '.join(weekday_selection),
        'params': params,
        'page_obj': page_obj,
        'jump_previous_page': jump_previous_page,
        'jump_next_page': jump_next_page,
        'page_query': urlencode(params),
        'export_query': urlencode(params),
        'load_report': models.load_report(),
        'export_limit': EXPORT_ROW_LIMIT,
        **program_summary(results),
    }
    return render_screen(request, 'programs/index.html', 'programs/_results.html', context)

def export_programs(request):
    params = _search_params(request)
    # The export applies the same budget range the page did.
    rows = filter_programs(params, program_budget_plan(params))
    refusal = over_export_limit(len(rows))
    if refusal is not None:
        return refusal
    return excel_response('SPORT_INSIGHT_programs.xlsx',
        ['프로그램 ID', '강좌명', '시설', '시설유형', '주소', '지역', '시군구', '전화', '종목',
         '대상', '요일', '시간', '기간', '모집인원', '수강료 원자료', '금액 단위',
         '정류장 도보(분)', '인접 정류장', '홈페이지', '출처'],
        ([row.id, row.name, row.facility, row.facility_type, row.address, row.region,
          row.district, row.phone, row.sport, row.target, row.weekday, row.time, row.period,
          row.capacity, row.fee, row.fee_unit, row.walk_minutes, row.stop, row.homepage,
          models.PROGRAM_FILE] for row in rows))
