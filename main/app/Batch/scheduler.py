"""Django 개발 서버가 실행 중일 때 서울 CSV 배치를 예약한다."""
import atexit
import logging
import threading

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from django.conf import settings

from .seoul_csv_batch import refresh_seoul_csvs


logger = logging.getLogger(__name__)
_scheduler = None
_scheduler_lock = threading.Lock()


def _run_seoul_batch():
    """예약 시각에 서울 CSV 배치를 실행하고 실패를 서버 로그에 남긴다."""
    try:
        refresh_seoul_csvs()
    except Exception:
        logger.exception("예약된 서울 CSV 배치 실행에 실패했습니다.")


def start_scheduler():
    """현재 프로세스에서 APScheduler를 한 번만 시작한다."""
    global _scheduler
    with _scheduler_lock:
        if _scheduler is not None and _scheduler.running:
            return _scheduler

        schedule = settings.SEOUL_BATCH_SCHEDULE
        scheduler = BackgroundScheduler(timezone=settings.TIME_ZONE)
        trigger = CronTrigger(
            day_of_week=schedule["day_of_week"],
            hour=schedule["hour"],
            minute=schedule["minute"],
            timezone=settings.TIME_ZONE,
        )
        scheduler.add_job(
            _run_seoul_batch,
            trigger=trigger,
            id="seoul_csv_batch",
            replace_existing=True,
            coalesce=True,
            max_instances=1,
            misfire_grace_time=24 * 60 * 60,
        )
        scheduler.start()
        _scheduler = scheduler
        logger.info(
            "서울 CSV 배치 예약을 시작했습니다: %s %02d:%02d",
            schedule["day_of_week"],
            schedule["hour"],
            schedule["minute"],
        )
        return scheduler


def stop_scheduler():
    """서버 종료 시 예약 스레드를 정리한다."""
    global _scheduler
    with _scheduler_lock:
        if _scheduler is not None and _scheduler.running:
            _scheduler.shutdown(wait=False)
        _scheduler = None


atexit.register(stop_scheduler)
