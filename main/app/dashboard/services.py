"""Dashboard aggregates and presentation data."""
from . import models
from ..programs.models import programs

def dashboard_data(region=''):
    region_rows = [item for item in models.coverage() if not region or item['region'] == region]
    target = _sum_known(item['target'] for item in region_rows)
    beneficiary = _sum_known(item['beneficiary'] for item in region_rows)
    facilities_count = _sum_known(item['facility_count'] for item in region_rows)
    return {
        'regions': region_rows,
        'target': target,
        'beneficiary': beneficiary,
        'facilities': facilities_count,
        'programs': len(programs()),
        'sports': models.usage_by_sport().most_common(5),
        'region_options': sorted({item['region'] for item in models.coverage() if item['region'] != '지역 미제공'}),
        'period': sorted({item['period'] for item in region_rows if item['period']})[-1:] or ['기준일 미확인'],
    }

def _sum_known(values):
    values = [value for value in values if value is not None]
    return sum(values) if values else None

def region_chart_rows(regions):
    """Sort coverage rows for the dashboard chart: known beneficiary counts first, descending."""
    return sorted(regions, key=lambda item: (item.get('beneficiary') is None, -(item.get('beneficiary') or 0)))
