#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def refresh_region_data_for_runserver():
    """개발 웹 서비스의 최초 기동에서만 설정 지역 데이터를 갱신한다."""
    command = sys.argv[1] if len(sys.argv) > 1 else ''
    if command != 'runserver' or os.environ.get('RUN_MAIN') == 'true':
        return

    # DB 저장기가 ORM을 사용해도 앱 등록 전 오류가 나지 않도록 먼저 초기화한다.
    import django

    django.setup()

    from django.conf import settings

    from app.Batch.data_refresh import get_storage_mode, refresh_region_data
    from app.common.regions import get_region_profile

    profile = get_region_profile(settings.BATCH_REGION_KEY)
    mode = get_storage_mode()
    print(f'[지역 데이터 배치] {profile.display_name} 데이터를 {mode} 방식으로 갱신합니다.')
    results = refresh_region_data(profile)
    # CSV 저장기는 파일별 결과를 반환하며 DB 저장기는 자체 결과 형식을 사용할 수 있다.
    for result in results or ():
        if hasattr(result, 'output') and hasattr(result, 'matched_rows'):
            print(
                f'[지역 데이터 배치] {result.output.name}: '
                f'{result.matched_rows:,}행 반영 완료'
            )


def start_region_scheduler_for_runserver():
    """자동 재로더의 실제 서버 프로세스에서만 예약을 시작한다."""
    command = sys.argv[1] if len(sys.argv) > 1 else ''
    is_server_process = (
        os.environ.get('RUN_MAIN') == 'true' or '--noreload' in sys.argv
    )
    if command != 'runserver' or not is_server_process:
        return

    from app.Batch.scheduler import start_scheduler

    start_scheduler()


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'main.settings')
    refresh_region_data_for_runserver()
    start_region_scheduler_for_runserver()
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
