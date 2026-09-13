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
- CSV 경로는 읽는 시점의 `settings.DATA_DIR`을 사용한다.
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
