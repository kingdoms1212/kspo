"""원본 CSV 네 개를 설정된 지역의 서비스 CSV로 갱신한다.

새 데이터는 먼저 ``.part`` 파일로 완성한다. 모든 파일의 생성과 검증이
끝나면 준비된 파일을 서비스용 최종 파일로 바로 반영하며, 직전 파일을
별도의 ``*_temp.csv``로 보관하지 않는다.
"""
from __future__ import annotations

import argparse
import codecs
import csv
import hashlib
import json
import os
import sys
from contextlib import contextmanager
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from time import perf_counter

PROJECT_ROOT = Path(__file__).resolve().parents[3]
# 파일을 직접 실행해도 Django 앱의 공통 지역 모듈을 찾게 한다.
MAIN_ROOT = PROJECT_ROOT / "main"
if str(MAIN_ROOT) not in sys.path:
    sys.path.insert(0, str(MAIN_ROOT))

from app.common.regions import REGION_PROFILES, RegionProfile, get_region_profile
DEFAULT_DATA_DIR = PROJECT_ROOT / "data"
DEFAULT_OUTPUT_DIR = DEFAULT_DATA_DIR / "Batch"

DEFAULT_REGION_PROFILE = get_region_profile("seoul")
MANIFEST_FILE = "batch_manifest.json"
LOCK_FILE = "regional_batch.lock"
LOG_FILE = "regional_batch.log"
LOCK_STALE_SECONDS = 6 * 60 * 60


def _formatted_now() -> str:
    """Manifest와 로그에서 공통으로 사용할 날짜와 시각을 반환한다."""
    return datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S")


@dataclass(frozen=True)
class SourceSpec:
    key: str
    filename: str
    province_code_column: str
    province_name_column: str
    district_code_column: str
    district_name_column: str

    def final_filename_for(self, profile: RegionProfile) -> str:
        return f"{Path(self.filename).stem}_{profile.output_suffix}.csv"

    @property
    def final_filename(self) -> str:
        """기존 호출부 호환을 위해 기본 서울 파일명을 반환한다."""
        return self.final_filename_for(DEFAULT_REGION_PROFILE)


@dataclass(frozen=True)
class ExtractResult:
    source: Path
    output: Path
    source_rows: int
    matched_rows: int
    skipped_rows: int
    missing_region_codes: int
    invalid_region_codes: int
    region_code_mismatches: int
    sha256: str

    @property
    def seoul_rows(self) -> int:
        """기존 출력과 테스트에서 사용하던 서울 행 이름을 유지한다."""
        return self.matched_rows


class _HashingCsvOutput:
    """CSV를 쓰는 동시에 최종 파일의 SHA-256을 계산한다."""

    def __init__(self, output):
        self.output = output
        self.digest = hashlib.sha256()
        self._write_bytes(codecs.BOM_UTF8)

    def _write_bytes(self, value: bytes) -> int:
        self.digest.update(value)
        return self.output.write(value)

    def write(self, value: str) -> int:
        encoded = value.encode("utf-8")
        self._write_bytes(encoded)
        return len(value)

    def hexdigest(self) -> str:
        return self.digest.hexdigest()


SOURCE_SPECS = (
    SourceSpec(
        "programs", "public_sports_program.csv",
        "CTPRVN_CD", "CTPRVN_NM", "SIGNGU_CD", "SIGNGU_NM",
    ),
    SourceSpec(
        "usage", "sports_voucher_usage.csv",
        "CTPRVN_CD", "CTPRVN_NM", "SIGNGU_CD", "SIGNGU_NM",
    ),
    SourceSpec(
        "facilities", "sports_facility_status.csv",
        "CTPRVN_CD", "CTPRVN_NM", "SIGNGU_CD", "SIGNGU_NM",
    ),
    SourceSpec(
        "transit",
        "facility_transit.csv",
        "ALSFC_CTPRVN_CD",
        "ALSFC_CTPRVN_NM",
        "ALSFC_SIGNGU_CD",
        "ALSFC_SIGNGU_NM",
    ),
)


def _matches_region(code: str, name: str, profile: RegionProfile) -> bool:
    """선택한 지역 프로필을 기준으로 원본 행의 포함 여부를 판정한다."""
    return profile.matches(code, name)


