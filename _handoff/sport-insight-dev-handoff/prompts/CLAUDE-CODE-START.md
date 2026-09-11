# Claude Code 시작 프롬프트
이 저장소의 SPORT INSIGHT MVP를 개발해줘.

먼저 CLAUDE.md와 여기서 가져오는 AGENTS.md를 읽어.
기존 지침이 있다면 덮어쓰지 말고 유지해.
docs/00-scope.md부터 03-calculation-export-map.md까지 읽고 현재 코드,
package.json, lockfile, git diff를 확인해.

이번에는 prompts/00-bootstrap.md의 범위만 구현해.
메뉴는 대시보드 / 프로그램 분석 / 시설 현황의 세 개이고,
프로그램 추천은 실제 강좌의 필터링·정렬 결과야.
Claude API나 다른 AI 기능을 제품에 넣지 마.
보고서는 없고 각 화면·표·차트의 XLSX 내보내기만 구현할 예정이야.

수정 범위를 짧게 제시하고 실제 구현 후 가능한 타입 검사·테스트·빌드를 실행해.
작업 종료 시 변경 파일, 검증 결과, 다음 단계 의존성만 명확히 보고해.
이 단계 밖의 기능 추가나 배포는 하지 마.
