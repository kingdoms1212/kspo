"""프로젝트 개요 컨트롤러.

저장소·집계를 호출하지 않는다. 이 화면은 시스템이 무엇을 하는지 설명하는 문서이므로,
자료가 아직 없거나 배치가 실패한 상황에서도 읽을 수 있어야 한다. 그래서 준비 상태
게이트의 대기 목록에도 올리지 않는다(runtime/middleware.py 의 제외 경로).
"""
from django.shortcuts import render

# 문서가 무엇을 기준으로 쓰였는지 화면이 스스로 말한다. 본문 수치를 손볼 때 함께 바꾼다.
CHECKED_ON = '2026-09-21'


def overview(request):
    return render(request, 'overview/index.html',
                  {'page': 'overview', 'checked_on': CHECKED_ON})
