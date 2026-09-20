"""실제 웹 프로세스에서 목록을 사전 적재하고 외부 배치 발행도 감지한다."""
import atexit
import logging
import threading
from time import perf_counter

from django.conf import settings

from .data import data_path
from .versioned_csv import DataGenerationPending

logger = logging.getLogger(__name__)
_lock = threading.Lock()
_stop = threading.Event()
_thread = None


def _caches():
    from app.programs.models import _snapshot_cache as programs
    from app.facilities.models import _snapshot_cache as facilities
    from app.dashboard.models import _usage_cache as usage
    # 큰 교통 상세 색인은 목록 조회에 필요하지 않아 기존 지연 적재를 유지한다.
    return programs, facilities, usage


def warm_csv_caches():
    """변경된 파일만 순차 적재한다. 한 파일 실패가 나머지 갱신을 막지 않는다."""
    for cache in _caches():
        try:
            if not data_path(cache.filename).exists():
                # 서비스 기동 후 CSV가 생성되는 경우 다음 주기에 재시도한다.
                continue
            started = perf_counter()
            previous = cache._value
            value = cache.get(refresh=True)
            if value is not previous:
                logger.info('CSV 메모리 적재 완료: %s (%.3f초)',
                            cache.filename, perf_counter() - started)
        except DataGenerationPending:
            # 파일 교체와 manifest 발행 사이에는 완성된 세대를 기다린다.
            continue
        except Exception:
            logger.exception('CSV 사전 적재 실패, 다음 주기에 재시도합니다: %s', cache.filename)


def _watch(interval):
    try:
        while not _stop.wait(interval):
            warm_csv_caches()
    finally:
        # 예기치 않게 감시가 끝나도 기존 요청 시 갱신 경로로 복구한다.
        for cache in _caches():
            cache.background_refresh = False


def start_csv_warmup():
    """WSGI/ASGI 초기화 후 실행. 배치/관리 명령 프로세스에서는 실행하지 않는다."""
    global _thread
    if not getattr(settings, 'CSV_WARMUP_ENABLED', True):
        return
    with _lock:
        if _thread is not None and _thread.is_alive():
            return
        interval = max(1.0, float(settings.CSV_REFRESH_INTERVAL_SECONDS))
        _stop.clear()
        warm_csv_caches()
        for cache in _caches():
            cache.background_refresh = True
        _thread = threading.Thread(target=_watch, args=(interval,),
                                   name='csv-cache-refresh', daemon=True)
        try:
            _thread.start()
        except Exception:
            for cache in _caches():
                cache.background_refresh = False
            logger.exception('CSV 갱신 스레드 시작 실패, 요청 시 갱신 방식을 사용합니다.')


def stop_csv_warmup():
    """종료 신호를 보내고 동기 조회 경로로 되돌린다."""
    with _lock:
        _stop.set()
        if _thread is not None:
            for cache in _caches():
                cache.background_refresh = False


atexit.register(stop_csv_warmup)
