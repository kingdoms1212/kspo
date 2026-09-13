"""Controller layer (Django "views"): parse the request, call the model/service
layer, and hand the result to a template or CSV writer. Business logic and
data access live in `services.py` and `models.py`, not here.
"""
import csv
from io import StringIO
from urllib.parse import urlencode

from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import render

from . import models
from .models import facilities as facility_rows
from .services import (
    dashboard_data,
    filter_facilities,
    filter_programs,
    program_regions,
    program_summary,
    region_chart_rows,
)


def dashboard(request):
    region = request.GET.get('region', '')
    context = dashboard_data(region)
    chart_rows = region_chart_rows(context.get('regions', []))
    context['region_chart_rows'] = chart_rows
    context['region_chart_max'] = max((item.get('beneficiary') or 0 for item in chart_rows), default=0)
    context.update({'page': 'dashboard', 'selected_region': region})
    return render(request, 'dashboard.html', context)


def programs(request):
    params = {key: request.GET.get(key, '') for key in ('region', 'district', 'sport', 'target', 'query', 'sort')}
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
    return render(request, 'programs.html', context)


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
    return render(request, 'facilities.html', context)


def _csv_response(filename, headers, rows):
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(headers)
    writer.writerows(rows)
    response = HttpResponse('﻿' + buffer.getvalue(), content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


def export_facilities(request):
    rows = filter_facilities(facility_rows(), request.GET.get('region', ''), request.GET.get('query', ''))
    return _csv_response('SPORT_INSIGHT_facilities.csv', ['시설 ID', '시설명', '지역', '주소', '전화', '주요 종목', '등록 상태'], [
        [row['id'], row['name'], row['region'], row['address'], row['phone'], row['sport'], row['voucher']] for row in rows
    ])


def export_programs(request):
    params = {key: request.GET.get(key, '') for key in ('region', 'district', 'sport', 'target', 'query', 'sort')}
    rows = filter_programs(params)
    return _csv_response('SPORT_INSIGHT_programs.csv', ['프로그램 ID', '강좌명', '시설', '지역', '종목', '대상', '요일', '기간', '수강료', '단위'], [
        [row['id'], row['name'], row['facility'], row['region'], row['sport'], row['target'], row['weekday'], row['period'], row['fee'], row['fee_unit']] for row in rows
    ])
