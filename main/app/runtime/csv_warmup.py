"""실제 웹 프로세스에서 목록을 사전 적재하고 외부 배치 발행도 감지한다.

[SG002] - CSV파일 초기화 예외처리 화면 제공
첫 적재도 감시 스레드가 맡는다. 예전에는 `start_csv_warmup()`이 동기로 한 번
읽고 나서 스레드를 띄웠는데, 이 호출은 `main.wsgi` 임포트 시점에 일어난다.
gunicorn은 WSGI 모듈을 다 읽은 뒤에야 요청 처리를 시작하므로, 그동안 들어온
접속은 응답도 안내도 없이 대기했다. 적재를 스레드로 옮기면 워커가 곧바로
요청을 받고, 자료가 필요 없는 화면(정책·배치 관리·상태 점검)은 즉시 열린다.

적재가 끝나기 전에 목록 화면이 요청되면 `VersionedCsvCache.get()`이 기존처럼
그 요청 안에서 읽는다. 감시 스레드가 이미 읽고 있으면 같은 잠금에서 기다렸다가
완료 즉시 응답하므로, 중복 적재도 무응답도 생기지 않는다.
"""
import atexit
import logging
import threading
from time import monotonic, perf_counter

from django.conf import settings

from ..common.data import data_path
from ..common.versioned_csv import DataGenerationPending
from .targets import csv_warmup_targets

logger = logging.getLogger('app.common.csv_warmup')
_lock = threading.Lock()
_stop = threading.Event()
_thread = None
_started_at = None


def warm_csv_caches():
    """변경된 파일만 순차 적재한다. 한 파일 실패가 나머지 갱신을 막지 않는다."""
    for cache in csv_warmup_targets():
        try:
            if not data_path(cache.filename).exists():
                # 서비스 기동 후 CSV가 생성되는 경우 다음 주기에 재시도한다.
                continue
            started = perf_counter()
            if cache.refresh():
                logger.info('CSV 메모리 적재 완료: %s (%.3f초)',
                            cache.filename, perf_counter() - started)
        except DataGenerationPending:
            # 파일 교체와 manifest 발행 사이에는 완성된 세대를 기다린다.
            continue
        except Exception:
            logger.exception('CSV 사전 적재 실패, 다음 주기에 재시도합니다: %s', cache.filename)


def _watch(interval):
    try:
        # [SG002] 첫 적재는 기다리지 않고 바로 시작한다. 이 호출이 끝나기 전에도
        # 워커는 이미 요청을 받고 있으므로 안내 화면을 돌려줄 수 있다.
        warm_csv_caches()
        while not _stop.wait(interval):
            warm_csv_caches()
    finally:
        # 예기치 않게 감시가 끝나도 기존 요청 시 갱신 경로로 복구한다.
        for cache in csv_warmup_targets():
            cache.set_background_refresh(False)


def start_csv_warmup():
    """WSGI/ASGI 초기화 후 실행. 배치/관리 명령 프로세스에서는 실행하지 않는다."""
    global _thread, _started_at
    if not warmup_enabled():
        return
    with _lock:
        if _thread is not None and _thread.is_alive():
            return
        interval = max(1.0, float(settings.CSV_REFRESH_INTERVAL_SECONDS))
        _stop.clear()
        for cache in csv_warmup_targets():
            cache.set_background_refresh(True)
        _started_at = monotonic()
        _thread = threading.Thread(target=_watch, args=(interval,),
                                   name='csv-cache-refresh', daemon=True)
        try:
            _thread.start()
        except Exception:
            _thread = None
            _started_at = None
            for cache in csv_warmup_targets():
                cache.set_background_refresh(False)
            logger.exception('CSV 갱신 스레드 시작 실패, 요청 시 갱신 방식을 사용합니다.')


def stop_csv_warmup():
    """종료 신호를 보내고 동기 조회 경로로 되돌린다."""
    global _started_at
    with _lock:
        _stop.set()
        _started_at = None
        if _thread is not None:
            for cache in csv_warmup_targets():
                cache.set_background_refresh(False)


def warmup_enabled():
    """[SG002] 이 프로세스가 사전 적재를 맡는지. 테스트와 관리 명령에서는 끈다."""
    return bool(getattr(settings, 'CSV_WARMUP_ENABLED', True))


def warmup_active():
    """[SG002] 감시 스레드가 살아 있고 종료 신호를 받지 않았는지."""
    return _thread is not None and _thread.is_alive() and not _stop.is_set()


def warmup_elapsed():
    """[SG002] 첫 적재를 시작한 뒤 흐른 초. 시작하지 않았으면 None."""
    return None if _started_at is None else monotonic() - _started_at


atexit.register(stop_csv_warmup)
