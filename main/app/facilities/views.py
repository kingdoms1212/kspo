"""Facility page and export controllers."""
from urllib.parse import urlencode
from django.core.paginator import Paginator
from django.http import HttpResponseNotFound
from ..common.exports import EXPORT_ROW_LIMIT, excel_response, over_export_limit
from ..common.partials import render_screen
from . import models
from .services import (facility_flags, facility_industries, facility_owners,
                       facility_regions, facility_states, facility_transit,
                       filter_facilities)

SEARCH_KEYS = ('region', 'industry', 'flag', 'state', 'owner', 'query')


def _search_params(request):
    """Use one query contract for both the page and its export.

    The register keeps closed facilities, so an unfiltered list would present
    35,000 shut sites as if they were open. The operating state defaults to
    `정상운영` and the select shows it, so the narrowing is visible and the
    reader can widen it rather than being silently shown a subset.
    """
    params = {key: request.GET.get(key, '') for key in SEARCH_KEYS}
    if 'state' not in request.GET:
        params['state'] = models.OPERATING
    return params


def _selection(request):
    catalogue = models.facilities()
    params = _search_params(request)
    rows = filter_facilities(catalogue, **params)
    selected_id = request.GET.get('facilityId', '')
    selected = next((row for row in rows if row.id == selected_id), None)
    return catalogue, params, rows, selected_id, selected


def facilities(request):
    catalogue, params, rows, selected_id, selected = _selection(request)
    context = {
        'page': 'facilities',
        'rows': rows,
        'page_obj': Paginator(rows, 20).get_page(request.GET.get('page')),
        'page_query': urlencode({**params, 'facilityId': selected_id}),
        'filter_query': urlencode(params),
        'selected': selected,
        'regions': facility_regions(catalogue),
        'industries': facility_industries(catalogue),
        'flags': facility_flags(catalogue),
        'states': facility_states(catalogue),
        'owners': facility_owners(catalogue),
        'selected_id': selected_id,
        'params': params,
        'transit': facility_transit(selected),
        'load_report': models.load_report(),
        'export_limit': EXPORT_ROW_LIMIT,
    }
    return render_screen(request, 'facilities/index.html', 'facilities/_workspace.html', context)


def export_facilities(request):
    _, _, rows, _, _ = _selection(request)
    refusal = over_export_limit(len(rows))
    if refusal is not None:
        return refusal
    return excel_response('SPORT_INSIGHT_facilities.xlsx',
        ['시설 ID', '시설명', '시설구분', '운영상태', '업종', '시설유형', '지역', '시군구', '읍면동',
         '주소', '보유주체', '운영형태', '실내외', '담당부서', '전화', '면적(㎡)', '수용인원',
         '국민체육센터', '홈페이지', '출처'],
        ([row.id, row.name, row.flag, row.state, row.industry, row.facility_type, row.region,
          row.district, row.emd, row.address, row.owner, row.operation, row.indoor,
          row.department, row.phone, row.area, row.capacity,
          'Y' if row.national else 'N', row.homepage,
          models.FACILITY_FILE] for row in rows))


def export_facility_transit(request):
    *_, selected = _selection(request)
    if selected is None:
        return HttpResponseNotFound('현재 검색 결과에서 시설을 찾을 수 없습니다.')
    linked = facility_transit(selected)
    return excel_response('SPORT_INSIGHT_facility_transit.xlsx',
        ['시설 ID', '시설명', '지역', '시군구', '주소', '교통수단', '정류장·역명',
         '도보 시간(초)', '도보 시간(분)', '도보 거리(m)', '직선 거리(m)', '출처'],
        ([selected.id, selected.name, selected.region, selected.district, selected.address,
          stop['mode'], stop['name'], stop['seconds'], stop['minutes'],
          stop['walk_distance'], stop['straight_distance'], linked['source']]
         for stop in linked['stops']))
