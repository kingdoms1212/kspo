"""Dashboard aggregates and presentation data."""
from collections import Counter

from . import models
# Keep the existing service imports compatible while presentation has one owner.
from .presenters import chart_sort, normalized_chart_rows, region_chart_rows, pie_chart_data


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


def requests_per_sport(sport_count, requests):
    """Recorded applications divided by the number of named sports."""
    if sport_count is None or sport_count <= 0 or requests is None:
        return None
    return requests / sport_count
