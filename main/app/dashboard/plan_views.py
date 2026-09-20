"""Validated plan previews and signed browser-held results; no server persistence."""
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import render
from django.templatetags.static import static
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_POST

from ..facilities.services import facility_transit
from .planning import ScopeForm, PlanForm, candidates, facility_token
from ..planning.reports import report_context, report_summary
from ..planning.snapshots import (
    SNAPSHOT_SALT, SNAPSHOT_LIMIT, InvalidSnapshot, decode_snapshot, encode_snapshot,
)


@never_cache
@require_POST
def restore(request):
    """브라우저가 보관한 결과의 서명을 확인한다. CSV 재조회나 DB 저장은 없다."""
    try:
        snapshot = decode_snapshot(request.POST.get('snapshot', ''))
    except InvalidSnapshot as error:
        return JsonResponse({'error': str(error)}, status=400)
    return JsonResponse(snapshot)


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
    created = timezone.localtime()
    result = render(request, 'dashboard/_plan_result.html',
                    report_context(form.cleaned_data, form.selected, form.statistics, created))
    if request.headers.get('Accept') != 'application/json':
        return result
    summary = report_summary(form.cleaned_data, form.selected, created)
    html = result.content.decode(result.charset)
    # HTML은 서버 템플릿에서 이스케이프된 결과만 서명한다. 복원 시에는
    # localStorage의 임의 HTML을 신뢰하지 않고 이 서명을 먼저 확인한다.
    return JsonResponse({'html': html, 'summary': summary,
                         'snapshot': encode_snapshot(html, summary)})
