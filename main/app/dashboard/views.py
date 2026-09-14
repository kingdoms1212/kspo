"""Dashboard controller: request -> service -> template."""
from ..common.partials import render_screen
from .services import courses_per_facility, dashboard_data, region_chart_rows, requests_per_course

def dashboard(request):
    region = request.GET.get('region', '')
    context = dashboard_data(region)
    chart_rows = region_chart_rows(context.get('areas', []))
    context['region_chart_rows'] = chart_rows
    context['region_chart_max'] = max((item.get('requests') or 0 for item in chart_rows), default=0)
    context['courses_per_facility'] = courses_per_facility(context.get('facilities'), context.get('courses'))
    context['requests_per_course'] = requests_per_course(context.get('courses'), context.get('requests'))
    context.update({'page': 'dashboard', 'selected_region': region})
    return render_screen(request, 'dashboard/index.html', 'dashboard/_body.html', context)
