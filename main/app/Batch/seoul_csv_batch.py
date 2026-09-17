"""원본 CSV 네 개를 서울 전용 서비스 CSV로 갱신한다.

새 데이터는 먼저 ``.part`` 파일로 완성한다. 모든 파일의 생성과 검증이
끝나면 현재 ``*_seoul.csv``를 ``*_seoul_temp.csv``로 옮겨 직전 버전을
보관하고, 새 파일을 ``*_seoul.csv``로 반영한다.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from uuid import uuid4

# 원본 이름은 배치와 네 저장소가 함께 쓰므로 공용 모듈에서만 정한다.
from ..common.sources import SOURCE_SPECS, SourceSpec


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DATA_DIR = PROJECT_ROOT / "data"
DEFAULT_OUTPUT_DIR = DEFAULT_DATA_DIR / "Batch"

SEOUL_CODE_PREFIX = "11"
SEOUL_NAMES = frozenset({"서울", "서울특별시"})
MANIFEST_FILE = "batch_manifest.json"
LOCK_FILE = "seoul_batch.lock"
LOG_FILE = "seoul_batch.log"
LOCK_STALE_SECONDS = 6 * 60 * 60


@dataclass(frozen=True)
class ExtractResult:
    source: Path
    output: Path
    source_rows: int
    seoul_rows: int
    skipped_rows: int


def _is_seoul(code: str, name: str) -> bool:
    """두 자리 코드와 전체 행정구역 코드를 모두 서울로 판정한다."""
    normalized_code = (code or "").strip()
    normalized_name = (name or "").strip()
    return normalized_code.startswith(SEOUL_CODE_PREFIX) or normalized_name in SEOUL_NAMES


def _part_path(output: Path) -> Path:
    return output.with_suffix(output.suffix + ".part")


def _discard_path(previous: Path) -> Path:
    return previous.with_suffix(previous.suffix + ".batch_discard")


def _previous_part_path(previous: Path) -> Path:
    return previous.with_suffix(previous.suffix + ".new")


def _write_log(output_dir: Path, message: str) -> None:
    """배치 실행 결과를 한글 로그로 남긴다."""
    log_dir = output_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().astimezone().isoformat(timespec="seconds")
    with (log_dir / LOG_FILE).open("a", encoding="utf-8") as log:
        log.write(f"{timestamp} {message}\n")


@contextmanager
def _batch_lock(output_dir: Path):
    """기동 배치와 예약 배치가 동시에 실행되지 않게 막는다."""
    lock_path = output_dir / LOCK_FILE
    descriptor = None
    for _ in range(2):
        try:
            descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(descriptor, f"pid={os.getpid()}".encode("ascii"))
            break
        except FileExistsError:
            age = datetime.now().timestamp() - lock_path.stat().st_mtime
            if age <= LOCK_STALE_SECONDS:
                raise RuntimeError(f"서울 CSV 배치가 이미 실행 중입니다: {lock_path}")
            lock_path.unlink(missing_ok=True)
    if descriptor is None:
        raise RuntimeError(f"배치 잠금 파일을 만들 수 없습니다: {lock_path}")
    try:
        yield
    finally:
        os.close(descriptor)
        lock_path.unlink(missing_ok=True)


def _copy_or_link(source: Path, target: Path) -> None:
    """가능하면 하드링크로 직전 파일을 빠르게 보관한다."""
    target.unlink(missing_ok=True)
    try:
        os.link(source, target)
    except OSError:
        shutil.copy2(source, target)


def _extract_to_part(source: Path, output: Path, spec: SourceSpec) -> ExtractResult:
    """원본을 순차적으로 읽어 새 최종 파일의 준비본을 생성한다."""
    if not source.is_file():
        raise FileNotFoundError(f"원본 CSV를 찾을 수 없습니다: {source}")

    part = _part_path(output)
    source_rows = 0
    seoul_rows = 0
    skipped_rows = 0

    try:
        with source.open("r", encoding="utf-8-sig", newline="") as input_file:
            reader = csv.reader(input_file)
            header = next(reader, None)
            if not header:
                raise ValueError(f"CSV 헤더가 없습니다: {source.name}")

            missing = [
                column
                for column in (spec.code_column, spec.name_column)
                if column not in header
            ]
            if missing:
                raise ValueError(
                    f"{source.name}에 서울 판별 열이 없습니다: {', '.join(missing)}"
                )

            code_index = header.index(spec.code_column)
            name_index = header.index(spec.name_column)
            required_index = max(code_index, name_index)

            with part.open("w", encoding="utf-8-sig", newline="") as output_file:
                writer = csv.writer(output_file)
                writer.writerow(header)

                for row in reader:
                    source_rows += 1
                    if len(row) <= required_index:
                        skipped_rows += 1
                        continue
                    if _is_seoul(row[code_index], row[name_index]):
                        writer.writerow(row)
                        seoul_rows += 1

                output_file.flush()
                os.fsync(output_file.fileno())

        if seoul_rows == 0:
            raise ValueError(f"서울 행을 한 건도 찾지 못했습니다: {source.name}")

        return ExtractResult(
            source=source,
            output=output,
            source_rows=source_rows,
            seoul_rows=seoul_rows,
            skipped_rows=skipped_rows,
        )
    except Exception:
        part.unlink(missing_ok=True)
        raise


def _validate_part(path: Path, spec: SourceSpec) -> int:
    """서비스 파일을 바꾸기 전에 준비본이 서울 데이터인지 전수 검사한다."""
    if not path.is_file():
        raise FileNotFoundError(f"새 서울 CSV 준비본을 찾을 수 없습니다: {path}")

    rows = 0
    with path.open("r", encoding="utf-8-sig", newline="") as source:
        reader = csv.reader(source)
        header = next(reader, None)
        if not header:
            raise ValueError(f"CSV 헤더가 없습니다: {path.name}")
        missing = [
            column
            for column in (spec.code_column, spec.name_column)
            if column not in header
        ]
        if missing:
            raise ValueError(
                f"{path.name}에 서울 판별 열이 없습니다: {', '.join(missing)}"
            )

        code_index = header.index(spec.code_column)
        name_index = header.index(spec.name_column)
        required_index = max(code_index, name_index)
        for line_number, row in enumerate(reader, start=2):
            if len(row) <= required_index:
                raise ValueError(f"{path.name}의 {line_number}행에 지역 열이 없습니다.")
            if not _is_seoul(row[code_index], row[name_index]):
                raise ValueError(f"{path.name}의 {line_number}행은 서울 데이터가 아닙니다.")
            rows += 1

    if rows == 0:
        raise ValueError(f"서울 행이 없는 준비본은 반영할 수 없습니다: {path.name}")
    return rows


def _rotate_prepared_files(
    output_dir: Path,
    specs: tuple[SourceSpec, ...],
) -> list[Path]:
    """기존 최종본을 temp로 보관하고 준비된 새 파일을 최종본으로 반영한다."""
    files = [
        (
            _part_path(output_dir / spec.final_filename),
            output_dir / spec.final_filename,
            output_dir / spec.previous_filename,
            _discard_path(output_dir / spec.previous_filename),
            _previous_part_path(output_dir / spec.previous_filename),
            spec,
        )
        for spec in specs
    ]

    # 네 준비본이 모두 정상이어야 기존 서비스 파일을 변경한다.
    for part, _, _, discard, previous_part, spec in files:
        if discard.exists() or previous_part.exists():
            raise FileExistsError(
                f"이전 교체 흔적이 남아 있습니다. 먼저 상태를 확인해 주세요: {discard}"
            )
        _validate_part(part, spec)

    discarded_previous: list[tuple[Path, Path]] = []
    prepared_previous: list[Path] = []
    rotated_finals: list[tuple[Path, Path]] = []
    promoted_parts: list[tuple[Path, Path]] = []
    try:
        # final 경로를 비우지 않도록 직전 파일의 링크나 복사본을 먼저 만든다.
        for _, final, _, _, previous_part, _ in files:
            if final.exists():
                _copy_or_link(final, previous_part)
                prepared_previous.append(previous_part)

        # 기존 temp는 즉시 삭제하지 않고 교체 성공 전까지만 복구용으로 보관한다.
        for _, _, previous, discard, _, _ in files:
            if previous.exists():
                os.replace(previous, discard)
                discarded_previous.append((discard, previous))

        # 현재 서비스 파일을 이번 실행의 temp 백업으로 이동한다.
        for _, final, previous, _, previous_part, _ in files:
            if previous_part.exists():
                os.replace(previous_part, previous)
                rotated_finals.append((previous, final))

        # 모든 원본에서 새로 만든 준비본을 서비스용 최종 파일로 반영한다.
        for part, final, _, _, _, _ in files:
            os.replace(part, final)
            promoted_parts.append((final, part))
    except Exception:
        # 중간 실패 시 새 파일과 기존 final, temp를 실행 전 상태로 되돌린다.
        for final, part in reversed(promoted_parts):
            if final.exists():
                os.replace(final, part)
        for previous, final in reversed(rotated_finals):
            if previous.exists():
                _copy_or_link(previous, final)
                previous.unlink(missing_ok=True)
        for discard, previous in reversed(discarded_previous):
            if discard.exists():
                os.replace(discard, previous)
        for previous_part in prepared_previous:
            previous_part.unlink(missing_ok=True)
        raise

    # 교체가 끝난 뒤에만 지난 실행의 temp를 실제로 삭제한다.
    for discard, _ in discarded_previous:
        discard.unlink(missing_ok=True)
    return [final for _, final, _, _, _, _ in files]


def _publish_manifest(output_dir: Path, results: list[ExtractResult]) -> str:
    """네 파일 교체가 끝난 뒤 새 배치 세대를 원자적으로 공개한다."""
    generation = uuid4().hex
    manifest = {
        "generation": generation,
        "created_at": datetime.now().astimezone().isoformat(),
        "files": {},
    }
    for result in results:
        stat = result.output.stat()
        manifest["files"][result.output.name] = {
            "mtime_ns": stat.st_mtime_ns,
            "size": stat.st_size,
            "rows": result.seoul_rows,
        }

    path = output_dir / MANIFEST_FILE
    part = path.with_suffix(path.suffix + ".part")
    with part.open("w", encoding="utf-8", newline="\n") as output:
        json.dump(manifest, output, ensure_ascii=False, indent=2)
        output.write("\n")
        output.flush()
        os.fsync(output.fileno())
    os.replace(part, path)
    return generation


def refresh_seoul_csvs(
    data_dir: Path = DEFAULT_DATA_DIR,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    specs: tuple[SourceSpec, ...] = SOURCE_SPECS,
) -> list[ExtractResult]:
    """서울 CSV를 새로 만들고 기존 최종본과 안전하게 교대한다."""
    data_dir = Path(data_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    results: list[ExtractResult] = []

    with _batch_lock(output_dir):
        _write_log(output_dir, "서울 CSV 배치를 시작합니다.")
        try:
            for spec in specs:
                final = output_dir / spec.final_filename
                results.append(_extract_to_part(data_dir / spec.filename, final, spec))
            _rotate_prepared_files(output_dir, specs)
            generation = _publish_manifest(output_dir, results)
            _write_log(output_dir, f"서울 CSV 배치를 완료했습니다. 세대={generation}")
        except Exception as error:
            for spec in specs:
                _part_path(output_dir / spec.final_filename).unlink(missing_ok=True)
            _write_log(output_dir, f"서울 CSV 배치가 실패했습니다. 오류={error}")
            raise

    return results


def main() -> int:
    parser = argparse.ArgumentParser(
        description="원본 CSV 네 개에서 서울 행을 추출해 서비스 CSV를 갱신합니다."
    )
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    results = refresh_seoul_csvs(args.data_dir, args.output_dir)
    for result in results:
        previous = result.output.with_name(
            result.output.name.replace("_seoul.csv", "_seoul_temp.csv")
        )
        print(
            f"{result.source.name} -> {result.output.name}: "
            f"원본 {result.source_rows:,}행, 서울 {result.seoul_rows:,}행, "
            f"건너뜀 {result.skipped_rows:,}행, "
            f"직전 파일 {'보관' if previous.exists() else '없음'}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
