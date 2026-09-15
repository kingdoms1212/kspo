"""Dashboard controller: request -> service -> template."""
from urllib.parse import urlencode

from ..common.partials import render_screen
from .services import (
    chart_sort, courses_per_facility, dashboard_data, normalized_chart_rows,
    region_chart_rows, requests_per_course, requests_per_facility, pie_chart_data,
)

def dashboard(request):
    region = request.GET.get('region', '')
    region_sort = chart_sort(request.GET.get('region_sort', 'desc'))
    sport_sort = chart_sort(request.GET.get('sport_sort', 'desc'))
    chart_type = request.GET.get('chart_type', 'bar')
    if chart_type not in ('bar', 'pie'):
        chart_type = 'bar'
    context = dashboard_data(region)
    chart_rows = region_chart_rows(context.get('areas', []), region_sort)
    context['region_chart_rows'] = chart_rows
    context['region_chart_max'] = max((item.get('requests') or 0 for item in chart_rows), default=0)
    context['courses_per_facility'] = courses_per_facility(context.get('facilities'), context.get('courses'))
    context['requests_per_course'] = requests_per_course(context.get('courses'), context.get('requests'))
    context['requests_per_facility'] = requests_per_facility(context.get('facilities'), context.get('requests'))
    context['sport_chart_rows'] = normalized_chart_rows(context.get('sport_rows', []), sport_sort)
    context['chart_type'] = chart_type
    if chart_type == 'pie':
        context['region_pie'] = pie_chart_data(chart_rows)
        context['sport_pie'] = pie_chart_data(context['sport_chart_rows'])
    filters = {'region': region, 'region_sort': region_sort, 'sport_sort': sport_sort}
    # Keep old default URLs concise; preserve the chosen non-default chart mode.
    shape_filter = {'chart_type': chart_type} if chart_type != 'bar' else {}
    context['chart_modes'] = [
        {'type': mode, 'label': label, 'url': '?' + urlencode({**filters, 'chart_type': mode})}
        for mode, label in (('bar', '막대'), ('pie', '원형'))
    ]
    context.update({
        'page': 'dashboard', 'selected_region': region,
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
    return render_screen(request, 'dashboard/index.html', 'dashboard/_body.html', context)
