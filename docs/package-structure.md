# 유지보수를 위한 패키지 경계

기존 기능·URL·배치 파일 형식을 유지하면서 중복 정책과 결과 처리, 웹 실행 관리를 분리했다.
현재는 하나의 Django 앱 아래 기능별 Python 패키지를 유지한다.

## 현재 적용한 구조

```text
app/
  shared/regions.py          지역 선택 정책·지역/시군구 옵션 생성
  planning/reports.py        검증된 입력·통계로 설계서 표시 데이터 구성
  planning/snapshots.py      결과 서명·검증·보관 크기 규약
  dashboard/presenters.py    차트 표시 계산 (저장소 조회 없음)
  runtime/targets.py         사전 적재 대상과 공개 콜백 등록
  runtime/csv_warmup.py      웹 프로세스의 적재·갱신 스레드 관리
  runtime/readiness.py       목록 준비 상태 판정 (화면·상태 점검·게이트 공용)
  runtime/middleware.py      미준비 요청을 요청 형식에 맞는 503으로 응답
  common/versioned_csv.py    CSV 세대 감지·캐시 교체
```

- `shared`는 구체적인 업무 패키지를 import하지 않는다. 프로그램과 시설의 지역 설정은 각각 유지한다.
- `dashboard/plan_views.py`는 요청 검증·응답을 담당하고 보고서 구성·서명은 `planning`에 위임한다.
- `planning/reports.py`는 전달받은 입력·통계만 사용한다. CSV를 재조회하지 않으며 차트 계산은
  `dashboard/presenters.py`를 재사용한다. 입력 폼·후보 시설 선정은 아직 기존 `dashboard/planning.py`에 있다.
- `runtime/targets.py`만 적재할 기능을 조립한다. 각 기능은 `refresh_snapshot()`과
  `set_background_refresh(enabled)`를 공개한다. 실행 관리자는 `_value`나 `_snapshot_cache`에 접근하지 않는다.
- `VersionedCsvCache.refresh()`는 내부 데이터 대신 메모리 교체 여부를 반환한다.
- 준비 상태는 `VersionedCsvCache.is_loaded`(최초 적재 여부)만 본다. 세대 갱신 중에는 옛 목록을
  그대로 서비스하므로 미준비로 보지 않는다. 자세한 내용은 [준비 상태 문서](readiness.md).
- 새 목록을 사전 적재하려면 기능의 공개 갱신 함수를 구현하고 `CsvWarmupTarget`으로 등록한다.
  교통 상세 색인은 기존처럼 필요한 시점에 적재한다.

## 호환성

- 기존 URL·이름, 관리 명령, manifest 발행 형식, CSV 경로, 스레드 개수·확인 주기는 변경하지 않았다.
- `programs/region_scope.py`, `facilities/region_scope.py`의 기존 클래스·함수 이름을 유지한다.
- `common/csv_warmup.py`는 새 실행 모듈의 공개 함수를 다시 내보낸다. 별도 스레드나 캐시는 만들지 않는다.
- 기존 로그 수집 설정과의 호환을 위해 CSV 실행 관리 로그 이름도 유지한다.
- `dashboard/services.py`의 기존 차트 함수 import 경로는 재노출로 유지한다.
- 최근 생성 목록의 localStorage 키, 최대 5건 정책, 서명 salt·version·payload·크기 제한은 유지한다.
  서명에 새 유효기간을 추가하지 않았으므로 기존에 보관한 결과도 같은 키로 복원할 수 있다.

## 이번에 제외한 변경

- `Batch` → `batch` 이름 변경: Windows/Linux 파일명 처리 및 기존 실행·import 경로 영향.
- 모든 `models.py` → `repository.py` 이동: 기존 조회 경로·테스트 대체 지점·캐시 객체 중복 생성 위험.
- CSV 읽기·파일 교체·manifest 구조 재설계: 배치와 서비스 간 데이터 일관성 영향.
- 설계 화면 JavaScript 일괄 분할 및 상태 머신 변경: 단계 이동·HTMX·팝업·인쇄 동작 영향.
- 템플릿/정적 파일 경로 일괄 이동과 호환 모듈 삭제: 자산 참조·브라우저 보관 결과·외부 호출 영향.
- 지역 별칭·서울 고정 범위 및 업무별 필터 통합: 화면별 운영 정책이 달라 동작 변경 가능.

프로그램 중복 제거, 시설 운영 상태, 종목별 후보 선정, 집계 규칙은 각 기능에 유지한다.
추가 공통화는 비슷한 코드 모양보다 동일한 변경 이유와 동작 계약이 있는지를 기준으로 판단한다.

## 검증 기준

Python 회귀 테스트와 기존 JavaScript 테스트를 함께 실행한다. 리팩터링 전에도 발생하는
프로그램 목록 스크롤 복원 테스트 실패는 별도 문제로 구분한다. 기존 v1 서명 결과의 복원,
영역별 설정 독립성, CSV 갱신 실패 시 기존 목록 유지 및 기동 경로를 확인한다.
