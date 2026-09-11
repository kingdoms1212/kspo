# Codex 시작 프롬프트

이 저장소의 SPORT INSIGHT MVP를 개발해줘.

먼저 프로젝트의 `AGENTS.md`와 적용 중인 기존 지침을 읽고,
현재 코드, git status/diff, package.json, lockfile, 실행 가능한 명령을 확인해.
기존 지침·사용자 변경·기술스택을 덮어쓰지 마.

다음 파일을 읽어:
- docs/00-scope.md
- docs/01-screen-spec.md
- docs/02-data-contract.md
- docs/03-calculation-export-map.md
- docs/WORK-STATUS.md

design/final-ui-reference.png는 세 화면의 배치 참고야.
콜라주 전체를 한 페이지로 만들지 말고, 표시값·라벨·기능은 명세를 우선해.
design/sport-insight-colors.css의 기존 색상 변수를 유지해.

이번 작업은 prompts/00-bootstrap.md 범위만 구현해.
그 단계가 이미 완료돼 있으면 재생성하지 말고 현재 상태와 검증 결과를 보고해.
다음 단계를 임의로 구현하지 마.

메뉴는 대시보드 / 프로그램 분석 / 시설 현황의 세 개만 만든다.
프로그램 추천은 실제 등록 강좌의 조건 필터링·명시적 정렬·상위 3개야.
제품에는 AI API, 추천 근거 생성, AI 인사이트, 추천 점수, 정책효과 예측을 넣지 마.
별도 보고서 메뉴는 만들지 않고 각 화면·차트·표의 XLSX 내보내기로 통일해.

원본 데이터와 대한민국 행정경계 GeoJSON은 이 패키지에 없어.
없는 자료는 실제 연결 완료로 보고하지 말고, 시연/실제 모드와 미연결 상태를 구분해.
실데이터의 수치·가격·사진·좌표를 추정해서 채우지 마.

수정 범위를 짧게 알린 후 실제 파일을 수정하고 가능한 검증을 수행해.
완료 후 변경 파일, 실행한 명령과 결과, 미실행 테스트, 남은 데이터 의존성을 보고하고
docs/WORK-STATUS.md를 갱신해.
커밋·푸시·배포·권한 우회는 하지 마.
