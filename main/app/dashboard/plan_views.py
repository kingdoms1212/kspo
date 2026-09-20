"""Validated plan previews and signed browser-held results; no server persistence."""
from django.core.paginator import Paginator
from django.core import signing
from django.http import JsonResponse
from django.shortcuts import render
from django.templatetags.static import static
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_POST

from ..facilities.services import facility_transit
from .planning import ScopeForm, PlanForm, candidates, facility_token
from .services import pie_chart_data, region_chart_rows

SNAPSHOT_SALT = 'program-plan-result-v1'
SNAPSHOT_LIMIT = 1_000_000


@never_cache
@require_POST
def restore(request):
    """브라우저가 보관한 결과의 서명을 확인한다. CSV 재조회나 DB 저장은 없다."""
    token = request.POST.get('snapshot', '')
    if not token or len(token) > SNAPSHOT_LIMIT:
        return JsonResponse({'error': '저장된 계획서를 읽을 수 없습니다.'}, status=400)
    try:
        snapshot = signing.loads(token, salt=SNAPSHOT_SALT)
        if (not isinstance(snapshot, dict) or snapshot.get('version') != 1
                or not isinstance(snapshot.get('html'), str)
                or not isinstance(snapshot.get('summary'), dict)):
            raise ValueError('Invalid snapshot')
    except (signing.BadSignature, ValueError, TypeError):
        return JsonResponse({'error': '저장된 계획서가 손상되었거나 서버 설정이 변경되어 열 수 없습니다.'}, status=400)
    return JsonResponse({'html': snapshot['html'], 'summary': snapshot['summary']})


@never_cache
@require_GET
def facility_list(request):
    form = ScopeForm(request.GET)
    if not form.is_valid():
        return JsonResponse({'errors': form.errors}, status=400)
    rows = candidates(**form.cleaned_data)
    eligible_count = len(rows)
    query = request.GET.get('q', '').strip()[:100].casefold()
    if query:
        rows = [row for row in rows if query in row.name.casefold() or query in row.address.casefold()]
    page = Paginator(rows, 20).get_page(request.GET.get('page', 1))
    return JsonResponse({'count': len(rows), 'eligible_count': eligible_count, 'page': page.number,
                         'pages': page.paginator.num_pages,
                         'rows': [{'id': row.id, 'token': facility_token(row),
                                   'name': row.name, 'address': row.address,
                                   'type': row.facility_type, 'state': row.state,
                                   'photo': static('image/center/center' + row.id[-1] + '.jpg')} for row in page]})


@never_cache
@require_GET
def facility_detail(request):
    form = ScopeForm(request.GET)
    if not form.is_valid():
        return JsonResponse({'errors': form.errors}, status=400)
    row = next((row for row in candidates(**form.cleaned_data)
                if row.id == request.GET.get('id')), None)
    if row is None:
        return JsonResponse({'error': '현재 조건에서 시설을 찾을 수 없습니다.'}, status=404)
    return render(request, 'dashboard/_plan_detail.html',
                  {'selected': row, 'transit': facility_transit(row)})


@never_cache
@require_POST
def preview(request):
    form = PlanForm(request.POST)
    if not form.is_valid():
        return JsonResponse({'errors': form.errors}, status=400)
    # The plan states the chosen sport's own application count beside the area
    # total. A sport absent from the usage ledger stays absent; it is reported
    # as such rather than shown as zero.
    sport_requests = dict(form.statistics['sports']).get(form.cleaned_data['sport'])
    sport_rows = form.statistics.get('sport_rows')
    if sport_rows is None:
        sport_rows = [dict(name=name, requests=count, facilities=None)
                      for name, count in form.statistics['sports']]
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
    # Three newspaper-style columns, twelve rows each; never omit extra sports.
    sport_pages = []
    for start in range(0, max(len(all_sports), 1), 36):
        batch = all_sports[start:start + 36]
        height = max(1, (len(batch) + 2) // 3)
        sport_pages.append([[batch[i + col * height] if i + col * height < len(batch) else None
                             for col in range(3)] for i in range(height)])
    created = timezone.localtime()
    result = render(request, 'dashboard/_plan_result.html', {
        'plan': form.cleaned_data, 'selected': form.selected,
        'statistics': form.statistics,
        'report_pie': report_pie, 'sport_pages': sport_pages,
        'report_sport_count': form.statistics.get('sport_count', len(sport_rows)),
        'region_pie': pie_chart_data(region_chart_rows(form.statistics.get('areas', []))),
        'total_capacity': form.cleaned_data['capacity'] * len(form.selected),
        'sport_requests': sport_requests,
        'created': created,
    })
    if request.headers.get('Accept') != 'application/json':
        return result
    plan = form.cleaned_data
    summary = {key: plan[key] for key in ('name', 'region', 'district', 'sport', 'capacity', 'fee')}
    summary.update(unit=plan['fee_unit'], facilities=[row.name for row in form.selected],
                   created=created.isoformat())
    html = result.content.decode(result.charset)
    # HTML은 서버 템플릿에서 이스케이프된 결과만 서명한다. 복원 시에는
    # localStorage의 임의 HTML을 신뢰하지 않고 이 서명을 먼저 확인한다.
    token = signing.dumps({'version': 1, 'html': html, 'summary': summary},
                          salt=SNAPSHOT_SALT, compress=True)
    return JsonResponse({'html': html, 'summary': summary,
                         'snapshot': token if len(token) <= SNAPSHOT_LIMIT else None})
