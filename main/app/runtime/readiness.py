"""[SG002] - CSV파일 초기화 예외처리 화면 제공

목록 자료의 준비 상태를 판정한다. 화면·상태 점검·게이트가 같은 답을 쓴다.

판정은 "최초 적재가 끝났는가"만 본다. 배치가 새 세대를 발행해 다시 읽는 중에도
캐시는 옛 목록을 그대로 서비스하므로, 갱신 중을 미준비로 보면 멀쩡한 자료를
두고 화면을 막게 된다. 자세한 이유는 `VersionedCsvCache.is_loaded` 참고.
"""
from django.conf import settings

from ..common.data import data_path
from .csv_warmup import warmup_active, warmup_elapsed, warmup_enabled
from .targets import csv_warmup_targets

# 이 프로세스가 사전 적재를 맡지 않는다. 요청이 직접 읽으므로 막지 않는다.
DISABLED = 'disabled'
# 필요한 목록이 모두 메모리에 있다.
READY = 'ready'
# 적재가 진행 중이다. 잠시 뒤 다시 시도하면 된다.
LOADING = 'loading'
# 원본 CSV 자체가 없다. 기다려도 해결되지 않고 배치를 돌려야 한다.
MISSING = 'missing'
# 감시 스레드가 없거나 너무 오래 걸린다. 막지 말고 요청이 직접 읽게 한다.
STALLED = 'stalled'

DEFAULT_TIMEOUT_SECONDS = 120.0


def _timeout():
    return float(getattr(settings, 'CSV_READY_TIMEOUT_SECONDS', DEFAULT_TIMEOUT_SECONDS))


def _selected(keys):
    targets = csv_warmup_targets()
    if keys is None:
        return targets
    wanted = set(keys)
    return tuple(target for target in targets if target.key in wanted)


def state(keys=None):
    """[SG002] - CSV파일 초기화 예외처리 화면 제공

    `keys`가 가리키는 목록의 준비 상태. None이면 전체를 본다.

    `keys`에 등록되지 않은 이름이 있으면 그 목록은 판정에서 빠진다. 교통 상세
    색인처럼 사전 적재 대상이 아닌 자료를 실수로 넣어도 화면이 막히지 않는다.
    """
    # [SG002] - CSV파일 초기화 예외처리 화면 제공
    # 판정 순서가 곧 안내 문구를 가른다. 앞의 조건이 뒤를 가리지 않게 둔다.
    if not warmup_enabled():
        return DISABLED
    pending = [target for target in _selected(keys) if not target.is_ready()]
    if not pending:
        return READY
    elapsed = warmup_elapsed()
    if elapsed is None and not warmup_active():
        # 이 프로세스는 사전 적재를 시작한 적이 없다. 관리 명령과 테스트가
        # 여기 해당한다. 막으면 아무도 읽지 않으므로 요청이 직접 읽게 둔다.
        return STALLED
    # 적재된 목록은 파일이 사라져도 계속 서비스한다. 아직 못 읽은 것만 따진다.
    if any(not data_path(target.filename).exists() for target in pending):
        return MISSING
    if not warmup_active():
        return STALLED
    if elapsed is not None and elapsed > _timeout():
        return STALLED
    return LOADING


def is_ready(keys=None):
    """[SG002] 게이트를 통과시켜도 되는 상태인지. 미준비 중 막는 것은 둘뿐이다."""
    return state(keys) not in (LOADING, MISSING)


def report():
    """[SG002] 상태 점검 응답과 배치 화면이 함께 쓰는 세부 내역."""
    targets = csv_warmup_targets()
    return {
        'state': state(),
        'warmup': {
            'enabled': warmup_enabled(),
            'active': warmup_active(),
            'elapsed_seconds': warmup_elapsed(),
            'timeout_seconds': _timeout(),
        },
        'targets': [
            {
                'key': target.key,
                'label': target.label,
                'filename': target.filename,
                'loaded': target.is_ready(),
                'present': data_path(target.filename).exists(),
            }
            for target in targets
        ],
    }
