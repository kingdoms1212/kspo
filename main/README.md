# SPORT INSIGHT 구조 검토

현재 구현은 **Django 서버 렌더링 MVC/MTV** 구조다. React 소스나 REST API는 현재 `main`에 없다.
CSV 스냅샷을 직접 읽으며, 도메인 데이터는 Django ORM 모델에 저장하지 않는다.

## 기능별 구성

```text
main/
  main/                     Django 설정, 프로젝트 URL
  app/
    dashboard/              지역별 활용정보·종목 이용현황
      models.py             CSV 데이터 접근
      services.py           집계·차트 정렬
      views.py              요청 처리와 템플릿 렌더링
      urls.py               /dashboard
      tests.py
    programs/               프로그램 조회·비교·엑셀 내보내기
      models.py
      services.py
      views.py
      urls.py               /programs, /export/programs.xlsx
      tests.py
    facilities/             시설 조회·선택·엑셀 내보내기
      models.py
      services.py
      views.py
      urls.py               /facilities, /export/facilities.xlsx
      tests.py
    common/
      data.py               CSV 읽기와 값 정규화
      exports.py            Excel(.xlsx) 응답·헤더 서식·문자열 보존
      calculations.py       예산·수혜율·도보시간 순수 계산
    urls.py                 세 모듈 URL 조합
    models.py               기존 import 호환 계층
    services.py             기존 import 호환 계층
    views.py                기존 import 호환 계층
    tests.py                공통 레이아웃·기존 동작 통합 테스트
  templates/
    dashboard/index.html
    programs/index.html
    facilities/index.html
    base.html               공통 레이아웃
    components/             아이콘·출처 상태·페이지 이동
  static/                   공통 CSS
```

세 기능은 하나의 Django 앱 `app` 안의 Python 패키지다. 별도 `INSTALLED_APPS` 등록이나
DB 마이그레이션은 필요 없다. Model은 데이터 접근, Service는 필터·정렬·계산,
Controller(Django view)는 요청·페이지 이동·응답, Template은 화면 표시를 담당한다.

새 코드는 소유 모듈에서 직접 import한다. 예: `app.programs.services.filter_programs`.
공통 호환 파일에 로직을 추가하지 않는다. 테스트 mock도 함수가 사용되는 모듈을 대상으로 한다.

## 검토 및 변경

- 역할별 파일에 섞여 있던 세 기능을 기능별 MVC 패키지로 분리했다.
- URL 경로와 이름, 쿼리 파라미터, 템플릿 컨텍스트를 유지했다.
- 프로그램 페이지와 엑셀 내보내기가 같은 검색 파라미터 추출 함수를 사용한다.
- 검색 정렬 전에 목록을 복사하여 `lru_cache`에 저장된 원본 순서를 변경하지 않는다.
- 엑셀은 openpyxl로 생성한다. 첫 행 고정·자동 필터·열 너비·헤더 서식을 적용하며, 원본 문자열은 명시적 텍스트 셀로 저장해 수식 실행과 전화번호 앞자리 손실을 방지한다.
- 웹 화면은 `data/Batch`의 서울 전용 CSV를 읽으며, 경로는 읽는 시점의
  `settings.DATA_DIR`을 사용한다.
- 기존 통합 테스트와 모듈별 라우팅·필터·캐시·내보내기 회귀 테스트를 추가했다.

## 유지된 데이터 제약과 후속 검토

이번 변경은 모듈 분리 중심이며 아래 기존 데이터 동작은 유지했다.

- 프로그램은 원본 선두 최대 15,000행, 종목 이용현황은 최대 50,000행만 읽는다.
- 대시보드에는 여러 기간·대상 정의가 섞일 수 있다. 최신 기준 연도 표시는 해당 연도만
  필터링했다는 뜻이 아니다. 전국 종목 참고자료와 프로그램 건수는 지역 필터와 범위가 다르다.
- 지역 활용정보의 시설 수 합산은 중복 시설을 제거한 고유 시설 수가 아니다.
- 일부 관측값이 누락되어도 기존 집계는 알려진 값만 합산한다. 완전성 표시를 별도 설계해야 한다.
- 시설·프로그램 ID는 파일 행 순서에 의존한다. 원본 갱신을 지원하려면 안정적인 식별 키가 필요하다.
- 프로세스 내 CSV 캐시는 파일 변경을 자동 감지하지 않는다. 원본 교체 후 서버를 재시작해야 한다.
- 프로그램 시설명만으로 계산하는 시설 건수는 동명이 시설을 구분하지 못한다.

이 항목들은 화면과 내보내기가 공유하는 모듈별 서비스·모델에서 후속 개선할 수 있다.

## 검증

저장소 루트에서 실행한다. 최초 설치 시 `config\Scripts\python.exe -m pip install -r main/requirements.txt`로 의존성을 설치한다.

