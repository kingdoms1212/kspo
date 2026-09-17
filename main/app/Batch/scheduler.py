"""Django 개발 서버가 실행 중일 때 지역 CSV 배치를 예약한다."""
import atexit
import logging
import threading

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from django.conf import settings

from app.common.regions import get_region_profile

from .data_refresh import refresh_region_data


logger = logging.getLogger(__name__)
_scheduler = None
_scheduler_lock = threading.Lock()


def _run_region_batch():
    """예약 시각에 설정된 지역 CSV 배치를 실행한다."""
    try:
        # 저장 방식은 공통 진입점이 설정에 따라 CSV 또는 DB로 선택한다.
        refresh_region_data(get_region_profile(settings.BATCH_REGION_KEY))
    except Exception:
        logger.exception("예약된 지역 CSV 배치 실행에 실패했습니다.")


def start_scheduler():
    """현재 프로세스에서 APScheduler를 한 번만 시작한다."""
    global _scheduler
    with _scheduler_lock:
        if _scheduler is not None and _scheduler.running:
            return _scheduler

        schedule = settings.BATCH_SCHEDULE
        scheduler = BackgroundScheduler(timezone=settings.TIME_ZONE)
        trigger = CronTrigger(
            day_of_week=schedule["day_of_week"],
            hour=schedule["hour"],
            minute=schedule["minute"],
            timezone=settings.TIME_ZONE,
        )
        scheduler.add_job(
            _run_region_batch,
            trigger=trigger,
            id="regional_data_batch",
            replace_existing=True,
            coalesce=True,
            max_instances=1,
            misfire_grace_time=24 * 60 * 60,
        )
        scheduler.start()
        _scheduler = scheduler
        logger.info(
            "지역 CSV 배치 예약을 시작했습니다: %s %02d:%02d",
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
