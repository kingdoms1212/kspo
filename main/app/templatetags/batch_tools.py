"""데이터 최신화 관리 버튼과 모달을 선택적으로 출력한다."""
from django import template
from django.conf import settings
from django.middleware.csrf import get_token


register = template.Library()


@register.inclusion_tag("batch/test_control.html", takes_context=True)
def show_batch_test_button(context):
    """이 태그를 호출한 화면에 데이터 최신화 버튼과 모달을 표시한다."""
    request = context.get("request")
    # 응답 본문은 매번 같게 유지하고 CSRF 값은 쿠키로만 전달한다.
    if request is not None:
        get_token(request)
    mode = str(getattr(settings, "BATCH_STORAGE_MODE", "csv")).strip().lower()
    return {
        "batch_storage_mode": mode,
        "batch_storage_label": "DB" if mode == "db" else "CSV",
    }
