"""Facility page and export controllers."""
from urllib.parse import urlencode
from django.core.paginator import Paginator
from django.shortcuts import render
from ..common.exports import excel_response
from .models import facilities as facility_rows
from .services import filter_facilities

def facilities(request):
    region = request.GET.get('region', '')
    query = request.GET.get('query', '')
    rows = filter_facilities(facility_rows(), region, query)
    selected_id = request.GET.get('facilityId', '')
    selected = next((row for row in rows if row['id'] == selected_id), None)
    context = {
        'page': 'facilities',
        'rows': rows,
        'page_obj': Paginator(rows, 20).get_page(request.GET.get('page')),
        'page_query': urlencode({'region': region, 'query': query, 'facilityId': selected_id}),
        'selected': selected,
        'regions': sorted({row['region'] for row in facility_rows()}),
        'selected_id': selected_id,
        'selected_region': region,
        'query': query,
    }
    return render(request, 'facilities/index.html', context)

def export_facilities(request):
    rows = filter_facilities(facility_rows(), request.GET.get('region', ''), request.GET.get('query', ''))
    return excel_response('SPORT_INSIGHT_facilities.xlsx', ['시설 ID', '시설명', '지역', '주소', '전화', '주요 종목', '등록 상태'], [
        [row['id'], row['name'], row['region'], row['address'], row['phone'], row['sport'], row['voucher']] for row in rows
    ])
