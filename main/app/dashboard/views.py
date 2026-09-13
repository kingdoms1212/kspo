"""Dashboard controller: request -> service -> template."""
from django.shortcuts import render
from .services import dashboard_data, region_chart_rows

def dashboard(request):
    region = request.GET.get('region', '')
    context = dashboard_data(region)
    chart_rows = region_chart_rows(context.get('regions', []))
    context['region_chart_rows'] = chart_rows
    context['region_chart_max'] = max((item.get('beneficiary') or 0 for item in chart_rows), default=0)
    context.update({'page': 'dashboard', 'selected_region': region})
    return render(request, 'dashboard/index.html', context)
