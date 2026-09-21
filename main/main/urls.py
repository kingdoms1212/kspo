"""
URL configuration for main project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView
from django.http import JsonResponse
from django.views.decorators.cache import never_cache

from app.runtime import readiness


@never_cache
def healthz(request):
    """[SG002] - CSV파일 초기화 예외처리 화면 제공

    자료가 준비되기 전에는 실패로 답한다.

    Render는 이 경로로 새 인스턴스의 투입 시점을 정한다. 준비 전에 200을
    돌려주면 목록이 아직 없는 인스턴스로 트래픽이 넘어가고, 배포할 때마다
    모든 사용자가 초기화 화면을 보게 된다. 예전에는 적재가 끝나야 워커가
    응답을 시작해 이 보호가 자연히 걸렸는데, 적재를 스레드로 옮기면서
    보호가 사라지므로 여기서 명시한다.
    """
    state = readiness.state()
    healthy = state not in (readiness.LOADING, readiness.MISSING)
    return JsonResponse({'status': 'ok' if healthy else state},
                        status=200 if healthy else 503)


@never_cache
def readyz(request):
    """[SG002] 준비 상태의 세부 내역. 안내 화면의 자동 재시도가 이 경로를 확인한다."""
    detail = readiness.report()
    healthy = detail['state'] not in (readiness.LOADING, readiness.MISSING)
    return JsonResponse(detail, status=200 if healthy else 503)


urlpatterns = [
    path('healthz/', healthz, name='healthz'),
    path('readyz/', readyz, name='readyz'),
    path('admin/', admin.site.urls),
    path('', RedirectView.as_view(pattern_name='dashboard', permanent=False), name='home'),
    path('', include('app.urls')),
]
