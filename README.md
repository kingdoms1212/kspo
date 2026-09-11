# SPORT INSIGHT

공공기관 체육복지 담당자를 위한 Django 기반 조회 화면입니다. 최초 공통 레이아웃 구현 후, 사용자 요청에 따라 **시안 기준으로 세 화면을 전면 재구성**했습니다. 대시보드 3열, 프로그램 좌측 검색·우측 결과, 시설 목록표·상세 패널로 구성합니다. [디자인 검토 및 변경 내용](docs/DESIGN-REVIEW.md)을 참고하세요. 데이터 처리와 XLSX·지도 기능은 아직 전체 명세를 충족하지 않습니다.

## 실행

PowerShell에서 `C:\kspo`를 작업 디렉터리로 사용합니다. 기존 `config` 가상환경의 Python과 Django 6.1.1을 유지했으며 추가 패키지를 설치하지 않았습니다.

```powershell
.\config\Scripts\python.exe main/manage.py runserver 127.0.0.1:8000
```

브라우저에서 <http://127.0.0.1:8000/>에 접속합니다. `/`는 `/dashboard`로 이동하며, 메뉴는 `/dashboard`, `/programs`, `/facilities` 세 개입니다.

## 검증 명령

```powershell
.\config\Scripts\python.exe main/manage.py check
.\config\Scripts\python.exe main/manage.py test app -v 2
.\config\Scripts\python.exe -m compileall -q app main/main scripts
.\config\Scripts\python.exe scripts/inspect_sources.py
```

단위·렌더링 테스트 12개를 통과했습니다. 실제 CSV를 사용하는 Django Client에서도 세 화면, 프로그램 2페이지, 시설 상세 및 시설 2페이지에서 200을 확인했습니다. 루트 302도 회귀 테스트합니다. 별도의 TypeScript 검사·프런트 빌드 설정은 없습니다.

수동 검증: 1440×900, 1280×800, 좁은 화면에서 세 메뉴 이동, 현재 메뉴 표시, Tab으로 본문 바로가기 → 메뉴 → 자료 안내 → 필터 순서 이동, Enter로 조회, 비교표의 가로 스크롤을 확인합니다. 이번 환경에서는 연결 가능한 브라우저가 없어 실제 화면 캡처·포커스 이동·뷰포트 검증은 미실행입니다.

## 데이터 상태

CSV 11개의 전체 파일을 읽어 체크섬·헤더·파서 기준 행 수·열 수 불일치를 [source-inventory.json](docs/source-inventory.json)에 기록했습니다. 기록에는 개인 이름이나 개별 원본 레코드를 포함하지 않았습니다. 이는 파일 구조 점검이며, 통계 정의·중복·단위·출처 검증 완료를 의미하지 않습니다.

- `공공체육시설 프로그램 정보.csv`와 `체육생활이용정보.csv`는 SHA-256까지 동일합니다. 공공 프로그램 자료로 연결하기 전에 원본 확인이 필요합니다.
- 네 파일에서 엄격한 CSV 따옴표 파싱 오류가 발견됐습니다. 해당 파일의 행 수는 기존 로더와 같은 관대한 파서 기준입니다.
- 이용시설 강좌 데이터 3행, 청소년·유아동 프로그램 정보 266행에서 헤더와 열 수가 다릅니다.
- 현재 프로그램은 최대 15,000행, 이용현황은 최대 50,000행만 읽습니다. 전체 자료 조회가 아닙니다.
- 현재 화면은 실제 자료 모드이며 시연 데이터 생성이나 누락값 대체가 없습니다. 별도 demo provider는 미구현입니다.
- 시설 연계·가격 단위·기간별 통계·행정경계 지도·XLSX는 다음 단계 검증/개발 대상입니다. 기존 CSV 다운로드는 XLSX 명세 완료로 취급하지 않습니다.

[작업 상태](docs/WORK-STATUS.md)와 [결정 기록](docs/DECISIONS.md)을 참고하세요. 원본 압축파일은 `_handoff/sport-insight-dev-handoff`에 별도로 풀었으며 기존 `_prompt`, `data`, 가상환경을 보존했습니다.
