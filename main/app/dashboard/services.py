"""Dashboard aggregates and presentation data."""
from collections import Counter

from . import models


def dashboard_data(region=''):
    snapshot = models.usage_snapshot()
    areas = [area for area in snapshot['areas'] if not region or area['region'] == region]
    sports = Counter()
    for area in areas:
        sports.update(area['sports'])
    months = sorted({month for area in areas for month in (area['first_month'], area['last_month']) if month})
    return {
        'areas': areas,
        'facilities': _sum_known(area['facilities'] for area in areas),
        'courses': _sum_known(area['courses'] for area in areas),
        'requests': _sum_known(area['requests'] for area in areas),
        'sports': sports.most_common(5),
        'region_options': sorted({area['region'] for area in snapshot['areas']
                                  if area['region'] != '지역 미제공'}),
        'period': [f'{months[0]} ~ {months[-1]}'] if months else ['기준일 미확인'],
        'load_report': {'ledger_rows': snapshot['ledger_rows'],
                        'unidentified': snapshot['unidentified'],
                        'source': snapshot['source']},
    }


def _sum_known(values):
    values = [value for value in values if value is not None]
    return sum(values) if values else None


def courses_per_facility(facilities, courses):
    """Report the ratio only when both counts are known and the denominator is valid."""
    if not facilities or courses is None:
        return None
    return courses / facilities


def requests_per_course(courses, requests):
    """Applications recorded per course; not a count of distinct participants."""
    if not courses or requests is None:
        return None
    return requests / courses


def region_chart_rows(areas):
    """Sort districts for the dashboard chart: known application counts first, descending."""
    return sorted(areas, key=lambda item: (item.get('requests') is None, -(item.get('requests') or 0)))
