"""Dashboard controller: request -> service -> template."""
from urllib.parse import urlencode

from ..common.partials import render_screen
from ..runtime.diagnostics import trace
from .planning import SPORT_TYPES
from .services import (
    selected_districts, chart_sort, courses_per_facility, dashboard_data, normalized_chart_rows,
    region_chart_rows, requests_per_course, requests_per_facility, requests_per_sport, pie_chart_data,
)

def dashboard(request):
    trace('dashboard.begin', request_id=getattr(request, 'csv_diag_id', '-'))
    region = '서울'
    districts = selected_districts(','.join(request.GET.getlist('district')))
    district = ','.join(districts)
    region_sort = chart_sort(request.GET.get('region_sort', 'desc'))
    sport_sort = chart_sort(request.GET.get('sport_sort', 'desc'))
    context = dashboard_data(region, district) if district else dashboard_data(region)
    trace('dashboard.data.end', request_id=getattr(request, 'csv_diag_id', '-'))
    context.setdefault('region_district_options', {})
    context['district_options'] = context.get('region_district_options', {}).get(region, [])
    chart_rows = region_chart_rows(context.get('areas', []), region_sort)
    context['region_chart_rows'] = chart_rows
    context['region_chart_max'] = max((item.get('requests') or 0 for item in chart_rows), default=0)
    context['courses_per_facility'] = courses_per_facility(context.get('facilities'), context.get('courses'))
    context['requests_per_course'] = requests_per_course(context.get('courses'), context.get('requests'))
    context['requests_per_facility'] = requests_per_facility(context.get('facilities'), context.get('requests'))
    context['sport_chart_rows'] = normalized_chart_rows(context.get('sport_rows', []), sport_sort)
    context['requests_per_sport'] = requests_per_sport(context.get('sport_count'), context.get('requests'))
    context['region_pie'] = pie_chart_data(chart_rows, name_label='지역')
    context['sport_pie'] = pie_chart_data(context['sport_chart_rows'], name_label='종목')
    shape_filter = {'district': district} if district else {}
    context.update({
        'planning_sports': list(SPORT_TYPES),
        'page': 'dashboard', 'selected_region': region, 'selected_district': district, 'selected_districts': districts,
        'region_sort': region_sort, 'sport_sort': sport_sort,
        'region_sort_url': '?' + urlencode({
            'region': region, 'region_sort': 'desc' if region_sort == 'asc' else 'asc',
            'sport_sort': sport_sort,
            **shape_filter,
        }),
        'sport_sort_url': '?' + urlencode({
            'region': region, 'region_sort': region_sort,
            'sport_sort': 'desc' if sport_sort == 'asc' else 'asc',
            **shape_filter,
        }),
    })
    trace('dashboard.render.begin', request_id=getattr(request, 'csv_diag_id', '-'))
    response = render_screen(request, 'dashboard/index.html', 'dashboard/_body.html', context)
    trace('dashboard.render.end', request_id=getattr(request, 'csv_diag_id', '-'))
    return response
