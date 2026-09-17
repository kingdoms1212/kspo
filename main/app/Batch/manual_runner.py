"""웹 화면에서 운영 지역 데이터 배치를 즉시 실행하고 상태를 기록한다."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.utils import timezone

from app.common.regions import get_region_profile

from .data_refresh import refresh_region_data
from .regional_csv_batch import (
    LOCK_FILE,
    LOCK_STALE_SECONDS,
    MANIFEST_FILE,
)


STATUS_FILE = "manual_batch_status.json"
STATUS_STALE_SECONDS = 30
_thread_lock = threading.Lock()


class BatchAlreadyRunning(RuntimeError):
    """예약 또는 수동 배치가 이미 실행 중임을 나타낸다."""


def _output_dir() -> Path:
    """웹 서비스가 실제로 읽는 배치 출력 경로를 반환한다."""
    return Path(settings.DATA_DIR)


def _status_path() -> Path:
    return _output_dir() / STATUS_FILE


def _now() -> str:
    return timezone.localtime().strftime("%Y-%m-%d %H:%M:%S")


def _write_status(status: dict) -> None:
    """다른 웹 프로세스도 읽을 수 있도록 상태를 원자적으로 저장한다."""
    path = _status_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    part = path.with_suffix(path.suffix + ".part")
    with part.open("w", encoding="utf-8", newline="\n") as output:
        json.dump(status, output, ensure_ascii=False, indent=2)
        output.write("\n")
        output.flush()
        os.fsync(output.fileno())
    os.replace(part, path)


def read_manual_batch_status() -> dict:
    """최근 수동 실행 상태를 읽고 없거나 손상되면 기본 상태를 반환한다."""
    path = _status_path()
    try:
        with path.open("r", encoding="utf-8") as source:
            status = json.load(source)
        if isinstance(status, dict):
            current = status.get("status")
            if current in {"queued", "running"} and not _batch_lock_is_active():
                age = timezone.now().timestamp() - path.stat().st_mtime
                if age > STATUS_STALE_SECONDS:
                    status.update({
                        "status": "failed",
                        "finished_at": _now(),
                        "error": "별도 배치 프로세스가 시작되지 않았거나 중단되었습니다.",
                        "progress_message": "배치 중단",
                    })
                    _write_status(status)
            return status
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        pass
    return {
        "status": "idle",
        "requested_at": None,
        "started_at": None,
        "finished_at": None,
        "job_id": None,
        "generation": None,
        "error": "",
        "progress_percent": 0,
        "progress_message": "실행 대기",
    }


def _batch_lock_is_active() -> bool:
    """예약 배치를 포함해 운영 파일 교체가 진행 중인지 확인한다."""
    path = _output_dir() / LOCK_FILE
    try:
        age = timezone.now().timestamp() - path.stat().st_mtime
    except FileNotFoundError:
        return False
    return age <= LOCK_STALE_SECONDS


def batch_is_running() -> bool:
    """수동 또는 예약 배치가 현재 실행 중인지 반환한다."""
    current = read_manual_batch_status()
    return (
        current.get("status") in {"queued", "running"}
        or _batch_lock_is_active()
    )


def _manifest_generation() -> str | None:
    try:
        with (_output_dir() / MANIFEST_FILE).open("r", encoding="utf-8") as source:
            manifest = json.load(source)
        return manifest.get("generation")
    except (FileNotFoundError, OSError, json.JSONDecodeError, AttributeError):
        return None


def _run_manual_batch(job_id: str, requested_at: str) -> None:
    """예약 배치와 같은 함수로 운영 데이터를 갱신하고 실행 결과를 남긴다."""
    started_at = _now()

    def write_running_progress(percent: int, message: str) -> None:
        _write_status({
            "status": "running",
            "requested_at": requested_at,
            "started_at": started_at,
            "finished_at": None,
            "job_id": job_id,
            "generation": None,
            "error": "",
            "progress_percent": percent,
            "progress_message": message,
        })

    write_running_progress(0, "배치 시작 준비 중")
    try:
        refresh_region_data(
            get_region_profile(settings.BATCH_REGION_KEY),
            output_dir=_output_dir(),
            progress_callback=write_running_progress,
        )
    except Exception as error:
        last_status = read_manual_batch_status()
        _write_status({
            "status": "failed",
            "requested_at": requested_at,
            "started_at": started_at,
            "finished_at": _now(),
            "job_id": job_id,
            "generation": None,
            "error": str(error)[:2000],
            "progress_percent": last_status.get("progress_percent", 0),
            "progress_message": "배치 실패",
        })
    else:
        _write_status({
            "status": "success",
            "requested_at": requested_at,
            "started_at": started_at,
            "finished_at": _now(),
            "job_id": job_id,
            "generation": _manifest_generation(),
            "error": "",
            "progress_percent": 100,
            "progress_message": "배치 완료",
        })


def start_manual_batch() -> str:
    """운영 배치를 웹 서버와 분리된 프로세스로 실행한다."""
    with _thread_lock:
        current = read_manual_batch_status()
        if current.get("status") in {"queued", "running"} or _batch_lock_is_active():
            raise BatchAlreadyRunning("지역 데이터 배치가 이미 실행 중입니다.")

        job_id = uuid4().hex
        requested_at = _now()
        queued_status = {
            "status": "queued",
            "requested_at": requested_at,
            "started_at": None,
            "finished_at": None,
            "job_id": job_id,
            "generation": None,
            "error": "",
            "progress_percent": 0,
            "progress_message": "실행 대기",
        }
        _write_status(queued_status)
        log_dir = _output_dir() / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        worker_log = (log_dir / "manual_batch_worker.log").open("ab")
        command = [
            sys.executable,
            str(Path(settings.BASE_DIR) / "manage.py"),
            "run_manual_region_batch",
            "--job-id",
            job_id,
            "--requested-at",
            requested_at,
            "--verbosity",
            "0",
            "--no-color",
        ]
        process_options = {
            "cwd": str(settings.BASE_DIR),
            "stdin": subprocess.DEVNULL,
            "stdout": worker_log,
            "stderr": subprocess.STDOUT,
            "close_fds": True,
        }
        if os.name == "nt":
            process_options["creationflags"] = (
                subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
            )
        else:
            process_options["start_new_session"] = True
        try:
            subprocess.Popen(command, **process_options)
        except Exception as error:
            queued_status.update({
                "status": "failed",
                "finished_at": _now(),
                "error": f"배치 작업을 시작하지 못했습니다: {error}",
                "progress_message": "실행 시작 실패",
            })
            _write_status(queued_status)
            raise
        finally:
            worker_log.close()
        return job_id
