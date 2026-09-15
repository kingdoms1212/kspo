"""Dashboard aggregates and presentation data."""
from collections import Counter

from . import models


def dashboard_data(region=''):
    snapshot = models.usage_snapshot()
    areas = [area for area in snapshot['areas'] if not region or area['region'] == region]
    sports = Counter()
    for area in areas:
        sports.update(area['sports'])
    sport_rows = sport_totals(areas)
    months = sorted({month for area in areas for month in (area['first_month'], area['last_month']) if month})
    return {
        'areas': areas,
        'facilities': _sum_known(area['facilities'] for area in areas),
        'courses': _sum_known(area['courses'] for area in areas),
        'requests': _sum_known(area['requests'] for area in areas),
        'sports': sports.most_common(),
        'sport_rows': sport_rows,
        'sport_count': sum(row['name'] != '종목 미제공' for row in sport_rows),
        'region_options': sorted({area['region'] for area in snapshot['areas']
                                  if area['region'] != '지역 미제공'}),
        'period': [f'{months[0]} ~ {months[-1]}'] if months else ['기준일 미확인'],
        # The map reads applications by province, and by Seoul district when it
        # drills down. Districts are disjoint, so a province total is their sum.
        'region_distribution': region_distribution(snapshot['areas']),
        'seoul_district_distribution': seoul_district_distribution(snapshot['areas']),
        'load_report': {'ledger_rows': snapshot['ledger_rows'],
                        'unidentified': snapshot['unidentified'],
                        'source': snapshot['source']},
    }


def region_distribution(areas):
    """Applications per province, most first, skipping areas with no count."""
    totals = Counter()
    for area in areas:
        if area['requests'] is not None and area['region'] != '지역 미제공':
            totals[area['region']] += area['requests']
    return totals.most_common()


def seoul_district_distribution(areas):
    """Applications per Seoul district, for the map's drill-down level."""
    seoul_names = {'서울', '서울특별시'}
    return Counter({
        area['district']: area['requests']
        for area in areas
        if area['region'] in seoul_names and area['requests'] is not None
        and area['district'] != '시군구 미제공'
    }).most_common()


def _sum_known(values):
    values = [value for value in values if value is not None]
    return sum(values) if values else None


def courses_per_facility(facilities, courses):
    """Report the ratio only when both counts are known and the denominator is valid."""
    if facilities is None or facilities <= 0 or courses is None:
        return None
    return courses / facilities


def requests_per_course(courses, requests):
    """Applications recorded per course; not a count of distinct participants."""
    if courses is None or courses <= 0 or requests is None:
        return None
    return requests / courses


def requests_per_facility(facilities, requests):
    """Recorded applications per facility, not distinct people per facility."""
    if facilities is None or facilities <= 0 or requests is None:
        return None
    return requests / facilities


def sport_totals(areas):
    """Aggregate all sports over the selected districts, retaining missing data.

    District identities are disjoint, as in the dashboard facility totals.
    A facility offering several sports counts once in each of those sports;
    summing these rows is therefore not a distinct facility total.
    """
    grouped = {}
    for area in areas:
        for sport in area.get('sport_details', []):
            grouped.setdefault(sport['name'], []).append(sport)
    return [
        {'name': name, **{
            field: _sum_known(row[field] for row in rows)
            for field in ('facilities', 'courses', 'requests')
        }}
        for name, rows in sorted(grouped.items())
    ]


def chart_sort(value):
    return value if value in ('asc', 'desc') else 'desc'


def normalized_chart_rows(rows, order='desc'):
    """Copy and sort all rows; express counts on the current min/max interval.

    Missing values sort last in either direction and have no bar. A constant
    positive series uses full bars; an all-zero series uses zero-width marks.
    Normalization uses every row, independently of sort and viewport position.
    """
    rows = list(rows)
    values = [row['requests'] for row in rows if row.get('requests') is not None]
    minimum, maximum = (min(values), max(values)) if values else (None, None)
    result = []
    for row in rows:
        value = row.get('requests')
        if value is None:
            width = None
        elif minimum == maximum:
            width = 100.0 if value > 0 else 0.0
        else:
            width = round((value - minimum) / (maximum - minimum) * 100, 6)
        result.append({**row, 'bar_percent': width})
    direction = 1 if chart_sort(order) == 'asc' else -1
    return sorted(result, key=lambda row: (
        row.get('requests') is None,
        direction * (row.get('requests') or 0),
        row.get('name', ''), row.get('region', ''), row.get('district', ''),
    ))


def region_chart_rows(areas, order='desc'):
    return normalized_chart_rows(areas, order)


def pie_chart_data(rows):
    """Pie angles use actual positive counts, independently of bar normalization."""
    total = sum(max(row.get('requests') or 0, 0) for row in rows)
    palette = ('--si-map-5', '--si-map-3', '--si-chart-primary', '--si-map-2', '--si-navy')
    segments, legend = [], []
    cumulative = 0
    for index, row in enumerate(rows):
        value = max(row.get('requests') or 0, 0)
        start = cumulative / total * 100 if total else 0
        cumulative += value
        end = cumulative / total * 100 if total else 0
        color = palette[index % len(palette)]
        if value and total:
            segments.append(f'var({color}) {start:.8f}% {end:.8f}%')
        legend.append({**row, 'number': index + 1, 'color': color,
                       'share': value / total * 100 if total else 0})
    return {'rows': legend, 'total': total,
            'gradient': 'conic-gradient(' + ', '.join(segments) + ')' if segments else 'none'}
