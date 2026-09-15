# 현재 프로젝트 구조 · 2026-09-15 확인

- `config/`: Python 가상환경.
- `data/`: 조회에 사용하는 원본 데이터.
- `main/main/`: Django 설정 및 최상위 URL.
- `main/app/dashboard`, `programs`, `facilities`: 기능별 models/services/views/urls/tests. 시설 모듈은 transit.py로 교통 연결을 분리한다.
- `main/app/policies`: 체육정책 화면·팝업.
- `main/app/common`: 데이터 처리, 엑셀, 계산, 크롤링, HTMX 부분 렌더링, 정적 경로 처리.
- `main/templates/`: base.html 공통 틀과 기능별 전체/부분 템플릿. React 빌드 없이 Django + HTMX로 렌더링한다.
- `main/static/`: 화면 CSS, 지도·상호작용 JavaScript, HTMX.
- `fonts/`: NotoSansKR TTF 9개 굵기(100–900). `main/static/fonts.css`에서 선언한다.
- `theme/`: `sport-insight-colors.css`를 전체 화면의 단일 색상 원본으로 사용한다.
- `image/`: 화면 이미지.
- `scripts/`: 데이터 점검 스크립트.
- `docs/`: 결정·작업 상태·구조 문서.

## 폰트와 색상 적용

공통 base.html은 theme/sport-insight-colors.css → fonts.css → app.css 순서로 로드한다.
본문·입력 요소·정책 팝업에 Noto Sans KR을 상속하며 지도 캔버스의 글꼴도 동일하게 지정한다.
지도는 폰트 로드 후 그려지고, 지도 색·툴팁·범례는 CSS 토큰을 읽는다.

`STATICFILES_DIRS`는 fonts, theme, image를 접두사로 제공한다. Windows에서도 URL 슬래시를
정상 처리하도록 common/staticfiles.py가 FileSystemFinder의 경로 구분자를 정규화한다.
배포 시에도 Django collectstatic의 표준 수집 방식을 그대로 사용한다.

기존 `main/static/sport-insight-colors.css`는 호환용 import만 포함한다. 실제 색상 변경은
루트 `theme/sport-insight-colors.css`에서 한다. 폰트 파일과 팔레트를 복제하지 않는다.