def _is_seoul(code: str, name: str) -> bool:
    """기존 호출부 호환을 위해 서울 프로필 판정을 제공한다."""
    return _matches_region(code, name, DEFAULT_REGION_PROFILE)


def _district_code_issue(province_code: str, district_code: str) -> str | None:
    """원본 전체의 시군구 코드 누락, 형식 오류, 앞자리 불일치를 판정한다."""
    if not district_code:
        return "missing"
    if not district_code.isdigit():
        return "invalid"
    if province_code.isdigit() and province_code[:2] != district_code[:2]:
        return "mismatch"
    return None


def _province_code_issue(province_code: str) -> str | None:
    """대상 지역으로 판정된 행의 시도 코드가 유효한지 확인한다."""
    if not province_code:
        return "missing"
    if not province_code.isdigit():
        return "invalid"
    return None


def _region_code_issue(province_code: str, district_code: str) -> str | None:
    """최종 결과 파일에 남을 행의 모든 지역 코드를 검증한다."""
    return (
        _district_code_issue(province_code, district_code)
        or _province_code_issue(province_code)
    )


def _part_path(output: Path) -> Path:
    return output.with_suffix(output.suffix + ".part")


def _legacy_temp_path(output_dir: Path, spec: SourceSpec, profile: RegionProfile) -> Path:
    """이전 배치 버전이 남긴 temp 백업 경로를 반환한다."""
    return output_dir / f"{Path(spec.filename).stem}_{profile.output_suffix}_temp.csv"


def _write_log(output_dir: Path, message: str) -> None:
    """배치 실행 결과를 한글 로그로 남긴다."""
    log_dir = output_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    timestamp = _formatted_now()
    with (log_dir / LOG_FILE).open("a", encoding="utf-8") as log:
        log.write(f"{timestamp} {message}\n")


def _format_elapsed(seconds: float) -> str:
    """배치 소요 시간을 분과 초 단위의 읽기 쉬운 문장으로 만든다."""
    total_seconds = max(0, round(seconds))
    minutes, remaining_seconds = divmod(total_seconds, 60)
    if minutes and remaining_seconds:
        return f"{minutes}분 {remaining_seconds}초"
    if minutes:
        return f"{minutes}분"
    return f"{remaining_seconds}초"


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
                raise RuntimeError(f"지역 CSV 배치가 이미 실행 중입니다: {lock_path}")
            lock_path.unlink(missing_ok=True)
    if descriptor is None:
        raise RuntimeError(f"배치 잠금 파일을 만들 수 없습니다: {lock_path}")
    try:
        yield
    finally:
        os.close(descriptor)
        lock_path.unlink(missing_ok=True)


