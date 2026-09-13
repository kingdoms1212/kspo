"""Service layer.

Business rules and query logic (filtering, sorting, aggregating, calculating)
that sit between the model layer (`models.py`, raw data access) and the
controller layer (`views.py`, request/response handling). Keeping this logic
here instead of in views keeps views thin and keeps the same rule usable from
both a page view and its CSV export.
"""
from collections import Counter

from . import models


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
        'programs': len(models.programs()),
        'sports': models.usage_by_sport().most_common(5),
        'region_options': sorted({item['region'] for item in models.coverage() if item['region'] != '지역 미제공'}),
        'period': sorted({item['period'] for item in region_rows if item['period']})[-1:] or ['기준일 미확인'],
    }


def _sum_known(values):
    values = [value for value in values if value is not None]
    return sum(values) if values else None


def filter_programs(params):
    result = models.programs()
    if params.get('region'):
        result = [item for item in result if item['region'] == params['region']]
    if params.get('district'):
        result = [item for item in result if item['district'] == params['district']]
    if params.get('sport'):
        result = [item for item in result if params['sport'].lower() in item['sport'].lower()]
    if params.get('target'):
        result = [item for item in result if params['target'].lower() in item['target'].lower()]
    if params.get('query'):
        query = params['query'].lower()
        result = [item for item in result if query in item['name'].lower() or query in item['facility'].lower()]
    sort_key = params.get('sort', 'name')
    if sort_key == 'fee':
        result.sort(key=lambda item: (models.to_number(item['fee']) is None, models.to_number(item['fee']) or 0, item['name'], item['id']))
    else:
        result.sort(key=lambda item: (item['name'], item['id']))
    return result


def filter_facilities(rows, region='', query=''):
    """Apply the region/text filters shared by the facilities page and its CSV export."""
    if region:
        rows = [row for row in rows if row['region'] == region]
    if query:
        query = query.lower()
        rows = [row for row in rows if query in row['name'].lower() or query in row['address'].lower()]
    return rows


def benefit_rate(target_count, beneficiary_count):
    """Return a ratio only when both counts are known and the denominator is valid."""
    if target_count is None or beneficiary_count is None or target_count <= 0:
        return None
    return beneficiary_count / target_count


def nearest_stop_minutes(walking_seconds):
    """Return the minimum observed facility-to-stop walk time, preserving missing data."""
    valid = [value for value in walking_seconds if value is not None and value >= 0]
    return min(valid) / 60 if valid else None


def calculate_budget(budget, planned_people, months, fee):
    """Calculate a monthly, per-person fee scenario without inferring other fee units."""
    if budget is None:
        return {'status': 'not_requested', 'cost': None, 'supported_people': None}
    if planned_people is None or planned_people < 1 or months is None or months < 1:
        return {'status': 'invalid_plan', 'cost': None, 'supported_people': None}
    if fee is None or fee < 0:
        return {'status': 'unverified_fee', 'cost': None, 'supported_people': None}
    cost = fee * planned_people * months
    supported = None if fee == 0 else budget // (fee * months)
    return {
        'status': 'within_budget' if cost <= budget else 'over_budget',
        'cost': cost,
        'supported_people': supported,
    }


def region_chart_rows(regions):
    """Sort coverage rows for the dashboard chart: known beneficiary counts first, descending."""
    return sorted(regions, key=lambda item: (item.get('beneficiary') is None, -(item.get('beneficiary') or 0)))


def program_regions(programs_rows):
    """Distinct regions present in a set of program rows, excluding the 'unknown' placeholder."""
    return sorted({item['region'] for item in programs_rows if item['region'] != '지역 미제공'})


def program_summary(results):
    """Aggregate counts shown on the programs page summary strip."""
    return {
        'region_distribution': Counter(item['region'] for item in results).most_common(),
        'fee_count': sum(1 for item in results if item['fee']),
        'facility_count': len({item['facility'] for item in results if item['facility'] != '시설 연결 미확인'}),
    }
