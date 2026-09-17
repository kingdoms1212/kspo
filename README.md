# SPORT INSIGHT

공공기관 체육복지 담당자를 위한 Django 기반 조회 화면입니다. 최초 공통 레이아웃 구현 후, 사용자 요청에 따라 **시안 기준으로 세 화면을 전면 재구성**했습니다. 대시보드 3열, 프로그램 좌측 검색·우측 결과, 시설 목록표·상세 패널로 구성합니다. [디자인 검토 및 변경 내용](docs/DESIGN-REVIEW.md)을 참고하세요. 2026-09-14 `data/` 재구성에 맞춰 세 모듈의 원본을 다시 붙였습니다. 지도 기능은 아직 전체 명세를 충족하지 않습니다.

## 실행

PowerShell에서 `C:\kspo`를 작업 디렉터리로 사용합니다. 기존 `config` 가상환경의 Python과 Django 6.1.1을 유지했습니다. 외부 정책 목록 크롤링을 위해 `beautifulsoup4`를 추가로 설치했습니다(`main/requirements.txt` 참조).

```powershell
.\config\Scripts\python.exe main/manage.py runserver 127.0.0.1:8000
```

브라우저에서 <http://127.0.0.1:8000/>에 접속합니다. `/`는 `/dashboard`로 이동하며, 메뉴는 `/dashboard`, `/programs`, `/facilities` 세 개입니다. 상단의 `체육정책` 버튼은 문화체육관광부 체육정책 목록 최신 10건을 팝업으로 보여줍니다. 이 목록만 외부 사이트를 실시간으로 읽으며, 수집기는 `main/app/common/crawler.py`(beautifulsoup4)이고, 주소와 수집 규칙은 `main/main/settings.py`의 `POLICY_SOURCE`에 있습니다. 성공은 15분, 실패는 60초 캐시하며 팝업을 열 때만 요청합니다.