def _extract_to_part(
    source: Path,
    output: Path,
    spec: SourceSpec,
    profile: RegionProfile,
) -> ExtractResult:
    """원본을 순차적으로 읽어 새 최종 파일의 준비본을 생성한다."""
    if not source.is_file():
        raise FileNotFoundError(f"원본 CSV를 찾을 수 없습니다: {source}")

    part = _part_path(output)
    source_rows = 0
    matched_rows = 0
    skipped_rows = 0
    missing_region_codes = 0
    invalid_region_codes = 0
    region_code_mismatches = 0

    try:
        with source.open("r", encoding="utf-8-sig", newline="") as input_file:
            reader = csv.reader(input_file)
            header = next(reader, None)
            if not header:
                raise ValueError(f"CSV 헤더가 없습니다: {source.name}")

            missing = [
                column
                for column in (
                    spec.province_code_column,
                    spec.province_name_column,
                    spec.district_code_column,
                    spec.district_name_column,
                )
                if column not in header
            ]
            if missing:
                raise ValueError(
                    f"{source.name}에 지역 판별 열이 없습니다: {', '.join(missing)}"
                )

            province_code_index = header.index(spec.province_code_column)
            province_name_index = header.index(spec.province_name_column)
            district_code_index = header.index(spec.district_code_column)
            district_name_index = header.index(spec.district_name_column)
            required_index = max(
                province_code_index,
                province_name_index,
                district_code_index,
                district_name_index,
            )

            with part.open("wb") as raw_output:
                output_file = _HashingCsvOutput(raw_output)
                writer = csv.writer(output_file)
                writer.writerow(header)

                for row in reader:
                    source_rows += 1
                    province_code = (
                        row[province_code_index].strip()
                        if len(row) > province_code_index else ""
                    )
                    province_name = (
                        row[province_name_index]
                        if len(row) > province_name_index else ""
                    )
                    district_code = (
                        row[district_code_index].strip()
                        if len(row) > district_code_index else ""
                    )
                    # 원본 전체의 시군구 코드 품질을 먼저 검사한다.
                    if len(row) <= required_index:
                        issue = "missing"
                    else:
                        issue = _district_code_issue(province_code, district_code)
                    if issue:
                        skipped_rows += 1
                        if issue == "missing":
                            missing_region_codes += 1
                        elif issue == "invalid":
                            invalid_region_codes += 1
                        else:
                            region_code_mismatches += 1
                        continue

                    if not _matches_region(
                        province_code,
                        province_name,
                        profile,
                    ):
                        continue

                    # 이름으로 대상 지역이 확인돼도 시도 코드가 없거나 잘못되면 제외한다.
                    issue = _province_code_issue(province_code)
                    if issue:
                        skipped_rows += 1
                        if issue == "missing":
                            missing_region_codes += 1
                        else:
                            invalid_region_codes += 1
                        continue

                    writer.writerow(row)
                    matched_rows += 1

                raw_output.flush()
                os.fsync(raw_output.fileno())
                output_sha256 = output_file.hexdigest()

        if matched_rows == 0:
            raise ValueError(
                f"{profile.display_name} 행을 한 건도 찾지 못했습니다: {source.name}"
            )

        return ExtractResult(
            source=source,
            output=output,
            source_rows=source_rows,
            matched_rows=matched_rows,
            skipped_rows=skipped_rows,
            missing_region_codes=missing_region_codes,
            invalid_region_codes=invalid_region_codes,
            region_code_mismatches=region_code_mismatches,
            sha256=output_sha256,
        )
    except Exception:
        part.unlink(missing_ok=True)
        raise


def _source_version(data_dir: Path, specs: tuple[SourceSpec, ...]) -> dict:
    """빠른 변경 감지를 위해 배포 버전과 원본 파일 정보를 수집한다."""
    render_commit = os.environ.get("RENDER_GIT_COMMIT", "").strip()
    files = {}
    for spec in specs:
        source = data_dir / spec.filename
        if not source.is_file():
            raise FileNotFoundError(f"원본 CSV를 찾을 수 없습니다: {source}")
        stat = source.stat()
        details = {"size": stat.st_size}
        # 로컬에서는 파일 수정 시각으로 변경을 감지하고 Render에서는 배포 SHA를 사용한다.
        if not render_commit:
            details["mtime_ns"] = stat.st_mtime_ns
        files[spec.filename] = details
    return {"render_git_commit": render_commit, "files": files}


def _current_generation_if_unchanged(
    output_dir: Path,
    specs: tuple[SourceSpec, ...],
    profile: RegionProfile,
    source_version: dict,
) -> str | None:
    """원본과 운영 파일이 그대로면 현재 세대를 반환한다."""
    try:
        with (output_dir / MANIFEST_FILE).open("r", encoding="utf-8") as source:
            manifest = json.load(source)
        if manifest.get("source_version") != source_version:
            return None
        if manifest.get("region", {}).get("key") != profile.key:
            return None
        published = manifest.get("files", {})
        for spec in specs:
            filename = spec.final_filename_for(profile)
            details = published.get(filename, {})
            path = output_dir / filename
            if (
                not path.is_file()
                or not details.get("rows")
                or path.stat().st_size != details.get("size")
            ):
                return None
        generation = manifest.get("generation")
        return str(generation) if generation else None
    except (FileNotFoundError, OSError, json.JSONDecodeError, AttributeError, TypeError):
        return None


