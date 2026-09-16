"""Dashboard aggregates and presentation data."""
from collections import Counter
from math import cos, sin, pi

from . import models


def selected_districts(value):
    values = value.split(',') if isinstance(value, str) else value
    return sorted({name.strip() for name in values if name.strip()})


def dashboard_data(region='', district=''):
    districts = selected_districts(district)
    snapshot = models.usage_snapshot()
    seoul_areas = [area for area in snapshot['areas'] if area['region'] == '서울']
    areas = [area for area in seoul_areas
             if not districts or area['district'] in districts]
    sports = Counter()
    for area in areas:
        sports.update(area['sports'])
    sport_rows = sport_totals(areas)
    region_districts = {}
    for area in seoul_areas:
        if area['region'] != '지역 미제공' and area['district'] != '시군구 미제공':
            region_districts.setdefault(area['region'], set()).add(area['district'])
    months = sorted({month for area in areas for month in (area['first_month'], area['last_month']) if month})
    return {
        'areas': areas,
        'facilities': _sum_known(area['facilities'] for area in areas),
        'courses': _sum_known(area['courses'] for area in areas),
        'requests': _sum_known(area['requests'] for area in areas),
        'sports': sports.most_common(),
        'sport_rows': sport_rows,
        'region_district_options': {name: sorted(names) for name, names in region_districts.items()},
        'sport_count': sum(row['name'] != '종목 미제공' for row in sport_rows),
        'region_options': ['서울'],
        'period': [f'{months[0]} ~ {months[-1]}'] if months else ['기준일 미확인'],
        # 대시보드 전용 신청인원 집계를 공통 지도의 입력 형식으로 전달한다.
        'region_distribution': region_distribution(seoul_areas),
        'district_distribution': district_distribution(seoul_areas),
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


def district_distribution(areas):
    """대시보드 신청인원을 지역별 시군구 분포로 집계한다.

    공통 지도 모듈이 사용하는 ``{지역: [(시군구, 신청인원), ...]}``
    구조를 반환한다. 프로그램 집계와 독립적으로 대시보드의 신청인원
    계산 기준만 이 함수에서 관리한다.
    """
    totals = {}
    for area in areas:
        if (area['region'] == '지역 미제공' or area['district'] == '시군구 미제공'
                or area['requests'] is None):
            continue
        totals.setdefault(area['region'], Counter())[area['district']] += area['requests']
    return {
        region: counts.most_common()
        for region, counts in sorted(totals.items())
    }


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
    rows = list(rows)
    canonical = sorted(rows, key=lambda row: (-(row.get('requests') or 0), row.get('name', ''), row.get('region', ''), row.get('district', '')))
    total = sum(max(row.get('requests') or 0, 0) for row in rows)
    palette = ('--si-map-5', '--si-map-3', '--si-chart-primary', '--si-map-2', '--si-navy')
    segments, legend = [], []
    cumulative = 0
    for index, row in enumerate(canonical):
        value = max(row.get('requests') or 0, 0)
        start = cumulative / total * 100 if total else 0
        cumulative += value
        end = cumulative / total * 100 if total else 0
        color = palette[index % len(palette)]
        if value and total:
            segments.append(f'var({color}) {start:.8f}% {end:.8f}%')
        start_angle, end_angle = start / 100 * 2 * pi - pi / 2, end / 100 * 2 * pi - pi / 2
        path = (f'M 100 100 L {100 + 95 * cos(start_angle):.6f} {100 + 95 * sin(start_angle):.6f} '
                f'A 95 95 0 {int(end - start > 50)} 1 '
                f'{100 + 95 * cos(end_angle):.6f} {100 + 95 * sin(end_angle):.6f} Z')
        legend.append({**row, 'number': index + 1, 'color': color, 'path': path,
                       'share': value / total * 100 if total else 0})
    by_identity = {id(row): item for row, item in zip(canonical, legend)}
    return {'rows': [by_identity[id(row)] for row in rows], 'total': total,
            'gradient': 'conic-gradient(' + ', '.join(segments) + ')' if segments else 'none'}


def requests_per_sport(sport_count, requests):
    """Recorded applications divided by the number of named sports."""
    if sport_count is None or sport_count <= 0 or requests is None:
        return None
    return requests / sport_count
