"""Program page and export controllers."""
from urllib.parse import urlencode
from django.core.paginator import Paginator
from django.shortcuts import render
from ..common.exports import excel_response
from . import models
from .services import filter_programs, program_regions, program_summary


def _search_params(request):
    """Use one query contract for both the page and its export."""
    return {key: request.GET.get(key, '') for key in ('region', 'district', 'sport', 'target', 'query', 'sort')}

def programs(request):
    params = _search_params(request)
    results = filter_programs(params)
    context = {
        'page': 'programs',
        'results': results,
        'top_results': results[:3],
        'result_count': len(results),
        'regions': program_regions(models.programs()),
        'params': params,
        'page_obj': Paginator(results, 20).get_page(request.GET.get('page')),
        'page_query': urlencode(params),
        'export_query': urlencode(params),
        **program_summary(results),
    }
    return render(request, 'programs/index.html', context)

def export_programs(request):
    params = _search_params(request)
    rows = filter_programs(params)
    return excel_response('SPORT_INSIGHT_programs.xlsx', ['프로그램 ID', '강좌명', '시설', '지역', '종목', '대상', '요일', '기간', '수강료', '단위'], [
        [row['id'], row['name'], row['facility'], row['region'], row['sport'], row['target'], row['weekday'], row['period'], row['fee'], row['fee_unit']] for row in rows
    ])
