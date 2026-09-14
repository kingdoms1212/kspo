"""Program page and export controllers."""
from urllib.parse import urlencode
from django.core.paginator import Paginator
from ..common.partials import render_screen
from ..common.exports import EXPORT_ROW_LIMIT, excel_response, over_export_limit
from . import models
from .services import (SORT_LABELS, filter_programs, program_facility_types,
                       program_regions, program_summary)

SEARCH_KEYS = ('region', 'district', 'facility_type', 'sport', 'target', 'weekday', 'query', 'sort')


def _search_params(request):
    """Use one query contract for both the page and its export."""
    return {key: request.GET.get(key, '') for key in SEARCH_KEYS}

def programs(request):
    params = _search_params(request)
    results = filter_programs(params)
    catalogue = models.programs()
    context = {
        'page': 'programs',
        'results': results,
        'top_results': results[:3],
        'result_count': len(results),
        'regions': program_regions(catalogue),
        'facility_types': program_facility_types(catalogue),
        'sort_labels': SORT_LABELS,
        'params': params,
        'page_obj': Paginator(results, 20).get_page(request.GET.get('page')),
        'page_query': urlencode(params),
        'export_query': urlencode(params),
        'load_report': models.load_report(),
        'export_limit': EXPORT_ROW_LIMIT,
        **program_summary(results),
    }
    return render_screen(request, 'programs/index.html', 'programs/_results.html', context)

def export_programs(request):
    params = _search_params(request)
    rows = filter_programs(params)
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