```powershell
config\Scripts\python.exe main\manage.py test app
config\Scripts\python.exe main\manage.py check
config\Scripts\python.exe main\manage.py makemigrations --check --dry-run
```

모듈만 검사하려면 `test app.programs`처럼 지정한다.

## 서울 CSV 배치와 자동 캐시 갱신

웹서비스 시작 시 `app/Batch/seoul_csv_batch.py`를 실행하고, 서버가 실행 중이면
APScheduler가 매주 일요일 00시에 같은 배치를 실행한다. 배치는 서울 전용 CSV
네 개를 교체한 뒤 `batch_manifest.json`의 세대를 갱신한다. 각 웹 프로세스는
작은 manifest 변경만 확인하고, 세대가 바뀐 경우 자신의 프로그램·이용현황·
시설·교통 캐시를 자동으로 다시 만든다.

실행 요일과 시각은 `main/settings.py`의 `SEOUL_BATCH_SCHEDULE`에서 변경한다.
개발 서버 자동 재로더의 실제 서버 프로세스에서만 스케줄러가 한 번 시작된다.
서버가 종료되어 있으면 예약 실행도 동작하지 않지만, 다음 서버 시작 시 시작
배치가 최신 CSV를 다시 생성한다.

배치 실행 기록은 `data/Batch/logs/seoul_batch.log`에 남는다.

## 프로그램 설계 (2026-09-16)

좌측 메뉴는 **프로그램 설계 / 프로그램 현황 / 시설 현황**으로 유지한다. 좁은 화면에서도 좌측에 남는다.
기존 Django 템플릿·HTMX를 사용하며 추가 라이브러리는 필요하지 않다.

- `app/dashboard/planning.py`: 지역 별칭, 명시적 종목-시설유형 대응, 입력 검증과 서명된 시설 선택값.
- `app/dashboard/plan_views.py`: 시설 후보(20개씩), 시설 상세·교통 조회, 저장 없는 계획서 응답.
- `templates/dashboard/_planner.html`, `_plan_detail.html`, `_plan_result.html`: 단계별 설계·상세·결과 화면.
- `static/program-planner.js`, `program-planner.css`: 키오스크 스타일 입력 흐름, 재선택, 결과 팝업·인쇄.
- `static/dashboard-region-map.js`: 시도·시군구 클릭과 선택창 변경을 실제 조회에 연결. HTMX 교체 후에도 동작.

지역 현황 → 계획서 생성하기 → 종목 선택 → 시설 상세 확인·복수 선택 → 시설 확정 → 프로그램 입력 → 계획서 생성 순서다.
시설 재선택은 이전 선택과 작성 내용을 유지한다. 지역·종목 변경은 시설 선택을 해제하므로 다시 확정해야 한다.
생성 성공 시 지역과 입력 화면을 초기화하며, 팝업은 생성 시점의 지역 통계와 시설·입력 정보를 표시한다.
DB·세션·브라우저 저장소에 계획서를 저장하지 않는다. 팝업을 닫으면 결과 DOM도 비운다. 재방문 시 복구 기능은 없다.

후보는 선택 지역에 속하고 종목이 시설유형/업종에 명시된 정상운영 시설만 포함한다. 시설명 추측이나 종합체육관의 종목 추론은 하지 않는다.
현재 대응 종목은 농구·수영·태권도·축구·풋살·배드민턴·탁구·테니스·골프·헬스·복싱·유도·합기도·검도·야구·볼링이다.
시설 최대 20곳, 모집인원은 시설별 동일 값, 수강료는 1인당 월/회/과정 기준이다. 무료는 0원으로 입력한다.
이용현황과 시설 명부는 서로 다른 모집단이다. 시설 정원은 모집 가능 인원이 아니며 대관·예약 연동도 하지 않는다.
통합 지역명(전남광주)이나 행정구역 변경으로 명칭이 대응하지 않는 경우 임의 연결하지 않는다.
교통 정보는 기존 시설명·좌표 연결 규칙을 재사용하며, 대표 이미지는 실제 해당 시설 사진이 아님을 표시한다.

프린트는 브라우저 인쇄를 사용한다. 문자·카카오톡 버튼은 서비스 미설정 안내를 표시한다.
실제 전송에는 문자 서비스·발신번호·수신자 또는 카카오 앱·도메인 설정과 별도의 연결 구현이 필요하다.

검증: Django 전체 156개 테스트 통과. 실제 브라우저에서 서울/농구 시설 조회, 시설 확정·재선택,
입력 유지, 계획서 팝업, 팝업 종료 시 결과 삭제, 전국 초기화, 지도 송파구 클릭과 경기 재선택,
700px 화면 좌측 메뉴를 확인했다.