화면은 htmx로 부분 렌더링합니다. 페이지 이동·필터·시설 선택은 전체 문서를 다시 그리지 않고 해당 영역만 교체하므로 스크롤 위치가 유지됩니다. 외부 라이브러리는 모두 `main/static/vendor/`에 포함했으며 CDN이나 빌드 도구는 쓰지 않습니다(아래 [외부 자산](#외부-자산) 참조). JS를 끈 브라우저에서는 모든 링크가 일반 이동으로 동작합니다. 뒤로·앞으로 가기는 해당 URL을 다시 요청해 전체 페이지를 받습니다.

## 외부 자산

런타임에 외부 호스트를 호출하지 않습니다. 화면은 폐쇄망에서도 동작해야 하고, 경계 자료를 `@master` 브랜치로 참조하면 이 저장소의 커밋 없이 지도 모양이 바뀔 수 있기 때문입니다. 아래 사본을 `main/static/vendor/`에 둡니다.

| 파일 | 버전·출처 | 라이선스 |
|---|---|---|
| `htmx.min.js` | htmx | BSD-2-Clause |
| `echarts.min.js` | Apache ECharts 5.6.0 (`npm/echarts@5.6.0/dist`) | Apache-2.0 |
| `skorea_provinces_geo_simple.json` | southkorea-maps `kostat/2013` · 시·도 17개 | 원자료 KOSTAT |
| `skorea_municipalities_geo_simple.json` | southkorea-maps `kostat/2013` · 시군구 251개 | 원자료 KOSTAT |

`region-map.js`는 이 폴더를 자기 `src`에서 유도하므로 `STATIC_URL`을 바꿔도 따라갑니다. 두 경계 파일은 KOSTAT 코드 앞 두 자리로 시·도와 시군구를 잇습니다. 회귀 테스트는 `app/common/test_staticfiles.py`의 `OfflineMapAssetTests`이며, 정적 자산 200 응답·`region-map.js` 내 외부 URL 부재·두 파일의 코드 일치를 확인합니다.

## 검증 명령

```powershell
.\config\Scripts\python.exe main/manage.py check
.\config\Scripts\python.exe main/manage.py test app -v 2
.\config\Scripts\python.exe -m compileall -q app main/main scripts
.\config\Scripts\python.exe scripts/inspect_sources.py
```

단위·렌더링 테스트 100개를 통과했습니다. 실제 CSV를 사용하는 Django Client에서도 세 화면, 프로그램 2페이지·복합 필터, 시설 상세 및 시설 2페이지, 엑셀 3종에서 200을 확인했습니다. 루트 302도 회귀 테스트합니다. 별도의 TypeScript 검사·프런트 빌드 설정은 없습니다.

수동 검증: 1440×900, 1280×800, 좁은 화면에서 세 메뉴 이동, 현재 메뉴 표시, Tab으로 본문 바로가기 → 메뉴 → 자료 안내 → 필터 순서 이동, Enter로 조회, 비교표의 가로 스크롤을 확인합니다. 이번 환경에서는 연결 가능한 브라우저가 없어 실제 화면 캡처·포커스 이동·뷰포트 검증은 미실행입니다.

## 데이터 상태

`data/`에는 CSV 4개가 있습니다. 화면은 그중 3개를 읽습니다.

| 파일 | 사용 모듈 | 적재 |
|---|---|---|
| `sports_voucher_usage.csv` | 대시보드 | 원장 517,101행을 시군구 단위로 집계 |
| `public_sports_program.csv` | 프로그램 | 396,693행 중 중복 101,660행 제외 → 295,033건 |
| `sports_facility_status.csv` | 시설 | 152,967행 중 삭제 표시 13,843행 제외 → 139,124건 (공공 35,673 · 신고 102,881 · 등록 570) |
| `facility_transit.csv` | 시설 상세 | 1,639,279행 · 시설 상세를 열 때만 색인 |
| `전국공공체육시설 데이터.csv` | 미사용 | 어떤 모듈도 읽지 않음 |

- 시설↔대중교통은 `시설명 + 좌표(소수점 6자리)`가 일치할 때만 연결합니다. 두 자료의 주소 체계가 달라(도로명 vs 지번) 주소로는 16%만 맞고, 이름만으로는 한 시군구 안 동명 시설이 섞입니다. 시설 30,971행(전체 22.3%, 공공 86.7%)에 붙습니다. 정류장은 직선거리 기준으로 가까운 10개만 보여주며, 도보 시간은 원자료의 53.9%가 비어 있어 있는 경우에만 병기합니다.
- 프로그램↔시설은 `(시도코드, 시군구코드, 시설명, 도로명주소)`가 모두 일치할 때만 연결합니다. 시설명만으로는 연결하지 않습니다. 시설 쪽 코드는 `FCLTY_MANAGE_*`를 씁니다 — 일반 `SIGNGU_CD`는 시 단위이거나 주소와 어긋나(7,503건) 연결률이 90.7%에서 70.9%로 떨어집니다. 도로명 정보가 부족한 시설 33,365건은 연결 대상이 아닙니다.
- 시설 목록은 폐업 34,480건을 기본으로 제외합니다. 운영상태 필터에 `정상운영`이 선택된 상태로 표시되며 전체로 넓힐 수 있습니다.
- 화면 간 지역명 대응표가 없습니다. 이용현황은 `서울`·`경기`처럼 짧은 이름을, 시설·프로그램은 `서울특별시`·`경기도` 같은 전체 명칭을 쓰며 두 목록의 교집합이 없습니다.
- 지원대상·수급인원 원본이 없어 수혜율은 계산하지 않고 "미연결"로 표기합니다. 다른 자료로 추정하지 않습니다.
- 수강료의 월/회/과정 단위는 미확인이며 원본 기재 그대로 표시합니다. `FCLTY_STATE_CD`도 의미가 확인되지 않아 해석 없이 값만 보여줍니다.
- 엑셀 내보내기는 한 번에 5만 행까지입니다. 초과하면 잘라내지 않고 거절하며 조건을 좁히도록 안내합니다.
- 현재 화면은 실제 자료 모드이며 시연 데이터 생성이나 누락값 대체가 없습니다.
- 행정경계 지도는 시·도에서 시군구로 드릴다운하며, 경계 자료는 저장소에 포함한 KOSTAT 2013 기준 GeoJSON을 씁니다.

[작업 상태](docs/WORK-STATUS.md)와 [결정 기록](docs/DECISIONS.md)을 참고하세요. 원본 압축파일은 `_handoff/sport-insight-dev-handoff`에 별도로 풀었으며 기존 `_prompt`와 가상환경을 보존했습니다.
