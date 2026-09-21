"""운영 데이터 최신화 모달에서 사용하는 화면과 실행 요청을 제공한다."""
from __future__ import annotations

import json
import re
from collections import deque
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_POST

from ..runtime import readiness
from .manual_runner import (
    BatchAlreadyRunning,
    batch_is_running,
    read_manual_batch_status,
    start_manual_batch,
)
from .regional_csv_batch import LOG_FILE, MANIFEST_FILE


STATUS_LABELS = {
    "idle": "실행 내역 없음",
    "queued": "실행 대기",
    "running": "실행 중",
    "success": "성공",
    "failed": "실패",
}


def _display_datetime(value) -> str:
    """기존 ISO 형식을 포함한 날짜 값을 화면용 초 단위 형식으로 바꾼다."""
    if not value:
        return "-"
    text = str(value)
    try:
        return datetime.fromisoformat(text).strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        return text[:19].replace("T", " ")


def _read_manifest_summary(output_dir: Path) -> dict:
    """Manifest 원문을 화면의 변경 사항 표에 맞는 구조로 정리한다."""
    try:
        with (output_dir / MANIFEST_FILE).open("r", encoding="utf-8") as source:
            manifest = json.load(source)
        if not isinstance(manifest, dict):
            raise ValueError("Manifest 형식이 올바르지 않습니다.")

        labels = {
            "programs": "프로그램 현황",
            "usage": "프로그램 설계 이용현황",
            "facilities": "시설 현황",
            "transit": "시설 인접 대중교통",
        }
        file_labels = {
            str(filename): labels.get(key, key)
            for key, filename in getattr(settings, "DATA_FILES", {}).items()
        }
        files = []
        for filename, details in manifest.get("files", {}).items():
            details = details if isinstance(details, dict) else {}
            quality = details.get("source_quality", {})
            quality = quality if isinstance(quality, dict) else {}
            files.append({
                "label": file_labels.get(filename, filename),
                "filename": filename,
                "source_rows": details.get("source_rows", 0),
                "rows": details.get("rows", 0),
                "skipped_rows": quality.get("skipped_rows", 0),
                # 이전 Manifest의 시군구 전용 필드명도 계속 읽을 수 있게 한다.
                "missing_region_codes": quality.get(
                    "missing_region_codes",
                    quality.get("missing_district_codes", 0),
                ),
                "invalid_region_codes": quality.get(
                    "invalid_region_codes",
                    quality.get("invalid_district_codes", 0),
                ),
                "region_code_mismatches": quality.get(
                    "region_code_mismatches",
                    quality.get("district_prefix_mismatches", 0),
                ),
            })
        region = manifest.get("region", {})
        region = region if isinstance(region, dict) else {}
        return {
            "available": True,
            "message": "",
            "generation": manifest.get("generation", "-"),
            "created_at": _display_datetime(manifest.get("created_at")),
            "region": region.get("display_name", "-"),
            "files": files,
        }
    except FileNotFoundError:
        return {
            "available": False,
            "message": "아직 생성된 변경 사항 내역이 없습니다.",
            "files": [],
        }
    except (OSError, json.JSONDecodeError, ValueError) as error:
        return {
            "available": False,
            "message": f"변경 사항 내역을 읽을 수 없습니다: {error}",
            "files": [],
        }


def _read_log_tail(output_dir: Path, limit: int = 120) -> str:
    try:
        with (output_dir / "logs" / LOG_FILE).open("r", encoding="utf-8") as source:
            lines = deque(source, maxlen=limit)
        log_text = "".join(lines).rstrip()
        log_text = re.sub(
            r"^(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2}:\d{2})(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?\s",
            r"\1 \2 ",
            log_text,
            flags=re.MULTILINE,
        )
        return log_text or "아직 기록된 로그가 없습니다."
    except FileNotFoundError:
        return "아직 기록된 로그가 없습니다."
    except OSError as error:
        return f"로그를 읽을 수 없습니다: {error}"


def _status_context(notice: str = "") -> dict:
    status = dict(read_manual_batch_status())
    for key in ("requested_at", "started_at", "finished_at"):
        status[key] = _display_datetime(status.get(key))
    current = status.get("status", "idle")
    try:
        progress_percent = max(0, min(100, int(status.get("progress_percent", 0))))
    except (TypeError, ValueError):
        progress_percent = 0
    status["progress_percent"] = progress_percent
    output_dir = Path(settings.DATA_DIR)
    return {
        "batch_status": status,
        "batch_status_label": STATUS_LABELS.get(current, current),
        "batch_running": current in {"queued", "running"},
        "batch_notice": notice,
        "manifest_summary": _read_manifest_summary(output_dir),
        "log_text": _read_log_tail(output_dir),
        # 적재가 안 될 때 원인을 보는 곳이므로 이 화면은 게이트에서 제외한다.
        "readiness": readiness.report(),
    }


@never_cache
@require_GET
def batch_test_status(request: HttpRequest) -> HttpResponse:
    """현재 수동 최신화 상태와 운영 Manifest, 최근 로그를 보여준다."""
    return render(request, "batch/_test_status.html", _status_context())


@never_cache
@require_POST
def batch_test_run(request: HttpRequest) -> HttpResponse:
    """일요일 예약 배치와 같은 운영 데이터 최신화를 즉시 시작한다."""
    try:
        start_manual_batch()
    except BatchAlreadyRunning as error:
        return render(
            request,
            "batch/_test_status.html",
            _status_context(str(error)),
            status=409,
        )
    return render(
        request,
        "batch/_test_status.html",
        _status_context("운영 데이터 최신화 작업을 시작했습니다."),
        status=202,
    )


@never_cache
@require_POST
def batch_test_clear_log(request: HttpRequest) -> HttpResponse:
    """Manifest와 실행 상태는 유지하고 화면에 표시하는 배치 로그만 비운다."""
    if batch_is_running():
        return render(
            request,
            "batch/_test_status.html",
            _status_context("배치 실행 중에는 로그를 초기화할 수 없습니다."),
            status=409,
        )

    log_path = Path(settings.DATA_DIR) / "logs" / LOG_FILE
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text("", encoding="utf-8")
    except OSError as error:
        return render(
            request,
            "batch/_test_status.html",
            _status_context(f"로그를 초기화하지 못했습니다: {error}"),
            status=500,
        )
    return render(
        request,
        "batch/_test_status.html",
        _status_context("최근 로그를 초기화했습니다."),
    )
