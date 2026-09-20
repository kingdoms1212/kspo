"""배치 세대를 확인해 CSV 메모리 캐시를 자동으로 갱신한다."""
import json
import logging
import threading
from pathlib import Path

from django.conf import settings
from .file_digest import sha256_file


MANIFEST_FILE = 'batch_manifest.json'
logger = logging.getLogger(__name__)


class DataGenerationPending(RuntimeError):
    """CSV 교체와 manifest 발행 사이의 짧은 중간 상태를 나타낸다."""


_manifest_lock = threading.Lock()
_manifest_cache = {}
_content_lock = threading.Lock()
_content_cache = {}


def _content_matches(path, signature, expected):
    """Deployment may change mtimes; verify bytes once per local file version."""
    digest = expected.get('sha256')
    if not digest or signature[1] != expected.get('size'):
        return False
    key = str(path.resolve())
    with _content_lock:
        cached = _content_cache.get(key)
        if not cached or cached[0] != signature:
            actual = sha256_file(path)
            if _signature(path) != signature:
                return False  # A batch replaced the file while it was hashed.
            cached = signature, actual
            _content_cache[key] = cached
        return cached[1] == digest


def _signature(path):
    """파일 교체를 나노초 수정시각과 크기로 식별한다."""
    stat = Path(path).stat()
    return stat.st_mtime_ns, stat.st_size


def _manifest(data_dir):
    """작은 manifest가 바뀐 경우에만 JSON을 다시 읽는다."""
    path = Path(data_dir) / MANIFEST_FILE
    signature = _signature(path)
    key = str(path.resolve())
    cached = _manifest_cache.get(key)
    if cached and cached[0] == signature:
        return cached[1]

    with _manifest_lock:
        cached = _manifest_cache.get(key)
        if cached and cached[0] == signature:
            return cached[1]
        with path.open('r', encoding='utf-8') as source:
            manifest = json.load(source)
        if not manifest.get('generation') or not isinstance(manifest.get('files'), dict):
            raise ValueError('배치 manifest 형식이 올바르지 않습니다.')
        _manifest_cache[key] = (signature, manifest)
        return manifest


def source_version(filename):
    """현재 프로세스가 사용할 CSV 세대를 반환한다."""
    data_dir = Path(settings.DATA_DIR)
    path = data_dir / filename
    manifest_path = data_dir / MANIFEST_FILE

    # 테스트나 최초 설치처럼 manifest가 없으면 파일 자체 변경을 감지한다.
    if not manifest_path.exists():
        if not path.exists():
            return 'missing',
        return 'file', *_signature(path)

    manifest = _manifest(data_dir)
    expected = manifest['files'].get(filename)
    if not expected:
        raise DataGenerationPending(f'manifest에 파일 정보가 없습니다: {filename}')
    current = _signature(path)
    recorded = expected.get('mtime_ns'), expected.get('size')
    if current != recorded and not _content_matches(path, current, expected):
        raise DataGenerationPending(f'CSV 교체가 진행 중입니다: {filename}')
    return 'manifest', manifest['generation']


class VersionedCsvCache:
    """각 프로세스에서 한 번만 적재하고 세대 변경 시 자동 갱신한다."""

    def __init__(self, filename, loader):
        self.filename = filename
        self.loader = loader
        self._lock = threading.Lock()
        self._version = None
        self._arguments = None
        self._value = None
        self._loaded = False
        self.background_refresh = False

    def get(self, *arguments, refresh=False):
        """같은 세대는 재사용하고 새 세대만 안전하게 다시 적재한다."""
        # 웹 서버의 갱신 스레드가 관리할 때는 요청이 CSV 읽기/잠금을
        # 부담하지 않는다. 아직 적재되지 않은 경우에는 기존 동작으로 복구한다.
        if self.background_refresh and not refresh and self._loaded and self._arguments == arguments:
            return self._value
        try:
            version = source_version(self.filename)
        except DataGenerationPending:
            if self._loaded and self._arguments == arguments:
                return self._value
            raise
        except Exception:
            if self._loaded and self._arguments == arguments:
                logger.exception('CSV 세대 확인 실패로 기존 캐시를 유지합니다: %s', self.filename)
                return self._value
            raise

        if self._loaded and self._version == version and self._arguments == arguments:
            return self._value

        with self._lock:
            try:
                version = source_version(self.filename)
            except DataGenerationPending:
                if self._loaded and self._arguments == arguments:
                    return self._value
                raise
            except Exception:
                if self._loaded and self._arguments == arguments:
                    logger.exception('CSV 세대 확인 실패로 기존 캐시를 유지합니다: %s', self.filename)
                    return self._value
                raise
            if self._loaded and self._version == version and self._arguments == arguments:
                return self._value

            try:
                value = self.loader(*arguments)
                confirmed = source_version(self.filename)
                if confirmed != version:
                    raise DataGenerationPending(f'CSV 적재 중 세대가 변경되었습니다: {self.filename}')
            except DataGenerationPending:
                if self._loaded and self._arguments == arguments:
                    return self._value
                raise
            except Exception:
                if self._loaded and self._arguments == arguments:
                    logger.exception('새 CSV 적재 실패로 기존 캐시를 유지합니다: %s', self.filename)
                    return self._value
                raise

            # 완전한 적재가 끝난 뒤에만 기존 메모리를 교체한다.
            self._value = value
            self._version = version
            self._arguments = arguments
            self._loaded = True
            return value

    def refresh(self, *arguments):
        """현재 세대를 확인하고 메모리가 교체되었는지 반환한다."""
        previous = self._value
        value = self.get(*arguments, refresh=True)
        return value is not previous

    def set_background_refresh(self, enabled):
        """실행 관리자가 내부 캐시 상태에 접근하지 않고 갱신 방식을 선택한다."""
        self.background_refresh = enabled

    def clear(self):
        """테스트와 수동 점검을 위해 현재 프로세스 캐시만 비운다."""
        with self._lock:
            self._version = None
            self._arguments = None
            self._value = None
            self._loaded = False
