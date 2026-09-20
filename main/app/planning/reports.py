"""검증된 설계 입력과 통계를 보고서 표시 데이터로 구성한다."""
from ..dashboard.presenters import pie_chart_data, region_chart_rows


def report_context(plan, selected, statistics, created):
    """CSV를 재조회하지 않고 전달받은 동일 통계로 표·차트·모집인원을 구성한다."""
    sport_requests = dict(statistics['sports']).get(plan['sport'])
    sport_rows = statistics.get('sport_rows')
    if sport_rows is None:
        sport_rows = [dict(name=name, requests=count, facilities=None)
                      for name, count in statistics['sports']]
    sport_rows = sorted(sport_rows, key=lambda row: (row.get('requests') is None,
                        -(row.get('requests') or 0), row['name']))
    all_sports = pie_chart_data(sport_rows)['rows']
    chart_rows = sport_rows[:5]
    if len(sport_rows) > 5:
        chart_rows = chart_rows + [dict(name='기타', requests=sum(row.get('requests') or 0 for row in sport_rows[5:]))]
    report_pie = pie_chart_data(chart_rows)
    for item, original in zip(report_pie['rows'][:5], all_sports[:5]):
        item['color'] = original['color']
    if len(sport_rows) > 5:
        report_pie['rows'][-1]['color'] = '--si-text-muted'
    # 한 페이지에 3열 × 12행을 배치하고 남은 종목은 다음 페이지에 표시한다.
    sport_pages = []
    for start in range(0, max(len(all_sports), 1), 36):
        batch = all_sports[start:start + 36]
        height = max(1, (len(batch) + 2) // 3)
        sport_pages.append([[batch[i + col * height] if i + col * height < len(batch) else None
                             for col in range(3)] for i in range(height)])
    return {
        'plan': plan, 'selected': selected, 'statistics': statistics,
        'report_pie': report_pie, 'sport_pages': sport_pages,
        'report_sport_count': statistics.get('sport_count', len(sport_rows)),
        'region_pie': pie_chart_data(region_chart_rows(statistics.get('areas', []))),
        'total_capacity': plan['capacity'] * len(selected),
        'sport_requests': sport_requests, 'created': created,
    }


def report_summary(plan, selected, created):
    """최근 목록과 공유 메시지에서 사용하는 요약 규약을 유지한다."""
    summary = {key: plan[key] for key in ('name', 'region', 'district', 'sport', 'capacity', 'fee')}
    summary.update(unit=plan['fee_unit'], facilities=[row.name for row in selected],
                   created=created.isoformat())
    return summary
