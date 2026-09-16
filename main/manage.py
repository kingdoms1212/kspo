#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def refresh_seoul_data_for_runserver():
    """개발 웹 서비스의 최초 기동에서만 서울 전용 CSV를 갱신한다."""
    command = sys.argv[1] if len(sys.argv) > 1 else ''
    if command != 'runserver' or os.environ.get('RUN_MAIN') == 'true':
        return

    from app.Batch.seoul_csv_batch import refresh_seoul_csvs

    print('[서울 CSV 배치] 원본 CSV에서 서울 데이터를 갱신합니다.')
    results = refresh_seoul_csvs()
    for result in results:
        print(
            f'[서울 CSV 배치] {result.output.name}: '
            f'{result.seoul_rows:,}행 반영 완료'
        )


def start_seoul_scheduler_for_runserver():
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
    refresh_seoul_data_for_runserver()
    start_seoul_scheduler_for_runserver()
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
