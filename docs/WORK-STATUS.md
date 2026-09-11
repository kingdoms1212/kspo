# SPORT INSIGHT 작업 상태

## 최신 작업 — 시안 전면 재구성 (2026-09-11)

후속 사용자 요청에 따라 대시보드·프로그램·시설 화면 전체 디자인을 재구성했다. [시안 검토표](DESIGN-REVIEW.md) 참조.

- 대시보드: 4개 아이콘 지표와 지도/지역차트/종목·참고지표의 3열 배치.
- 프로그램: 좌측 조건 패널, 우측 요약 4개·TOP 3, 하단 분포 대체 목록과 비교표.
- 시설: 상단 검색, 좌측 표, 우측 시설 기본정보와 연결강좌 상태.
- 공통: 헤더·네이비 사이드바·SVG 아이콘·카드·버튼·표·하단 자료 안내, 단일 CSS 및 반응형 분기.
- 동작: 20행 페이지 이동, 선택 시설·필터 보존, 프로그램 다운로드의 모든 적용조건 전달.
- 변경 파일: `main/templates/base.html`, `dashboard.html`, `programs.html`, `facilities.html`, `components/icons.html`, `icon.html`, `pagination.html`, `main/static/app.css`, `app/views.py`, `app/tests.py`. `main/static/shell.css` 제거. 관련 문서 갱신.
- 검증: Django check 정상, 단위·렌더링 테스트 **12개 통과**, Python compileall 성공. 실제 데이터로 3개 화면·프로그램 2페이지·시설 상세·시설 2페이지 모두 200.
- 브라우저 확인: CUA의 apps/browsers가 빈 배열. 화면 캡처·실제 뷰포트·키보드 조작 검증 미실행.
- 지도 자산·시설 사진·데이터 정규화·XLSX 등 앞서 기록한 의존성은 남아 있다. 아래 기록은 최초 00단계 작업 이력이다.

작업일: 2026-09-11. 기준: 제공 ZIP의 AGENTS.md, CODEX-START.md, 00-bootstrap.md, docs/00~04, 색상 토큰과 시안. 기존 `_prompt`의 AGENTS.md, START.md, WORK-STATUS.md도 확인함.

| 단계 | 상태 | 검증 및 남은 사항 |
|---|---|---|
| 00 공통 레이아웃 | 구현·서버 검증 완료 / 브라우저 검증 대기 | 3개 메뉴, 루트 이동, 자료 상태, 토큰, 반응형·포커스 스타일. 실제 뷰포트·키보드 검증 미실행 |
| 01 데이터 | 기존 부분 구현 / 검증 필요 | CSV 11개 구조 점검 완료. 단위·기간·대상 정의·연계·안정 ID·전체 전처리 미완료 |
| 02 대시보드 | 기존 부분 구현 / 검증 필요 | 기간·대상군 혼합 합계와 지역별 신청집계 일관성 확인 필요 |
| 03 프로그램 | 기존 부분 구현 / 검증 필요 | 전체 적재, PROGRM_TY_NM 매핑, 단위별 정렬, 필터, 페이지, 시설 연계 필요 |
| 04 시설 | 기존 부분 구현 / 검증 필요 | 안정 ID·중복 제거·장애인 자료 연결·강좌 연결·페이지 필요 |
| 05 엑셀·지도 | 미완료 | 기존 CSV 방식. XLSX 전체 조회조건 일치, 행 보호한도, 행정경계 자산 필요 |
| 06 최종 검수 | 미완료 | 브라우저·XLSX·전체 기능 인수 테스트는 단계 개발 후 수행 |

## 변경 파일

- `main/main/urls.py`: 루트 리다이렉트.
- `main/templates/base.html`, `components/source_status.html`: 공통 메뉴·본문 바로가기·자료 상태.
- `main/templates/dashboard.html`: 불필요한 닫는 태그 제거.
- `main/templates/programs.html`: 표 스크롤 영역의 키보드 포커스·접근성 이름.
- `main/static/app.css`, `shell.css`, `sport-insight-colors.css`: 반응형 문법 수정, 시스템 폰트, 토큰 적용, 공통 UI 크기·상태·포커스.
- `app/tests.py`: 루트·메뉴·활성 상태·본문 포커스 타깃·자료 안내·표 접근성 테스트 추가.
- `scripts/inspect_sources.py`, `docs/source-inventory.json`: 전체 CSV의 구조 메타데이터 점검.
- `README.md`, `docs/DECISIONS.md`, 이 파일: 실행 및 검증 기록.
- `_handoff/sport-insight-dev-handoff/*`: 사용자 ZIP 원문 추출. 기존 자료와 별도 보존.

## 실행 및 결과

| 명령 / 확인 | 결과 |
|---|---|
| `config/Scripts/python.exe main/manage.py check` | 문제 없음 |
| `config/Scripts/python.exe main/manage.py test app -v 2` | 9개 통과: 기존 계산 6개 + 신규 공통 화면 3개 |
| `config/Scripts/python.exe -m compileall -q app main/main scripts` | 성공 |
| Django Client의 실제 데이터 요청 `/`, `/dashboard`, `/programs`, `/facilities` | 각각 302, 200, 200, 200 |
| `config/Scripts/python.exe scripts/inspect_sources.py` | 최종 성공, 11파일. 최초 엄격 파서 오류를 확인하고 오류 메타데이터 보존 방식으로 보완 |
| Git status/diff | git 실행 파일이 PATH에 없고 루트에 .git도 없음. 변경 전 소스를 직접 확인 |
| TypeScript 검사·프런트 빌드 | 해당 스택·설정 없음. Django 검사와 Python 컴파일 수행 |
| 브라우저 E2E·1440/1280/좁은 화면 캡처·실제 키보드 포커스 | 미실행: CUA 브라우저 연결 결과 `No browser is available`. 렌더링 테스트는 브라우저 검증을 대체하지 않음 |

## 데이터 확인 결과

모든 CSV를 UTF-8-SIG 파서로 읽음. 헤더·체크섬·행 수는 `source-inventory.json` 참조. 공공 프로그램 파일과 체육생활이용정보 파일이 바이트 단위 동일함. 엄격 따옴표 오류 4파일, 열 수 불일치는 강좌 데이터 3행 및 청소년·유아동 프로그램 266행. 원본은 변경하지 않음. 출처·가격 단위·기간·시설 crosswalk는 검증되지 않음.

다음 단계는 `prompts/01-data-layer.md`의 데이터 계약·전처리·계산 검증이다. 이번 시작 프롬프트의 범위를 넘어 전체 MVP를 구현하지 않았으며 커밋·푸시·배포하지 않았다.