def _publish_prepared_files(
    output_dir: Path,
    specs: tuple[SourceSpec, ...],
    profile: RegionProfile,
) -> list[Path]:
    """추출 중 검증을 마친 준비본을 최종 파일로 반영한다."""
    files = [
        (
            _part_path(output_dir / spec.final_filename_for(profile)),
            output_dir / spec.final_filename_for(profile),
            spec,
        )
        for spec in specs
    ]

    # 모든 준비본이 비어 있지 않아야 기존 서비스 파일을 변경한다.
    for part, _, _ in files:
        if not part.is_file() or part.stat().st_size <= len(codecs.BOM_UTF8):
            raise ValueError(f"새 지역 CSV 준비본이 없거나 비어 있습니다: {part.name}")

    # os.replace를 사용해 개별 운영 파일이 불완전한 상태로 노출되지 않게 한다.
    for part, final, _ in files:
        os.replace(part, final)

    # 이전 버전에서 만든 백업이 남아 있으면 성공한 교체 뒤 정리한다.
    for spec in specs:
        _legacy_temp_path(output_dir, spec, profile).unlink(missing_ok=True)
    return [final for _, final, _ in files]


def _publish_manifest(
    output_dir: Path,
    results: list[ExtractResult],
    profile: RegionProfile,
    source_version: dict,
) -> str:
    """네 파일 교체가 끝난 뒤 새 배치 세대를 원자적으로 공개한다."""
    generation = _next_generation(output_dir)
    manifest = {
        "generation": generation,
        "created_at": _formatted_now(),
        "region": {
            "key": profile.key,
            "display_name": profile.display_name,
            "output_suffix": profile.output_suffix,
        },
        "source_version": source_version,
        "files": {},
    }
    for result in results:
        stat = result.output.stat()
        manifest["files"][result.output.name] = {
            "mtime_ns": stat.st_mtime_ns,
            "size": stat.st_size,
            "sha256": result.sha256,
            "rows": result.matched_rows,
            "source_rows": result.source_rows,
            "source_quality": {
                "skipped_rows": result.skipped_rows,
                "missing_region_codes": result.missing_region_codes,
                "invalid_region_codes": result.invalid_region_codes,
                "region_code_mismatches": result.region_code_mismatches,
            },
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


def _next_generation(output_dir: Path) -> str:
    """같은 날짜의 배치 실행 횟수를 세대 번호로 만든다."""
    today = datetime.now().astimezone().strftime("%Y-%m-%d")
    count = 0
    try:
        with (output_dir / MANIFEST_FILE).open("r", encoding="utf-8") as source:
            previous = str(json.load(source).get("generation", ""))
        prefix, separator, sequence = previous.rpartition("_")
        if separator and prefix == today and sequence.isdigit():
            count = int(sequence) + 1
    except (FileNotFoundError, OSError, json.JSONDecodeError, AttributeError):
        pass
    return f"{today}_{count}"


def _notify_progress(
    callback: Callable[[int, str], None] | None,
    percent: int,
    message: str,
) -> None:
    """화면 진행률 기록 실패가 운영 CSV 교체를 막지 않게 전달한다."""
    if callback is None:
        return
    try:
        callback(percent, message)
    except Exception:
        pass


def refresh_region_csvs(
    profile: RegionProfile = DEFAULT_REGION_PROFILE,
    data_dir: Path = DEFAULT_DATA_DIR,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    specs: tuple[SourceSpec, ...] = SOURCE_SPECS,
    progress_callback: Callable[[int, str], None] | None = None,
    force_refresh: bool = False,
) -> list[ExtractResult]:
    """선택 지역 CSV를 만들며 필요하면 원본 변경 여부와 무관하게 재정제한다."""
    data_dir = Path(data_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    results: list[ExtractResult] = []
    started_at = perf_counter()

    with _batch_lock(output_dir):
        _write_log(output_dir, f"{profile.display_name} CSV 배치를 시작합니다.")
        _notify_progress(progress_callback, 5, "원본 CSV 확인 중")
        try:
            source_version = _source_version(data_dir, specs)
            current_generation = None
            if not force_refresh:
                current_generation = _current_generation_if_unchanged(
                    output_dir, specs, profile, source_version
                )
            if current_generation:
                _write_log(
                    output_dir,
                    f"원본 CSV 변경이 없어 기존 세대를 유지합니다. "
                    f"세대={current_generation}",
                )
                _write_log(
                    output_dir,
                    f"{profile.display_name} CSV 변경 확인 소요 시간: "
                    f"{_format_elapsed(perf_counter() - started_at)}.",
                )
                _notify_progress(progress_callback, 100, "원본 변경 없음")
                return results
            if force_refresh:
                _write_log(
                    output_dir,
                    "강제 최신화 요청으로 원본 변경 여부와 관계없이 다시 정제합니다.",
                )

            total_files = len(specs)
            for index, spec in enumerate(specs, start=1):
                file_started_at = perf_counter()
                final = output_dir / spec.final_filename_for(profile)
                result = _extract_to_part(
                    data_dir / spec.filename, final, spec, profile
                )
                results.append(result)
                _write_log(
                    output_dir,
                    f"{spec.filename} 추출 소요 시간: "
                    f"{_format_elapsed(perf_counter() - file_started_at)} "
                    f"(원본 {result.source_rows:,}행, 반영 {result.matched_rows:,}행).",
                )
                percent = 10 + round(index / total_files * 60)
                _notify_progress(
                    progress_callback,
                    percent,
                    f"{Path(spec.filename).stem} 추출 완료",
                )
            _notify_progress(progress_callback, 75, "새 CSV 확인 중")
            publish_started_at = perf_counter()
            _publish_prepared_files(output_dir, specs, profile)
            _write_log(
                output_dir,
                f"운영 CSV 교체 소요 시간: "
                f"{_format_elapsed(perf_counter() - publish_started_at)}.",
            )
            _notify_progress(progress_callback, 90, "운영 CSV 교체 완료")
            manifest_started_at = perf_counter()
            generation = _publish_manifest(
                output_dir, results, profile, source_version
            )
            _write_log(
                output_dir,
                f"Manifest 생성 소요 시간: "
                f"{_format_elapsed(perf_counter() - manifest_started_at)}.",
            )
            _write_log(
                output_dir,
                f"{profile.display_name} CSV 배치를 완료했습니다. 세대={generation}",
            )
            _write_log(
                output_dir,
                f"{profile.display_name} CSV 배치 소요 시간: "
                f"{_format_elapsed(perf_counter() - started_at)}.",
            )
            _notify_progress(progress_callback, 100, "배치 완료")
        except Exception as error:
            for spec in specs:
                _part_path(
                    output_dir / spec.final_filename_for(profile)
                ).unlink(missing_ok=True)
            _write_log(
                output_dir,
                f"{profile.display_name} CSV 배치가 실패했습니다. 오류={error}",
            )
            _write_log(
                output_dir,
                f"{profile.display_name} CSV 배치 실패까지 소요 시간: "
                f"{_format_elapsed(perf_counter() - started_at)}.",
            )
            raise

    return results


def refresh_seoul_csvs(
    data_dir: Path = DEFAULT_DATA_DIR,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    specs: tuple[SourceSpec, ...] = SOURCE_SPECS,
    force_refresh: bool = False,
) -> list[ExtractResult]:
    """기존 호출부에서 서울 프로필 배치를 실행한다."""
    return refresh_region_csvs(
        DEFAULT_REGION_PROFILE,
        data_dir,
        output_dir,
        specs,
        force_refresh=force_refresh,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="원본 CSV 네 개에서 선택 지역 행을 추출해 서비스 CSV를 갱신합니다."
    )
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--region",
        choices=sorted(REGION_PROFILES),
        default=DEFAULT_REGION_PROFILE.key,
    )
    parser.add_argument(
        "--force-refresh",
        action="store_true",
        help="원본 CSV가 변경되지 않았어도 서비스 CSV를 다시 정제합니다.",
    )
    args = parser.parse_args()

    profile = get_region_profile(args.region)
    results = refresh_region_csvs(
        profile,
        args.data_dir,
        args.output_dir,
        force_refresh=args.force_refresh,
    )
    for result in results:
        spec = next(item for item in SOURCE_SPECS if item.filename == result.source.name)
        print(
            f"{result.source.name} -> {result.output.name}: "
            f"원본 {result.source_rows:,}행, {profile.display_name} {result.matched_rows:,}행, "
            f"건너뜀 {result.skipped_rows:,}행"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
