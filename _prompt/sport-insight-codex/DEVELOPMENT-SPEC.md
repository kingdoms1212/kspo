# SPORT INSIGHT — Codex 전용 개발 명세 및 프롬프트

버전: 1.1 / 분리일: 2026-09-11

세 화면의 기존 제품 명세는 유지하고 개발 지침·프롬프트를 Codex 단독 사용용으로 분리했다.
이 파일은 열람용 통합본이다. 실제 개발은 같은 이름의 ZIP 내부 상대 경로를 유지해 사용한다.
별도 도구의 지침 파일을 가져오지 않고 `AGENTS.md`만으로 프로젝트 규칙을 제공한다.
실제 앱 코드, 원본 데이터, 행정경계 GeoJSON, 개발 실행 결과는 포함하지 않는다.


---

## 원본 경로: `AGENTS.md`

# SPORT INSIGHT — Codex 프로젝트 개발 지침
## 제품과 범위
공공기관 체육복지 담당자용 B2G 서비스다.
메뉴/라우트는 대시보드 `/dashboard`, 프로그램 분석 `/programs`, 시설 현황 `/facilities`만 구현한다.
별도 보고서·AI·공지사항·설정·회원가입·결제·예약 기능은 이번 범위가 아니다.

## 먼저 읽을 문서
1. `docs/00-scope.md`
2. `docs/01-screen-spec.md`
3. `docs/02-data-contract.md`
4. `docs/03-calculation-export-map.md`
작업에 맞는 `prompts/` 문서와 `docs/04-acceptance-tests.md`도 읽는다.
`contracts/domain.ts`는 내부 계약 초안이지 원천 CSV 헤더가 아니다.
명세와 이미지가 충돌하면 명세를 따른다.

## 데이터 진실성
- LLM/API 호출, 추천 이유 생성, AI 점수, 수혜자 증가 예측, 정책효율 예측을 구현하지 않는다.
- 추천은 조건 필터링 + 명시적인 정렬 + 상위 3개다. 강좌명·주소·수치를 생성하지 않는다.
- 신청인원 합계는 고유 이용자 수가 아니다. 월별 합계로 연간 실인원을 만들지 않는다.
- 수혜율은 같은 기간·지역·대상 정의가 확인된 수급인원/대상인원으로만 계산한다.
- 교통 정보는 시설↔정류장 구간이다. 거주지 출발시간·환승·무장애 접근성을 추정하지 않는다.
- 수강료의 월/회/전체과정 및 1인/단체 단위 확인 전 예산 계산을 하지 않는다.
- “등록시설”을 “확대 운영 가능 시설”로, “모집인원”을 “잔여석”으로 바꾸지 않는다.
- 가맹 데이터에 안 나온 시설은 확인 필요다. 자동으로 이용 불가로 처리하지 않는다.
- 사진·시설 운영시간은 확인된 자료가 있을 때만 표시한다.
- `null`과 0을 구분한다. 결측을 0으로 채우거나 실제 데이터 부족을 mock으로 보충하지 않는다.
- demo/real 모드를 분리하고 모든 demo 화면·내보내기에 시연 표시를 유지한다.

## 구현 방식
기존 저장소의 프레임워크·패키지 매니저·lockfile을 우선 존중한다.
신규 프로젝트 기본안은 React + TypeScript + Vite, Apache ECharts, ExcelJS다.
기존 라이브러리가 같은 기능을 제공하면 중복 설치하지 않는다.
새 버전 번호를 추측하지 말고 설치 시 공식 문서·호환성·lockfile을 확인한다.
기존 `design/sport-insight-colors.css`의 `--si-*` 변수를 재사용한다.
도메인 계산과 데이터 조회를 UI에서 분리한다. 모든 화면/엑셀은 같은 조회 결과를 사용한다.
실제 데이터가 없으면 demo provider와 검증 오류를 반환하는 real provider 경계를 만든다.

## 작업 안전성과 검수
현재 파일·git diff·실행 명령을 먼저 확인한다. 기존 변경을 덮어쓰지 않는다.
키·자격증명·개인정보를 소스나 로그에 넣지 않는다. 공개 스냅샷은 공개 가능한 데이터만 포함한다.
외부 텍스트는 HTML/코드/수식으로 해석하지 않는다.
코드 수정 후 타입 검사·단위 테스트·빌드를 실행한다. 가능한 경우 E2E도 실행한다.
미실행 테스트는 이유와 함께 미실행으로 보고한다. 통과했다고 추측하지 않는다.
응답에는 변경 파일, 구현 내용, 테스트 결과, 남은 데이터 의존성을 남긴다.
스키마나 동작 변경은 `docs/DECISIONS.md`에 기록하고 관련 테스트를 갱신한다.
명세 밖 기능, 자동 배포, git push는 승인 없이 하지 않는다.

## 이 패키지의 실행 규칙
이 파일 `AGENTS.md`에 제품 공통 규칙을 모두 담았다. 별도 에이전트 지침 import는 필요하지 않다.
실행할 작업은 `prompts/START.md` 또는 사용자가 지정한 단계 프롬프트를 따른다.
각 단계의 상세 문서는 필요할 때 직접 읽는다. 모든 명세를 이 파일에 자동으로 포함하지 않는다.
작업 시작 시 적용 중인 프로젝트 지침과 기존 변경을 확인하고, 기존 지침을 삭제하거나 교체하지 않는다.
한 번에는 지정한 한 단계만 구현한다. 이미 구현된 부분은 검토하고 필요한 변경만 한다.
새 세션에서는 `docs/WORK-STATUS.md`와 실제 코드·테스트를 대조한 뒤 진행한다.
작업 후 `docs/WORK-STATUS.md`에 변경 파일·실행 명령·검증 결과·미해결 의존성을 기록한다.
환경·네트워크·권한 제한이 있으면 우회하지 않고 실제로 못한 작업을 구분한다.
명세서에 적힌 라이브러리 선택은 제안이다. 이미 같은 기능이 있으면 기존 구현을 재사용한다.
개발 지침은 작업 기준이며 보안·권한을 기술적으로 강제하는 설정을 대신하지 않는다.
코드 커밋·푸시·배포와 명세 밖의 추가 개발은 별도 요청 없이 실행하지 않는다.
최종 보고는 한국어로 간결하게 작성하고 실제 검증 증거를 남긴다.

---

## 원본 경로: `docs/00-scope.md`

# 00. 구현 범위와 작업 기준
## 1. 목표
담당자가 지역별 체육복지 현황을 살피고, 실제 등록 프로그램을 조건별로 비교하며,
시설·강좌 목록과 통계표를 엑셀로 내보낼 수 있는 읽기 중심 MVP를 만든다.

상위 흐름은 `현황 조회 → 조건별 프로그램 비교 → 시설 상세 확인 → 엑셀 내보내기`다.
프로그램은 시민 개인에게 운동을 처방하는 기능이 아니라 정책 검토용 후보 검색이다.

## 2. 메뉴 및 라우트
| ID | 메뉴 | URL | 구성 |
|---|---|---|---|
| DASH | 대시보드 | /dashboard | 지표 카드·대한민국 지도·지역별 막대차트·종목별 차트 |
| PROG | 프로그램 분석 | /programs | 왼쪽 조건 폼·상위 3개 카드·전체 비교표·시설 분포 |
| FAC | 시설 현황 | /facilities | 상단 필터·시설 목록·우측 시설 상세·등록 강좌표 |
`/`은 `/dashboard`로 이동한다. 지역 상세를 별도 메뉴로 추가하지 않는다.
시설 상세도 별도 라우트 대신 같은 화면의 패널로 구성한다.
공지사항·설정·정책 보고서·사용자 관리 메뉴는 숨긴다.

## 3. 디자인
참조: `design/final-ui-reference.png`, `design/sport-insight-colors.css`.
이미지는 3개 화면을 한 장에 배치한 콜라주이며, 콜라주 전체를 한 페이지에 구현하는 것이 아니다.
대시보드 배치와 프로그램 카드형·시설 목록/상세형 배치는 유지한다.
본문은 한국어, 통화는 원, 기본 시간대는 Asia/Seoul이다.
화면은 데스크톱 우선 1440px 기준이며 1280px에서도 주요 기능을 사용할 수 있게 한다.
사이드바 약 208px, 헤더 약 64px, 콘텐츠 여백 24px, 카드 간격 16px를 기본 제안으로 쓴다.
좁은 화면은 프로그램 조건 폼을 위로, 시설 상세를 목록 아래로 배치한다.
이 치수는 제안값이며 기존 디자인 시스템과 충돌하면 일관성을 우선한다.
기본 시스템 폰트를 사용하고 폰트 파일을 번들에 추가하지 않는다.

## 4. 확정 구현 / 조건부 구현 / 제외
| 구분 | 항목 |
|---|---|
| 확정 | 3개 메뉴, 조건 검색, 명시적 정렬, 상위 3개 카드, 목록/상세, 통계 집계, XLSX |
| 데이터 검증 후 | 수혜율, 월·1인 가격 평균, 예산 검토, 전년 비교, 모집인원, 시설 좌표, 시설↔정류장 도보 |
| 별도 자산 필요 | 출처·이용조건·코드체계·기준연도를 확인한 국내 행정경계 GeoJSON |
| 제외 | AI 인사이트/추천 근거/추천 점수, 정책효과 예측, 예산 최적 배분, 보고서 생성 |
| 제외 | 실시간 잔여석, 예약·결제, 시설 신규 사업 생성, 대중교통 경로탐색, 무장애 판정 |
| 제외 | 로그인·권한관리·공공기관 운영 배포·자동 수집 스케줄러 |

실제 기관 운영 서비스로 배포할 경우 보안·권한·접근기록·성능 등을 별도 설계해야 한다.
이번 범위의 정적 MVP 완성을 운영 서비스의 준비 완료로 표현하지 않는다.

## 5. 구현 제안
기존 프로젝트가 있으면 해당 스택을 유지한다.
신규일 때의 기본안:
- React + TypeScript + Vite: 화면과 명시적 상태 관리.
- Apache ECharts: 막대차트와 GeoJSON 지도 공통 렌더링 [T03].
- ExcelJS: 브라우저 XLSX 작성 [T04].
- 기존 테스트 도구 우선. 없으면 단위 테스트와 브라우저 E2E 도구를 작업 00에서 선정한다.

지도용 SDK·차트 라이브러리를 여러 개 도입하지 않는다.
ECharts 지도는 별도 GeoJSON이 필요하다. 라이브러리가 국내 경계를 자동 제공한다고 가정하지 않는다.
실제 도로 배경·위치 탐색이 필요해질 때만 Leaflet 등 별도 지도 기능을 검토한다 [T05].

## 6. 데이터 공급 방식
첫 단계는 검증·정규화한 정적 JSON 스냅샷을 읽는 구조로 한다.
이미 API/DB가 있으면 provider 어댑터만 바꾸며, UI가 원본 CSV 컬럼을 직접 읽지 않게 한다.
원본 파일은 담당자가 확보한다. 인증 우회나 프런트에서 외부 포털을 스크래핑하지 않는다.
원본을 받지 못하면 demo 모드로 동작 검증하고 실제 연결 완료라고 보고하지 않는다.

공통 컴포넌트 제안:
AppShell, FilterPanel, MetricCard, SectionCard, ChartPanel, DataTable,
ExportButton, SourceMeta, EmptyState, ErrorState, FacilityDetailPanel.

## 7. 구현 순서
00 저장소 점검·공통 레이아웃 → 01 데이터 계약/계산 함수 → 02 대시보드 →
03 프로그램 분석 → 04 시설 현황 → 05 엑셀·지도 통합 → 06 최종 검수.

공통 데이터 계약은 단계 01 완료 후 기준을 고정한다.
지도 자산이 없더라도 지역 선택/표/통계는 개발할 수 있지만 지도 항목 자체는 미완료로 기록한다.

---

## 원본 경로: `docs/01-screen-spec.md`

# 01. 화면별 기능 명세
규칙 참조: `02-data-contract.md`, `03-calculation-export-map.md`.
숫자·가격·시설명은 실제 조회 결과에서만 렌더링한다. 이미지 속 수치를 하드코딩하지 않는다.

## A. 공통 화면 — COM
| ID | 요소 | 동작 및 완료 조건 |
|---|---|---|
| COM-01 | 헤더·사이드바 | SPORT INSIGHT, 3개 메뉴, 활성 메뉴 표시. 별도 보고서/AI/공지/설정 메뉴 없음 |
| COM-02 | 조회 기준 | 자료 기준시점·대상 데이터 범위·demo 여부를 표시. 포털 업데이트일과 통계 기준일을 구분 |
| COM-03 | 필터 상태 | draft 입력과 applied 조회조건 분리. 조회 클릭 후 표·카드·지도·엑셀에 같은 조건 적용 |
| COM-04 | 초기화 | 폼·정렬·페이지·선택 시설을 정의된 기본값으로 복원. 이전 조건이 남지 않음 |
| COM-05 | 로딩·오류 | 영역별 로딩·재시도. 한 차트 실패로 전체 페이지가 사라지지 않음 |
| COM-06 | 데이터 없음 | 0건과 미제공 구분. 임의 추천·기본 시설·지난 결과로 대체하지 않음 |
| COM-07 | 내보내기 | XLSX, 검색 전체 결과 또는 현재 차트 집계값을 저장. 이미지·PDF·PPT 생성 안 함 |
| COM-08 | 접근성 | label 연결, 키보드 탐색, 포커스 표시, 정렬 aria-sort, 차트 대응표 제공 |
| COM-09 | 출처 안내 | 자료명·기준시점·단위·집계 방식 표시. 생성형 설명이 아니라 고정 메타데이터 |
| COM-10 | URL 연동 | 허용된 지역/스냅샷/선택시설만 query에 직렬화. 새로고침/뒤로가기에 조회 상태 복원 |

통계 카드와 프로그램·시설 카드의 기준시점이 다르면 카드마다 따로 표시한다.
서로 다른 자료를 한 연도의 동시 현황으로 보이게 하지 않는다.

## B. 대시보드 — DASH /dashboard
### 목적 및 배치
최종 시안의 `상단 4개 지표 → 왼쪽 지도 / 가운데 지역차트 / 오른쪽 종목차트·참고지표` 구조를 유지한다.
상단 제목은 전체일 때 “전국 체육복지 현황”, 선택 지역이 있으면 해당 지역을 반영한다.

### 구성 요소
| ID | 요소 | 입력/표시 | 동작·예외 |
|---|---|---|---|
| DASH-01 | 기준 자료·지역 필터 | 실제 사용 가능한 스냅샷/기준시점, 시도 | 없는 연도 생성 금지. 조회 후 공통 applied 조건 갱신 |
| DASH-02 | 지원대상 인원 카드 | 검증된 지역별 대상인원 | 대상 정의·기준일 확인 전 `확인 필요`. 장애인 대상 분모를 유청소년 자료로 대체 금지 |
| DASH-03 | 수급인원 카드 | 같은 정의의 실제 수급인원 | 시안의 “실제 이용자”를 “지원 수급인원”으로 수정. 강좌 신청합계와 구분 [D08,D09] |
| DASH-04 | 등록시설 수 카드 | 중복 제거·연계 확인된 시설 수 | 전국 전체 체육시설 수라고 표현하지 않고 대상 자료 범위를 표시 |
| DASH-05 | 등록 강좌 수 카드 | 기준 스냅샷의 고유 강좌 수 | 과거 월별 스냅샷 단순 합산 금지. 현재 운영 중이라고 단정 금지 |
| DASH-06 | 대한민국 지도 | 수혜율/수급인원/등록시설 수 중 검증된 지표 | 시도 색상, 호버 정보, 클릭 선택, 선택 해제. ECharts와 검증 GeoJSON 사용 |
| DASH-07 | 지역별 지원 현황 | 대상인원/수급인원/수혜율 탭 | 지표 전환, 내림차순, 긴 지역 목록 스크롤. 현재 필터의 하위지역 집계 |
| DASH-08 | 종목별 현황 | 신청인원 합계 상위 5 / 등록강좌 수 상위 5 | “수요 상위” 대신 관측값 명칭 사용. 단위가 다른 값을 같은 축에 혼합 금지 |
| DASH-09 | 정책 참고 지표 | 수혜율, 대상자 1천 명당 등록시설, 교통자료 보유시설 비율 | 계산 가능 항목만 표시. 수혜율은 전체 분자/분모 비율 |
| DASH-10 | 엑셀 내보내기 | 화면 전체 버튼 + 차트별 버튼 | 화면 전체는 적용 집계 데이터·조회조건·출처, 차트는 해당 차트의 집계 데이터 |
| DASH-11 | 프로그램 연결 | “선택 지역 프로그램 보기” | `/programs`로 지역을 전달. 자동 추천 생성 안 함 |

### 지도 연동 범위
MVP는 전국 시도 지도에서 시도를 선택하는 수준이다.
시군구 폴리곤 드릴다운, 도로 타일, 길찾기, 위치 권한은 범위에서 제외한다.
선택 시도 내부 시군구는 오른쪽 표/차트로 조회한다.
지도는 `전체 → 시도 선택 → 전체 보기` 동작을 제공한다.
데이터 없는 지역은 별도 회색이며 실제 0과 다르게 표현한다.
GeoJSON이 없으면 동일 공간에 지역 선택과 표를 제공하되 “지도 데이터 미연결”을 명시한다.

### 차트·지표 해석
강좌 이용현황의 “신청인원수”를 집계할 때 단위는 `신청인원 합계(중복 가능)`로 한다 [D07,D08].
체육생활이용정보만으로 지역 주민의 미충족 수요 인원을 생성하지 않는다 [D10].
전년 증감률 배지는 동일 정의·동일 기간의 두 시점이 확인될 때만 표시한다.
시설↔정류장 도보시간을 “국민 평균 접근 소요시간”으로 표시하지 않는다 [D11].

### 사용자 시나리오
전국 자료 조회 → 지도에서 시도 선택 → 카드/하위지역 차트 갱신 →
등록강좌 상위 종목 탭 전환 → 차트 엑셀 → 선택 지역 프로그램 분석으로 이동.

### 완료 기준
동일 applied 조건에서 화면 카드·차트·내보내기 값이 일치한다.
지도 클릭 없이도 지역 선택과 표로 같은 정보에 접근할 수 있다.
원본 결측·분모 0·미검증 지표가 0 또는 NaN으로 출력되지 않는다.

## C. 프로그램 분석 — PROG /programs
### 목적 및 배치
이전 시안의 왼쪽 조건 폼, 오른쪽 요약 카드와 상위 3개 카드,
하단 시설 분포와 전체 비교표를 유지한다.
제목은 “프로그램 분석”, 카드 영역은 “조건에 맞는 프로그램 TOP 3”로 한다.
TOP 3는 선택 정렬순 상위 3건이며 추천 확률/AI 순위가 아니다.

### 입력 폼
| ID | 필드 | 형식·기본값 | 검증 |
|---|---|---|---|
| PROG-01 | 자료 스냅샷 | 실제 파일의 기준시점 | 없는 미래 운영강좌를 생성하지 않음 |
| PROG-02 | 지역 | 시도, 시군구. 필수 시도 | 시도 변경 시 시군구 초기화. 행정코드 매핑 사용 |
| PROG-03 | 대상 | 확인된 대상 구분, 기본 전체 | 출처가 유아동·청소년 통합이면 임의로 세부 나이 분리 금지 |
| PROG-04 | 종목 | 복수 선택, 기본 전체 | 정규화된 종목 목록. 이름만 보고 유사 종목 자동 추정 금지 |
| PROG-05 | 이용권 구분 | 전체/스포츠/장애인 | 가입자 자격 판정이 아니라 자료상 가맹·강좌 구분 |
| PROG-06 | 요일·시간 | 선택 조건 | 비제공 행은 조건 확인 불가로 분리. 강좌 시간을 시설 영업시간으로 사용 금지 |
| PROG-07 | 강좌 기간 | 시작일/종료일, 선택 | 둘 다 입력 시 시작<=종료. 기간 교집합, 기간 미상은 엄격 필터에서 제외 |
| PROG-08 | 지원예산 B | 원 단위 정수, 선택 | 음수 금지, 단위 “원” 고정. 총 운영사업비가 아니라 수강료 지원예산 |
| PROG-09 | 계획인원 N | 양의 정수 | 예산 검토 활성 시 필수. 실제 확보/신규 수혜자 아님 |
| PROG-10 | 지원개월 M | 양의 정수 | 예산 검토 활성 시 필수. 원본 강좌기간과 별도 정책 가정 |
| PROG-11 | 정렬 기준 | 강좌명 / 월·1인 수강료 / 정류장 도보시간 | 기본 강좌명. 단위 미확인값·결측은 해당 정렬의 뒤쪽 |
| PROG-12 | 조회·초기화 | 버튼 | 조회 후 적용. 필터 조용한 자동 완화 금지. 예산 입력 오류면 기존 결과 조건 유지 안내 |

운영방식은 “기존 등록강좌 조회”로 고정하고 선택 컨트롤을 제거한다.
강좌 신설·시설 확충·종목 변경 같은 정책 생성 옵션은 만들지 않는다.

### 결과 영역
| ID | 요소 | 표시 | 동작·예외 |
|---|---|---|---|
| PROG-13 | 결과 요약 | 검색 강좌 수, 연결시설 수, 평균 월·1인 수강료, 교통자료 보유시설 수 | 현재 전체 적용 결과 기준. 가격/교통 커버리지 n/N 표기 |
| PROG-14 | TOP 3 카드 | 실제 강좌명, 시설명, 종목, 대상, 요일·시간, 수강료와 단위, 자료 기준일 | 정렬된 동일 결과의 앞 3건. 1~2건이면 그 개수만 표시 |
| PROG-15 | 사실 배지 | 스포츠이용권 등록, 장애인이용권 등록, 제공된 요일·종목 | “수요 높음/접근 우수/고효율/확대 가능” 등 해석 배지 삭제 |
| PROG-16 | 예산 검토 | N명×M개월 수강료, 예산 충족 여부, 산술상 지원가능 인원 | 단위 검증된 월·1인 가격만 계산. 결과는 효과 예측이 아님 |
| PROG-17 | 시설 분포 | 현재 결과에 연결된 시설 좌표 | 중복 마커 제거, 지도 표시 n/전체시설 N, 좌표 없으면 목록 유지 |
| PROG-18 | 전체 비교표 | 강좌명·시설·지역·종목·대상·요일·시간·가격·단위·예산 상태 | 기본 20건 페이지, 20/50 선택. 정렬과 페이지 이동 |
| PROG-19 | 시설 상세 이동 | 카드/표 시설명 링크 | `/facilities?facilityId=...`로 이동해 상세 선택 |
| PROG-20 | 엑셀 | 전체 적용 결과 버튼 | TOP 3만이 아니라 페이지 밖을 포함한 전체 검색결과. 순위와 계산 가정 포함 |

상위 3개 카드가 동일 예산의 독립 비교안이라는 문구를 표시한다.
세 카드를 동시에 운영하는 최적 배분안으로 표현하거나 지원가능 인원을 합산하지 않는다.
“기존 시설 6개를 즉시 활용 가능” 대신 “자료에 연결된 등록시설 6개”로 표현한다.
원본 사진이 없으면 동일한 시설 아이콘을 사용한다.

### 검색·예산 처리
예산을 입력하지 않으면 예산 필터를 적용하지 않는다.
B 입력 후 N/M 누락 시 검증 오류를 보여주며 예산이 적용됐다고 표시하지 않는다.
예산 검토가 활성화된 엄격 검색은 계산 가능하고 비용<=B인 강좌만 반환한다.
가격 단위 미확인/가격 결측으로 예산 판단 불가인 행 수를 별도로 안내한다.
계산식과 기준은 고정 도움말로 제공한다. 이는 금지한 “AI 추천 근거 생성”과 다르다.

### 완료 기준
지역·대상·기간·예산·정렬 변경이 실제 결과에 반영된다.
카드, 지도, 요약, 표, 엑셀의 모집단이 동일하다.
강좌 없음/가격 미확인/시설 미연계/좌표 미제공을 각기 구분한다.
어떤 API도 AI 설명·AI 점수 생성용으로 호출하지 않는다.

## D. 시설 현황 — FAC /facilities
### 목적 및 배치
이전 시안의 상단 검색 폼, 왼쪽 시설 목록, 오른쪽 시설 상세 및 등록강좌 표를 유지한다.
카드형 시설 사진은 검증된 사진이 있는 경우에만 사용한다.

| ID | 요소 | 표시·입력 | 동작·예외 |
|---|---|---|---|
| FAC-01 | 필터 | 스냅샷, 시도/시군구, 확인된 시설유형, 종목, 이용권 구분, 검색어 | 검색어는 시설명·주소 부분일치. 유형 미확인값은 기타로 임의 분류 금지 |
| FAC-02 | 검색·초기화 | 버튼, Enter | applied 조건에 반영. 검색 결과 변경 시 페이지 1로 |
| FAC-03 | 시설 목록 | 시설명, 지역, 주소, 주요종목, 연결 강좌 수, 자료상 이용권 등록 상태 | 기본 20행, 정렬·페이지. 숫자는 계산, 이미지 수치 복사 금지 |
| FAC-04 | 시설 선택 | 시설명 버튼/행 내부 링크 | 우측 상세 변경. 선택 시설이 결과에서 사라지면 선택 해제 |
| FAC-05 | 시설 상세 | 이름, 주소, 전화번호, 주요종목, 등록 구분, 기준일 | 시설 운영시간은 별도 원자료가 있을 때만. 강좌 시간으로 대체 금지 |
| FAC-06 | 사진 | 검증된 URL 또는 플레이스홀더 | 실패 시 플레이스홀더. 외부 검색 사진 자동 삽입 안 함 |
| FAC-07 | 등록 강좌표 | 실제 강좌명, 대상, 요일, 시작/종료시간, 금액/단위, 기간 | 선택 시설 + 선택 강좌 스냅샷에 해당하는 전체 강좌. 목록 종목필터와 상세 범위 차이를 라벨에 표시 |
| FAC-08 | 교통 정보 | 제공된 정류장/역명, 직선·도보거리, 도보시간 | 시설↔정류장으로 명시. 값 없는 항목은 미제공, 일반 경로탐색 아님 |
| FAC-09 | 시설 목록 엑셀 | 상단 목록 내보내기 | 적용 필터의 전체 시설 목록. 선택 시설만/현재 페이지만 내보내지 않음 |
| FAC-10 | 등록 강좌 엑셀 | 상세 표 내보내기 | 선택 시설의 표 대상 전체 강좌와 시설/출처/조회조건 포함 |
| FAC-11 | 프로그램 분석 이동 | 상세의 “이 시설 강좌 분석” | facilityId와 지역 전달. 별도 새 메뉴 생성 안 함 |

이용권은 `스포츠`, `장애인`을 별도 상태로 표시한다.
자료에서 미확인인 시설을 “이용 불가”로 단정하지 않는다.
장애인 이용권 등록을 경사로·엘리베이터 등 무장애 시설 인증으로 표시하지 않는다.
원본 모집인원이 제공되더라도 “모집인원(자료 기준)”으로 표시하며 잔여석으로 바꾸지 않는다.
연계 실패로 강좌가 없는 경우 `등록 강좌 연결 자료 없음`이며 `실제 운영 강좌 0개`로 단정하지 않는다.

### 직접 진입 및 완료 기준
시설 ID가 URL에 있으면 해당 기준자료에서 유효한지 확인한 뒤 상세를 연다.
존재하지 않는 ID면 오류 안내와 목록으로 돌아가기를 제공한다.
필터·선택·페이지·상세가 서로 꼬이지 않는다.
시설 목록과 강좌표의 엑셀 범위가 각각 명확하고 조회 시점과 일치한다.

---

## 원본 경로: `docs/02-data-contract.md`

# 02. 데이터 계약 및 원자료 연결 명세
## 1. 검증 수준
상품 설명은 확인했지만 원본 CSV/JSON, 전체 컬럼 정의서, 실제 결측·중복은 아직 검증하지 않았다.
정규화 필드는 프런트엔드/서비스 내부 계약이다. 원본 헤더를 추측해서 구현하지 않는다.
필드 매핑은 원본 확보 후 `source field → normalized field → unit → validation → source evidence`로 기록한다.

## 2. 데이터셋별 연결
URL과 공식 설명은 `05-source-register.md`를 참조한다.
| ID | 데이터 | 주 사용 화면 | 이번에 활용할 범위 및 제약 |
|---|---|---|---|
| D01 | 스포츠강좌이용권 시설 | PROG/FAC | 시설명·주소·전화·주종목. 좌표·사진·운영시간은 별도 확인 |
| D02 | 공공체육시설 프로그램 | PROG/FAC | 프로그램명·기간·요일·모집인원·가격. 모집인원≠잔여석 |
| D03 | 이용시설 강좌 | PROG/FAC | 강좌명·종목·금액·시간·요일. 금액의 월/회 단위는 추가 검증 |
| D04 | 장애인 이용권 강좌 | PROG/FAC | 장애인 이용권 강좌 조회. 세부 장애유형 적합성을 추정하지 않음 |
| D05 | 장애인 이용권 시설 | PROG/FAC | 시설 정보 연결. 좌표 등 실제 필드는 원본으로 확인 |
| D06 | 청소년·유아동 프로그램 | PROG/FAC | 대상 자료 범위 활용. 정확한 연령·개별 참가자 자격은 별도 확인 |
| D07 | 장애인 이용현황 | DASH | 강좌별 신청인원·기간 등 관측값. 고유 이용자 수 아님 |
| D08 | 이용권 이용현황 | DASH | 신청인원 합계·강좌연월. 월 합계를 연간 실인원으로 사용 금지 |
| D09 | 지역별 이용권 활용 | DASH | 대상인원·수급인원·지역인구·시설수. 동일 집계정의 확인 후 수혜율 |
| D10 | 체육생활이용정보 | DASH 보조 | 종목별 시설·인구 구조. 잠재수요 인원이나 신규사업 효과를 생성하지 않음 |
| D11 | 시설 인접 대중교통 | PROG/FAC/DASH 보조 | 750m 범위 시설↔교통시설, 거리 m·도보시간 sec. 결측 가능 |

D09의 유청소년 대상 정의를 장애인 이용권 수혜율의 분모로 사용하지 않는다.
D10의 주요 수요종목 구분은 지역별 미충족 인원을 직접 주는 것으로 해석하지 않는다.
D11은 시설 주변 교통시설 자료이지 주민 출발지 기반 접근시간 자료가 아니다.

## 3. 필수 manifest
모든 데이터 묶음에 다음을 둔다.
- datasetId, snapshotId, 자료명, sourceUrl, 원본 파일명/체크섬.
- portalUpdatedAt: 상품 페이지 갱신일.
- referencePeriod: 실제 통계/관측 기준기간. 확인되지 않으면 null.
- collectedAt: 프로젝트가 파일을 확보한 시각.
- geoCodeSystem, geoBoundaryYear, 집계 단위와 대상 정의.
- rowCount, 중복/결측/매칭실패 건수, 검증한 가격 단위.
- licenseNote, 검증 상태, 공개 가능 여부.
- fieldMappings: 원본 헤더와 내부 필드명 매핑.

포털의 업데이트 연도를 원자료 기준연도로 자동 사용하지 않는다.
자료마다 기준시점이 다른 경우 하나의 최신연도로 묶어 표시하지 않는다.
통계 인원 자료는 비교 가능한 스냅샷을 지정하고 시설·프로그램의 별도 스냅샷도 명시한다.

## 4. 내부 엔터티
구체적인 TypeScript 초안은 `contracts/domain.ts`에 있다.
| 엔터티 | 핵심 필드 | 필수 검증 |
|---|---|---|
| Region | id, level, parentId, sourceCodes | 행정코드체계와 연도. 이름만으로 서로 다른 코드체계 합치지 않음 |
| Facility | id, regionId, name, address, phone, sportCodes, voucherStatus, location | 시설 고유성, 정확한 연계, 좌표계. 사진·영업시간 nullable |
| Program | id, facilityId, regionId, name, sportCode, targetGroups, schedule, fee, recruitmentCapacity | 원본 강좌 보존, 시설 연계 여부, 가격 단위, 기간 |
| UsageRecord | programId/facilityId, regionId, period, applicationCount | 신청 집계 단위 및 중복 가능성 |
| RegionalCoverage | regionId, period, cohortKey, targetCount, beneficiaryCount | 상호배타 대상군 여부·분자분모 호환성 |
| TransitLink | facilityId, stopName, mode, distances, walkingSeconds | 시설↔정류장 구간, 미터/초, 중복·결측 |
| SourceRef | datasetId, snapshotId, rowKey | 화면/엑셀의 원자료 추적 |

시설·프로그램 ID는 원본 안정 ID가 있으면 우선 사용한다.
원본 ID가 없으면 출처별 stable surrogate key를 만든 뒤, 검증된 crosswalk로 통합한다.
매 실행마다 배열 index/임의 UUID로 ID를 바꾸지 않는다.

## 5. 병합·중복
### 시설
공통 ID → 사전 검증 crosswalk → 주소/이름의 명확한 일대일 일치 순으로만 연결한다.
주소·시설명 정규화는 공백·대소문자·명백한 포맷 차이만 처리한다.
동명시설, 지점, 다중 후보는 자동 연결하지 않고 ambiguous로 격리한다.
불확실한 fuzzy matching/LLM 매칭은 범위 밖이다.
일반·장애인 시설자료에 중복 등록된 시설은 검증된 경우에만 하나의 시설로 합친다.

### 프로그램
시설이 같고 이름이 같아도 요일·시간·기간이 다르면 다른 강좌일 수 있다.
D02와 D06의 중복은 crosswalk 또는 검증한 복합키로만 제거한다.
월별 동일 강좌 스냅샷은 현재 현황의 여러 강좌로 합산하지 않는다.
매칭 실패한 프로그램도 원본 강좌로 보존하고 시설 연결 미확인 상태를 표시한다.

### 지역통계
복지구분별 대상자가 중복될 수 있는지 먼저 확인한다.
상호배타성이 확인되지 않으면 구분별 행을 무조건 합산하지 않는다.
도 단위 행과 시군구 행을 함께 더하지 않는다.
전국 집계는 같은 계층·기간·대상 정의를 갖는 행만 사용한다.
지역별 누락은 전체 평균을 낮추는 0으로 보충하지 않는다.

## 6. 값 정규화
| 값 | 규칙 |
|---|---|
| 코드·전화 | 문자열. 선행 0과 + 보존 |
| 인원·금액 | 유효한 비음수 정수. null/빈 문자열/잘못된 단위 구분 |
| 날짜 | YYYY-MM-DD, 원본 날짜 해석 기록. 조회 범위와 기준일 구분 |
| 요일 | 월~일 배열. D03 WKDAY_NM, D04 POSBL_WKDAY_FLAG_CD의 7비트 예시는 출처 설명 확인 [D03,D04] |
| 가격 | amount + periodUnit + chargeBasis. 월/회/전체과정/미확인과 1인/단체/미확인을 별도 저장 |
| 좌표 | 유효한 좌표계·위경도 변환 확인. 없으면 null. 지역 중심점으로 대체 금지 |
| 시간 | HH:mm 또는 초 단위 구간시간. 시설 영업시간과 강좌시간 별개 |
| 가맹 | registered / not_registered / unknown. 명시적 반증 없이 not_registered 금지 |

“무료”가 명시되거나 0원이 확인되면 금액 0을 보존한다.
미제공 가격을 0원으로 바꾸지 않는다.
도보시간 0초가 실제 제공된 경우 결측으로 취급하지 않는다.

## 7. capabilities
provider는 각 기능에 available / partial / unavailable / unverified와 사유를 반환한다.
예: coverageRate, comparableYearOnYear, monthlyPerPersonFee, programPeriod,
facilityCoordinates, transitWalkingTime, facilityPhotos.
원본 검증 전에는 해당 capability를 available로 선언하지 않는다.
실제 데이터 모드에서 미검증 필드는 비활성/확인 필요로 표시한다.
시연 모드의 정상 테스트 데이터를 실제 모드의 누락값에 섞지 않는다.

## 8. provider 경계
DataProvider.load()는 manifests, regions, facilities, programs, usage,
coverage, transit 및 capabilities를 포함한 데이터 패키지를 반환한다.
한 조회 중에 참조 스냅샷이 바뀌지 않도록 view snapshot을 고정한다.
UI 컴포넌트는 원본 CSV 헤더나 외부 포털 주소를 직접 읽지 않는다.
대용량 원본의 변환·인코딩 변환·매핑은 오프라인 전처리 단계에서 수행한다.
UTF-8/CP949 여부, 따옴표와 쉼표가 포함된 CSV, 행 수 일치 검사를 원본 확보 시 추가한다.

---

## 원본 경로: `docs/03-calculation-export-map.md`

# 03. 계산·검색·엑셀·지도 규칙
이 문서의 산식은 제안한 애플리케이션 규칙이다.
정책효과 추정이나 실제 운영비 산정 모델이 아니다.

## 1. 지표 계산
### 1.1 수혜율
동일 기간·지역·대상 정의, 중복 제거, 분자/분모 호환성이 확인된 경우에만:
`수혜율 = 수급인원 / 지원대상 인원`
UI에서는 ×100 후 소수점 1자리 %로 표시한다.
엑셀에는 0~1 비율 값을 저장하고 `0.0%` 서식을 적용한다.

분모 0, 결측, 정의 미확인일 때 null과 사유를 반환한다.
시도/전국 수혜율은 `합계 수급인원 / 합계 대상인원`이다.
지역별 비율의 단순평균을 전국 수혜율로 쓰지 않는다.
예: A(대상100,수급50), B(대상900,수급90) → 140/1000=14.0%.
관측값이 100%를 초과하면 자르지 말고 정의·중복 검증 오류로 표시하고 정식 지표에서 제외한다.
일부 지역만 확인된 경우 집계 범위 n/N을 표시하며 전국 전체 값이라고 표현하지 않는다.

### 1.2 등록시설·등록강좌 수
동일 스냅샷과 필터에서 canonical ID 기준 중복 제거한 개수다.
미연계 원본을 임의의 새 시설로 합산하지 않는다.
완전히 적재된 자료에서 조회 0건이면 0, 적재 실패/범위 미확인이면 null이다.
시설별 프로그램 수는 연결된 프로그램의 개수이며 실제 총 운영강좌 수라고 단정하지 않는다.

### 1.3 종목별 신청인원 합계
동일 기간의 사용 가능한 신청인원 필드를 종목별 합계한다.
이 값은 신청 관측합계다. 동일인이 여러 강좌·여러 달에 포함될 수 있다 [D07,D08].
UI·엑셀 모두 `신청인원 합계(중복 가능)`라고 명시한다.
평균 수요/미충족 수요/향후 신청자 증가로 변환하지 않는다.

### 1.4 월·1인 수강료 평균
`fee.verified == true`, `periodUnit == month`, `chargeBasis == per_person`인 값만 사용한다.
현재 검색된 고유 강좌의 단순평균이며 값 확인 n/전체 N을 함께 표시한다.
월·회·전체과정·단체요금을 섞지 않는다.
가격 단위가 다르면 각 행의 원래 금액·단위를 보여주고 비교 불가로 둔다.

### 1.5 교통 정보
각 시설의 유효한 `walkingSeconds >= 0` 중 최솟값:
`nearestStopWalkingMinutes = min(walkingSeconds) / 60`
이는 제공된 시설 인접 교통시설 중 최소 관측 도보시간이다.
표시명은 `시설↔인접 정류장 도보시간(제공자료 최솟값)`으로 한다.
주민 집에서 시설까지의 시간이나 가장 빠른 전체 경로라고 표현하지 않는다 [D11].
교통자료 보유시설 비율은 `유효 도보시간 보유시설 수 / 현재 대상시설 수`.
주변 교통시설 자료 없음은 실제 교통시설 없음과 다르다.

### 1.6 전년 증감
동일 지표·기간 길이·집계대상·코드체계의 전년 값이 있을 때만:
`(현재값 - 전년값) / 전년값 × 100`
전년 값 0/미확인, 기간 불일치면 배지를 숨기고 비교 불가 사유를 제공한다.
수혜율 차이는 비율의 증감률과 구분하여 필요할 때 `%p`로 표시한다.

## 2. 프로그램 검색 파이프라인
1. 선택한 강좌 스냅샷과 유효한 필수 식별값을 가진 원본 강좌를 읽는다.
2. 지역 → facilityId(있는 경우) → 대상 → 종목 → 이용권 구분 → 요일/시간 → 기간 순으로 필터링한다.
3. 예산 검토 활성 시 아래 산식으로 계산 가능 여부·조건 충족 여부를 판정한다.
4. 선택 정렬을 적용하고 동률은 강좌명, programId 순으로 고정한다.
5. 전체 결과, 요약, 앞 3건, 시설 분포, 전체 표, export payload를 같은 결과로 생성한다.
6. 페이지는 전체 결과를 자른 뷰일 뿐이며 export를 제한하지 않는다.

요일 복수선택은 선택 요일과 강좌요일의 교집합이 하나 이상인 강좌를 포함한다.
시간 범위는 `강좌 시작>=선택 시작 AND 강좌 종료<=선택 종료`로 한다.
강좌 기간은 `강좌 시작<=조회 종료 AND 강좌 종료>=조회 시작`인 교집합 기준이다.
선택 조건에 필요한 원자료가 없으면 “조건 확인 불가”로 제외하고 제외 개수를 기록한다.
지정하지 않은 조건 때문에 결측 행을 자동 제외하지 않는다.
필터 결과가 없으면 조건을 조용히 완화하지 않는다.

### 정렬
- 강좌명순: 한국어 locale 정렬, 동률 programId.
- 수강료 낮은순: 검증된 월·1인 수강료 오름차순, 미확인/다른 단위 뒤쪽.
- 정류장 도보시간순: 유효 최솟값 오름차순, 미연계/미제공 뒤쪽.
- 임의 가중치·AI 점수·인기도 추정은 없다.

## 3. 예산 검토 — 수강료 지원 한정
입력:
- B: 담당자가 입력한 수강료 지원예산(원), 0 이상의 정수.
- N: 계획 지원인원, 1 이상의 정수.
- M: 계획 지원개월, 1 이상의 정수.
- P: 검증된 월·1인 수강료(원).

B가 비어 있으면 예산 검토를 하지 않는다.
B가 입력되면 N/M은 필수이며, 정수 범위와 곱셈 결과가 안전한 수인지 검증한다.
P의 단위가 미확인/회당/전체과정/단체 요금이면 계산하지 않는다.

산식:
```
계획 인원 수강료 소요액 = P × N × M
예산 조건 충족 = (P × N × M) <= B
산술상 지원가능 인원 = floor(B / (P × M))  # P > 0일 때만
```
P=0이 확인된 무료 강좌라면 소요액은 0이다.
이 경우 산술상 지원가능 인원은 null로 두고 “수강료 기준 예산 제한 없음 · 정원 별도 확인”이라고 표시한다.
무한대 또는 매우 큰 가짜 인원을 만들지 않는다.

검증 예:
B=30,000,000원, N=100명, M=6개월, P=50,000원/월·1인:
소요액 30,000,000원, 조건 충족, 산술상 지원가능 100명.
B가 29,999,999원이면 조건 불충족, 산술상 지원가능 99명.

이 계산은 수강료 전액을 계획기간 동안 지원한다는 **사용자 가정**이다.
현행 이용권 지원상한·지원자격·중복지원 여부를 자동 판단하는 기능이 아니다.
실제 사업비에는 별도 인건비·장소 대관·보험·홍보·장비·운영비 등이 있을 수 있으므로,
이 값을 “사업 총운영비”, “예산집행효율”, “추가 수혜자 예측”으로 표시하지 않는다.

### 예산 필터와 TOP 3
예산 검토 활성 시 비용 계산이 가능하고 예산 안에 드는 강좌만 기본 결과에 포함한다.
가격 미확인으로 예산 검토 불가한 행 수를 결과 위에 별도 안내한다.
세 카드는 각각 같은 B/N/M 조건을 가정한 **독립 비교안**이다.
세 카드 소요액/지원가능 인원을 합산해 동시 정책 편성안으로 제시하지 않는다.
모집인원이 있어도 잔여석·강사·운영 가능 여부가 확인된 것은 아니므로 “실제 수용가능 인원”은 계산하지 않는다.

## 4. XLSX 내보내기
브라우저 작성은 ExcelJS 문서형 workbook + `writeBuffer()`를 사용한다 [T04].
스트리밍 writer나 Node fs를 브라우저 코드에서 사용하지 않는다.
기존 저장소에 동등한 XLSX 기능이 있으면 기존 구현을 우선한다.

### 버튼별 범위
| 버튼 ID | 위치 | 내보낼 대상 |
|---|---|---|
| EXP-01 | 대시보드 상단 | 적용 지표 요약·지도/지역 집계·종목 집계·조회조건 |
| EXP-02 | 지역 차트 | 선택 지표의 차트 대상 전체 지역 행 |
| EXP-03 | 종목 차트 | 현재 차트에 표시한 상위 5개 집계 행. 순위 포함 |
| EXP-04 | 프로그램 비교표 | 모든 페이지의 전체 적용 프로그램 결과. TOP 3 여부와 순위 포함 |
| EXP-05 | 시설 목록 | 모든 페이지의 전체 적용 시설 목록 |
| EXP-06 | 시설 등록강좌표 | 현재 선택 시설의 표 범위에 해당하는 전체 강좌 |

### 워크북 공통
- 데이터 시트는 주제별로 분리한다. 반드시 `조회조건_출처` 시트를 추가한다.
- 조회조건, 정렬, 스냅샷, 원자료명/URL, 통계 기준일, 포털 갱신일, 내보낸 시각을 기록한다.
- demo 모드면 파일명 앞에 DEMO_와 모든 시트 상단에 “시연 데이터 · 실제 통계 아님”을 표시한다.
- 인원/금액은 숫자, 비율은 비율 숫자, 코드/전화/ID는 텍스트로 저장한다.
- 알 수 없는 숫자는 빈 셀이고 필요하면 별도 상태 열에 미제공/미검증 사유를 넣는다.
- 단위는 헤더에 명시한다. 혼합 단위 수강료는 금액과 단위 열을 분리한다.
- 예산 계산 열은 입력 B/N/M, 월·1인 P, 계산상태, 소요액, 산술상 지원가능 인원을 포함한다.
- 생성형 해석·추천 문장·사업효과 수치를 넣지 않는다.
- 표시 데이터의 집계수준과 달리 개인식별 원자료를 섞어 내보내지 않는다.

### 파일·보안·성능
파일명 예: `SPORT_INSIGHT_시설목록_경기도_20260911_143012.xlsx`.
운영체제에서 금지한 파일명 문자는 제거하고 시트명도 31자·금지문자 조건을 처리한다.
외부 문자열은 반드시 문자열 셀로 넣으며 `=`, `+`, `-`, `@`가 시작돼도 수식 객체로 바꾸지 않는다.
수식은 필요 없다. 계산은 애플리케이션에서 완료하고 결과값을 저장한다.
버튼 클릭 시 applied 결과를 고정하고 그 뒤 사용자가 필터를 바꿔도 내보내기 내용이 섞이지 않게 한다.
0행은 비활성 + 안내, 처리 중 중복 클릭 차단, 실패 시 재시도 제공.
임의로 첫 1,000행 등으로 잘라 저장하지 않는다.
MVP 기본 보호한도는 설정값 10,000행으로 제안한다. 초과 시 필터 축소를 안내하고 부분파일은 생성하지 않는다.
이 한도는 라이브러리의 고정 한계가 아니라 팀이 성능 검증 후 조정할 애플리케이션 정책이다.
통합 대시보드 내보내기는 전체 시트 행수·예상 메모리를 함께 검사한다.
Blob URL은 다운로드 시작 후 정리한다.

## 5. 대한민국 지도
### 권장 방식
MVP는 Apache ECharts의 `registerMap`으로 검증된 GeoJSON을 등록해 사용한다 [T03].
막대차트와 같은 라이브러리를 사용해 의존성을 줄이는 선택이다.
지도 라이브러리와 행정구역 경계 데이터는 별개다.
국내 경계 파일을 확보하지 못했으면 실제 지도가 연결된 것으로 보고하지 않는다.

### 자산 요구사항
`public/geo/korea-sido.geojson`은 팀이 다음을 확인한 뒤 추가한다.
- 원 제공기관·다운로드 위치·이용조건·귀속 표시·반출/캐시 조건.
- 실제 경계 기준연도와 통계/시설 지역코드의 대응.
- Polygon/MultiPolygon 형식과 좌표계 변환.
- 내부 regionId로 변환하는 코드 crosswalk.
- 명칭 변경·행정구역 개편 처리.
지역명을 문자열로 무조건 매칭하거나 SGIS/행정안전부 코드를 혼용하지 않는다.
파일을 단순화할 때 원본을 보관하고 경계 모양·인접 관계 검수를 한다.

### 동작
동일 통계시점의 전국 지도는 지역 선택용 문맥을 유지하고 선택 지역을 강조한다.
지도 클릭은 selectedRegionId를 갱신하며 카드·지역차트를 해당 범위로 바꾼다.
지도 전체 데이터와 선택지역 상세 데이터의 범위 차이는 export 메타정보에도 명시한다.
호버: 지역명, 선택 지표, 단위, 자료 기준시점, 미제공 여부.
수혜율 구간: [0,10), [10,30), [30,50), [50,70), [70,100].
0은 최저 구간, null은 `--si-map-no-data`.
높은 수혜율의 진한 색은 높은 관측값을 의미하며 정책 취약도 색상으로 설명하지 않는다.
수/비율은 각기 별도 범례를 사용한다.
마우스에 의존하지 않고 지역 select·대응표로 같은 기능을 제공한다.

### 프로그램 시설 분포
검증된 시설 좌표가 있고 해당 지역 경계와 결합 가능한 경우 동일 geo 컴포넌트에 점을 표시한다.
도로 배경·출발지·길찾기는 넣지 않는다.
좌표 없는 시설은 표에 유지하고 지도 제외 n건을 표시한다.
경계 자산이 없으면 분포 영역을 시설 지역목록으로 대체한다. 가짜 지도·중심점 마커를 생성하지 않는다.

---

## 원본 경로: `docs/04-acceptance-tests.md`

# 04. 인수 테스트
테스트 데이터는 실제 공공통계와 분리된 고정 fixture를 사용한다.
단위 테스트는 순수 함수, 통합 테스트는 공통 selector, E2E는 화면·다운로드를 검증한다.
테스트 명령과 결과는 저장소의 실제 도구에 맞춰 기록한다.

## A. 데이터·집계
| ID | Given / When | Then |
|---|---|---|
| DATA-01 | 동일 시설이 일반·장애인 자료에 있고 검증 crosswalk가 있음 | 시설 1개, 이용권 상태는 별도 유지 |
| DATA-02 | 이름은 같고 주소가 다른 두 시설 | 서로 다른 시설로 유지 |
| DATA-03 | 이름/주소 매칭 후보가 여러 개 | ambiguous 처리, 임의 연계 없음 |
| DATA-04 | D02/D06에 같은 검증 강좌 중복 | 강좌 1개, 두 출처 추적 가능 |
| DATA-05 | 같은 이름이나 시간·기간이 다른 강좌 | 별개 강좌 유지 |
| DATA-06 | 가격 null, 실제 0원, 월5만원, 회1만원 | 0원만 무료, 단위 혼합 평균 없음 |
| DATA-07 | 수급50/대상100, 수급90/대상900 | 전체 수혜율 14.0%, 단순평균30% 아님 |
| DATA-08 | 분모0/null/기간 불일치/대상군 중복 미확인 | 수혜율 null+사유, NaN/Infinity 없음 |
| DATA-09 | 월별 신청 합계100·150 | 신청 합계250(중복 가능), 연간 실인원250으로 표시 금지 |
| DATA-10 | 포털 2026 갱신, 실제 통계 2024 | 통계 기준2024 표시, 기준기간 조작 없음 |
| DATA-11 | 유청소년 분모와 장애인 신청인원 | 장애인 수혜율 생성하지 않음 |
| DATA-12 | 미연계 시설/강좌 | 연계 미확인 보존, 실제 부존재로 단정하지 않음 |

## B. 예산·검색
| ID | Given / When | Then |
|---|---|---|
| PROG-T01 | B=30,000,000/N=100/M=6/P=50,000 월·1인 | 소요30,000,000, 충족, 산술지원100 |
| PROG-T02 | B=29,999,999, 나머지 동일 | 소요 동일, 불충족, 산술지원99 |
| PROG-T03 | B 입력, N/M 미입력 또는 N=0 | 입력 오류, 예산 적용됨 표시 없음 |
| PROG-T04 | P 단위 미상/회당/전체과정/단체 | 월·1인 계산하지 않음, 제외 개수 안내 |
| PROG-T05 | 확인된 무료 강좌 | 소요0, 지원가능 인원은 무한대 아닌 null+설명 |
| PROG-T06 | 기간 필터 적용, 기간 미상 강좌 | 조건 확인불가로 제외, 제외 수 표시 |
| PROG-T07 | 정렬 값 같은 프로그램 | 강좌명/ID 보조정렬로 재실행 결과 동일 |
| PROG-T08 | 결과2건 | 카드2개, 임의3번째 카드 없음 |
| PROG-T09 | 결과0건 | 빈 상태, 조건 자동완화/가짜 강좌 없음 |
| PROG-T10 | 예산 비교카드3개 | 독립비교 안내, 3건 지원인원 합산 없음 |
| PROG-T11 | 지역만 수정하고 조회하지 않음 | 기존 applied 결과·export 유지, 미적용 변경 안내 |
| PROG-T12 | 필터 결측 필드가 있지만 해당 필터는 미지정 | 그 사유만으로 행을 제외하지 않음 |

## C. 지도·시설
| ID | Given / When | Then |
|---|---|---|
| MAP-T01 | 지도 시도 클릭 | 지역 필터·카드·하위지역 차트 동기화 |
| MAP-T02 | GeoJSON 로딩 실패 | 지도 영역 안내/표 대체, 다른 기능 정상 |
| MAP-T03 | 통계0과null | 지도 최저색과결측색 구분 |
| MAP-T04 | 시설 좌표 일부 미제공 | 표 보존, 지도 n/N 표시, 중심점 대체 금지 |
| MAP-T05 | 지역코드 체계 불일치 | 무시/합치지 않고 매핑 오류 기록 |
| FAC-T01 | 시설 선택 | 이름·주소·연락처·강좌표가 해당 시설로 변경 |
| FAC-T02 | 필터변경으로 선택시설 제외 | 선택 해제, 이전 상세가 잘못 남지 않음 |
| FAC-T03 | 유효 facilityId 직접 진입 | 해당 시설 상세 열림 |
| FAC-T04 | 존재하지 않는 facilityId | 명확한 오류, 목록 복귀 |
| FAC-T05 | 사진/영업시간 없음 | 플레이스홀더/미제공, 외부사진·강좌시간 대체 없음 |
| FAC-T06 | 이용권 자료에 시설 미등장 | 확인 필요, 이용불가 자동 판정 없음 |
| FAC-T07 | 도보시간180초, 다른 link 결측 | 3.0분(시설↔정류장), 결측을0으로 사용하지 않음 |

## D. 엑셀
| ID | Given / When | Then |
|---|---|---|
| XLSX-T01 | 결과53건, 화면20건 | 내보내기53건 |
| XLSX-T02 | 지역·정렬 변경 후 적용 | 파일 데이터·순서·메타정보가 화면 applied 결과와 일치 |
| XLSX-T03 | 시설 목록 내보내기 | 필터된 전체 시설, 선택시설 강좌표와 혼동 없음 |
| XLSX-T04 | 시설 상세 강좌 내보내기 | 선택시설의 전체 표 대상 강좌 |
| XLSX-T05 | 031 전화, 001 코드, 비율0.182, 금액50000 | 텍스트 선행0 보존, 비율18.2%, 숫자형 금액 |
| XLSX-T06 | 외부 값 =HYPERLINK(...), +ABC, @ABC | 수식이 아닌 문자열 셀로 재읽힘 |
| XLSX-T07 | 내보내는 중 필터 변경 | 클릭 시점 데이터로 일관된 파일 |
| XLSX-T08 | 0건/처리 중/실패/한도 초과 | 비활성 또는 안내, 중복 생성/조용한 잘림 없음 |
| XLSX-T09 | demo 모드 | 파일명과 모든 시트에 시연 표시 |
| XLSX-T10 | 파일 생성 후 재읽기 | 시트명, 행수, 필드 타입, 조회조건/출처, 숫자 서식 검증 |

## E. 화면·범위·안전성
3개 메뉴만 표시되고 `/`, 새로고침, 뒤로가기가 정상 동작한다.
1440×900, 1280×800, 좁은 화면에서 필터/표/내보내기에 접근할 수 있다.
키보드로 필터·조회·정렬·시설선택·내보내기 동작이 가능하다.
차트 툴팁의 외부 문자열을 HTML로 직접 삽입하지 않는다.
AI API·LLM SDK·보고서 생성·가짜 효과 예측 코드가 포함되지 않는다.
실제 모드에서 demo provider로 조용히 fallback하지 않는다.
타입 검사/단위 테스트/빌드/E2E 실행 결과와 미실행 사유를 보고한다.

## F. 최종 완료 증거
- 화면3개 스크린샷: 실제 구현에서 캡처. 이 패키지의 디자인 이미지를 완료 캡처로 재사용하지 않는다.
- 대표 XLSX 파일을 생성·재읽기한 테스트 결과.
- 지도 자산 출처/이용조건/기준연도/코드매핑 기록 또는 미연결 상태.
- 실제 데이터 연결 상태와 아직 미검증인 필드·기능 목록.
- 변경 파일 목록, 실행한 명령, 실패/미실행 항목.

---

## 원본 경로: `docs/05-source-register.md`

# 05. 출처 및 확인 범위
기존 명세의 출처 확인일: 2026-09-11.
도구별 분리일: 2026-09-11. 도구의 지침 파일 안내만 이번 분리 작업에서 재확인했다.
아래 공공데이터·라이브러리 기록은 기존 패키지에서 유지했으며 원본 파일을 새로 검증한 것은 아니다.
아래 내용은 상품 설명 또는 공식 개발 문서의 확인 요약이다.
실제 원본 CSV/JSON과 전체 컬럼 정의서의 검증을 대신하지 않는다.
포털 페이지 갱신일은 원자료의 관측 기준일이 아니다.

## 공공데이터

### [D01] 스포츠강좌이용권 시설 데이터
`https://www.bigdata-culture.kr/bigdata/user/data_market/detail.do?id=98eb52c8-da31-462a-9c01-5b9cb2f9d077`

시설명·주소·전화번호·주종목 등 시설 조회 범위를 확인. 좌표·사진·운영시간의 실제 제공 여부는 원자료 검증 대상.

### [D02] 공공체육시설 프로그램 정보
`https://www.bigdata-culture.kr/bigdata/user/data_market/detail.do?id=c3b8fb69-307d-4ae7-ab42-d0314c89ef47`

프로그램명·시작/종료일·요일·모집인원·가격 설명을 확인. 모집인원은 현재 남은 좌석 수가 아니다.

### [D03] 스포츠강좌이용권 이용시설 강좌 데이터
`https://www.bigdata-culture.kr/bigdata/user/data_market/detail.do?id=4e1a59b2-c54b-42a5-9a75-b86bb33ce279`

강좌명·종목·금액·시작/종료시간·요일 설명을 확인. WKDAY_NM의 7비트 요일 예시가 제시되어 있다. 금액 단위는 추가 확인.

### [D04] 장애인스포츠강좌이용권 강좌 정보
`https://www.bigdata-culture.kr/bigdata/user/data_market/detail.do?id=3c0dffb0-2594-11eb-af9a-4b03f0a582d6`

강좌명·종목·금액·시간·요일 설명을 확인. POSBL_WKDAY_FLAG_CD의 요일 비트 예시를 확인. 무장애 판정 자료로 사용하지 않는다.

### [D05] 장애인스포츠강좌이용권시설정보
`https://www.bigdata-culture.kr/bigdata/user/data_market/detail.do?id=35f861b0-2594-11eb-af9a-4b03f0a582d6`

장애인 이용권 시설 데이터의 상품 페이지를 확인. 세부 필드·좌표 유효성은 실제 파일에서 검증한다.

### [D06] 청소년 유아동 이용가능 체육시설 프로그램 정보
`https://www.bigdata-culture.kr/bigdata/user/data_market/detail.do?id=cae91264-6bc2-49fc-b38f-7df7d00c1e89`

대상별 프로그램 상품 페이지를 확인. 개별 강좌의 정확한 연령 범위·기간·가격 단위는 원자료 매핑에서 확인한다.

### [D07] 장애인스포츠강좌이용권 이용현황 정보
`https://www.bigdata-culture.kr/bigdata/user/data_market/detail.do?id=a70e157b-0bef-4832-bf31-857f13420464`

시설·강좌·종목·강좌연월·시작/종료일·신청인원·가격 설명을 확인. 사용자가 처음 제공한 ID 끝의 Z를 제거한 페이지다.

### [D08] 스포츠강좌이용권 이용현황 정보
`https://www.bigdata-culture.kr/bigdata/user/data_market/detail.do?id=04e1e27f-51fc-4ad2-a87b-112ea3b868e5`

시설·강좌·기간·신청인원·가격 설명을 확인. 신청인원 합계와 고유 이용자 수를 구분한다.

### [D09] 지역별스포츠강좌이용권활용정보
`https://www.bigdata-culture.kr/bigdata/user/data_market/detail.do?id=5b30e290-2594-11eb-af9a-4b03f0a582d6`

시군구 인구·시설수·지원대상인원·실제 수급인원 설명을 확인. 중복·기준시점·대상 정의 검증 후 비율을 계산한다.

### [D10] 체육생활이용정보
`https://www.bigdata-culture.kr/bigdata/user/data_market/detail.do?id=25c4e3e0-2594-11eb-af9a-4b03f0a582d6`

주요 공공/민간 수요종목에 대한 인구·시설·인당시설·순위 설명을 확인. 미충족 수요 인원을 자동 산출할 근거로 사용하지 않는다.

### [D11] 스포츠강좌이용권시설 인접 대중교통 정보
`https://www.bigdata-culture.kr/bigdata/user/data_market/detail.do?id=914ac658-d64b-4fc9-add5-9773393bbe51`

시설 반경 750m의 교통시설, 직선/도보거리(m), 도보시간(sec) 설명을 확인. API 결과가 없을 경우 결측 가능하다고 명시되어 있다.

## 개발 도구·라이브러리

### [T01] OpenAI — Codex 프로젝트 지침
`https://developers.openai.com/codex/guides/agents-md`

공식 문서는 작업 전 AGENTS.md를 읽고 경로에 따라 프로젝트 지침을 구성하는 방식을 안내한다.
이 패키지는 저장소 루트 AGENTS.md에 필요한 프로젝트 규칙을 담아 독립 구성했다.
기존 지침·하위 경로 지침을 확인하고 임의로 덮어쓰지 않는다.

### [T03] Apache ECharts — API / registerMap
`https://echarts.apache.org/en/api.html`

GeoJSON/SVG 지도 등록 API. 국내 행정경계 파일 자체는 별도 준비하며 코드/이름 대응을 검증한다.

### [T04] ExcelJS — 공식 저장소 README
`https://github.com/exceljs/exceljs`

문서형 workbook의 XLSX 작성 및 브라우저 사용 설명. 브라우저에는 스트리밍 workbook writer가 포함되지 않는다고 안내한다.

### [T04-RAW] ExcelJS — README 원문
`https://raw.githubusercontent.com/exceljs/exceljs/master/README.md`

Browser, Writing XLSX, Value Types 항목 확인. writeBuffer()와 숫자/문자열 셀 타입 참고.

### [T05] Leaflet — GeoJSON 예제
`https://leafletjs.com/examples/geojson/`

GeoJSON 벡터·상호작용 공식 예제. MVP 필수 의존성이 아니라 향후 일반 지도 확장 시 검토 대안.

## 출처 활용 원칙
설계상 산식·상태·권장 스택·예산 처리·행수 제한은 이 프로젝트를 위한 제안이며 제공기관이 정한 공식 정책이 아니다.
법적 이용권 지원상한·지원 자격은 이 명세에서 확정하지 않는다.
지도 경계는 아직 확보하지 않았으며 사용 가능한 국내 경계 데이터의 이용조건 확인을 별도 완료해야 한다.
이번 확인에 없는 실제 수치, 시설 사진, 주소, 운영시간을 시안만 보고 구현하지 않는다.

---

## 원본 경로: `docs/DECISIONS.md`

# 결정 및 미확정 사항
## 확정
| 항목 | 결정 |
|---|---|
| 사용자 | 정부·지자체·공공기관 체육정책 담당자 |
| 메뉴 | 대시보드, 프로그램 분석, 시설 현황 |
| AI | 제품에는 없음. Codex는 개발 도구로만 사용 |
| 추천 | 실제 등록 강좌의 조건검색·명시적 정렬·상위3개 |
| 보고서 | 독립 메뉴 없음. 조회 결과 XLSX 내보내기 |
| 예산 | 검증된 월·1인 수강료를 이용한 독립 대안별 산술 계산 |
| 디자인 | 최종 이미지 배치 및 기존 CSS. 데이터 의미는 명세 우선 |
| 지도 | ECharts + 팀이 검증한 시도 GeoJSON, 없으면 대응표 fallback |
| 초기 데이터 | demo/real provider 분리. 원본 매핑 후 real 연결 |

## 아직 미확정 — 완료로 보고하지 말 것
| 항목 | 필요 조치 | 현재 상태 |
|---|---|---|
| 원본 CSV/JSON | 담당자 확보 및 이용조건 확인 | 미제공 |
| 실제 컬럼 정의서 | 필드·단위·키 매핑 | 설명 페이지 확인만 완료 |
| 월·1인 가격 | 원자료/정의서 검증 | 미확인 |
| 고유 수급인원 집계 | 대상군 중복·기간·분모 호환 확인 | 미확인 |
| 시설/강좌 중복 제거 | 원본 ID·crosswalk 검증 | 미확인 |
| 사진·영업시간 | 확인 자료 및 이용권한 | 미제공 |
| 국내 행정경계 GeoJSON | 출처·이용조건·좌표계·연도·코드 검증 | 미포함 |
| 실제 저장소 기술스택 | 첫 프롬프트에서 확인 | 미제공 |
| 운영기관 배포 요구 | 인증·권한·인프라·보안 검토 | MVP 밖 |

에이전트는 변경일, 이유, 영향 화면/테스트를 이 문서에 추가한다.
데이터가 미확정이라는 이유로 수치를 생성하거나 요구사항을 몰래 삭제하지 않는다.

## 도구별 분리 — 2026-09-11
- 패키지: Codex 단독 개발용.
- 지침 파일: AGENTS.md. 공통 규칙을 이 파일에 직접 포함한다.
- 화면·계산·엑셀·지도·데이터 계약·수용 테스트의 제품 범위는 기존 명세를 유지한다.
- 다른 개발 도구의 시작 프롬프트나 공유 지침 import를 요구하지 않는다.
- 이번 산출물은 명세·프롬프트 재구성이며 앱 코드 구현·테스트 통과를 의미하지 않는다.

---

## 원본 경로: `docs/WORK-STATUS.md`

# SPORT INSIGHT — Codex 작업 상태

패키지 버전: 1.1 / 분리일: 2026-09-11

이 표는 기록용 초기 템플릿이다. 현재 저장소의 구현 상태를 검사한 결과가 아니다.
개발 시작 시 기존 코드와 테스트를 확인한 뒤 실제 상태로 수정한다.
상태: 미확인 / 진행 중 / 완료 / 의존성 대기.
의존성이 남은 기능은 완료로 처리하지 않는다.

| 단계 | 작업 | 상태 | 변경 파일 | 검증 증거 | 남은 의존성 |
|---|---|---|---|---|---|
| 00 | 공통 레이아웃 | 미확인 | — | — | 시작 시 코드 확인 |
| 01 | 데이터 구조·계산 함수 | 미확인 | — | — | 시작 시 코드 확인 |
| 02 | 대시보드 | 미확인 | — | — | 시작 시 코드 확인 |
| 03 | 프로그램 분석 | 미확인 | — | — | 시작 시 코드 확인 |
| 04 | 시설 현황 | 미확인 | — | — | 시작 시 코드 확인 |
| 05 | 엑셀·지도 통합 | 미확인 | — | — | 시작 시 코드 확인 |
| 06 | 최종 검수 | 미확인 | — | — | 시작 시 코드 확인 |

## 단계별 실행 기록 양식
- 작업일 / 단계:
- 읽은 지침·명세:
- 변경 파일:
- 구현한 범위:
- 실행 명령:
- 결과: 통과 / 실패 / 미실행:
- 테스트 로그·실행 화면 위치:
- 미해결 데이터·지도·환경 의존성:
- 다음 단계에 전달할 사항:

## 계속 유지할 제약
메뉴는 3개, 제품 AI 기능 없음, 독립 보고서 없음, 전체 적용결과 XLSX 내보내기.
실데이터 원본·GeoJSON은 패키지에 없으며 실제 연결은 별도 검증 대상이다.

---

## 원본 경로: `design/README.md`

# 디자인 자산 적용 안내
- final-ui-reference.png: 사용자가 마지막으로 확인한 세 화면의 콜라주.
- sport-insight-colors.css: 기존에 제공한 개발용 색상 토큰.

시안의 위치·형태·색감은 유지하되, 표시 문구와 숫자 의미는 docs 명세를 우선한다.
콜라주는 세 라우트의 참고 이미지다. 통째로 화면 배경에 넣는 구현은 하지 않는다.
수치·날짜·사진·시설명·연락처는 검증된 실제 데이터로 대체하거나 시연 데이터라고 명시한다.

주요 라벨 수정:
- 실제 이용자 → 검증된 경우 지원 수급인원, 강좌 이용현황일 때 신청인원 합계.
- 수요 상위 → 신청인원 합계 상위.
- 운영 프로그램 수 → 자료 기준 등록 강좌 수.
- 활용 가능 시설 → 연결된 등록시설.
- 평균 접근시간 → 시설↔인접 정류장 도보시간 또는 교통자료 보유시설 비율.
- 수요 높음 / 접근성 우수 → 삭제.
- 추천 근거 / AI 인사이트 / 점수 / 효과예측 → 삭제.
- 공지사항 / 설정 / 보고서 → 메뉴에서 삭제.
- 시설 영업시간 / 실제 사진 → 원자료 확인 때만 표시.

브랜드명은 SPORT INSIGHT로 사용한다.
CSS는 KSPO 공식 CI 규정이 아니라 대화에서 제안한 개발용 팔레트다.
시안에 보이는 기관 로고를 공식 서비스 인증·승인 표시로 해석하지 않는다.
별도 승인된 로고 원본이 없으면 공식 로고를 새로 그려 넣지 않고 서비스명만 사용한다.
폰트 파일은 패키지에 포함하지 않는다.

---

## 내부 데이터 계약: `contracts/domain.ts`

```typescript
/**
 * SPORT INSIGHT internal domain contract DRAFT.
 * These names are NOT verified source CSV headers.
 * Map raw columns only after inspecting the actual files and definitions.
 * All counts and flags require the validations in docs/02-data-contract.md.
 */
export type DataMode = "demo" | "real";
export type Availability = "available" | "partial" | "unavailable" | "unverified";
export type Nullable<T> = T | null;

export interface ReferencePeriod {
  label: string;
  startDate: Nullable<string>; // YYYY-MM-DD
  endDate: Nullable<string>;   // YYYY-MM-DD
}

export interface SourceRef {
  datasetId: string;
  snapshotId: string;
  rowKey: string;
}

export interface FieldMapping {
  rawField: string;
  domainField: string;
  unit: Nullable<string>;
  verified: boolean;
  evidenceNote: string;
}

export interface DatasetManifest {
  datasetId: string;
  snapshotId: string;
  title: string;
  sourceUrl: string;
  sourceFileName: string;
  sourceChecksum: Nullable<string>;
  portalUpdatedAt: Nullable<string>;
  referencePeriod: Nullable<ReferencePeriod>;
  collectedAt: string;
  rowCount: number;
  geoCodeSystem: Nullable<string>;
  geoBoundaryYear: Nullable<number>;
  aggregationUnit: string;
  cohortDefinition: Nullable<string>;
  licenseNote: Nullable<string>;
  status: Availability;
  fieldMappings: FieldMapping[];
}

export interface Capability {
  status: Availability;
  reason: string;
  sourceDatasetIds: string[];
}

export interface DataCapabilities {
  coverageRate: Capability;
  comparableYearOnYear: Capability;
  monthlyPerPersonFee: Capability;
  programPeriod: Capability;
  facilityCoordinates: Capability;
  transitWalkingTime: Capability;
  facilityPhotos: Capability;
}

export interface Region {
  id: string; // canonical internal key, never infer code systems by length alone
  name: string;
  level: "country" | "sido" | "sigungu";
  parentId: Nullable<string>;
  sourceCodes: Array<{ system: string; code: string; year: Nullable<number> }>;
}

export type VoucherState = "registered" | "not_registered" | "unknown";

export interface VerifiedLocation {
  latitude: number;
  longitude: number;
  crs: "EPSG:4326";
  verified: true;
  sourceRefs: SourceRef[];
}

export interface Facility {
  id: string;
  regionId: Nullable<string>;
  name: string;
  address: Nullable<string>;
  phone: Nullable<string>;
  facilityType: Nullable<string>;
  sportCodes: string[];
  voucherStatus: {
    sports: VoucherState;
    disability: VoucherState;
  };
  location: Nullable<VerifiedLocation>;
  photo: Nullable<{ url: string; attribution: string; rightsVerified: true }>;
  openingHours: Nullable<{ text: string; sourceRefs: SourceRef[] }>;
  sourceRefs: SourceRef[];
}

export interface ProgramFee {
  amountKrw: Nullable<number>;
  periodUnit: "month" | "session" | "course" | "unknown";
  chargeBasis: "per_person" | "per_group" | "unknown";
  verified: boolean;
  rawLabel: Nullable<string>;
  sourceRefs: SourceRef[];
}

export interface ProgramSchedule {
  weekdays: Nullable<Array<1 | 2 | 3 | 4 | 5 | 6 | 7>>; // Monday=1
  startTime: Nullable<string>; // HH:mm
  endTime: Nullable<string>;
  startDate: Nullable<string>;
  endDate: Nullable<string>;
}

export interface Program {
  id: string;
  facilityId: Nullable<string>;
  facilityLinkStatus: "matched" | "unmatched" | "ambiguous";
  sourceFacilityName: Nullable<string>;
  regionId: Nullable<string>;
  name: string;
  sportCode: Nullable<string>;
  targetGroups: Nullable<string[]>; // only verified source categories
  voucherType: "sports" | "disability" | "unknown";
  schedule: ProgramSchedule;
  fee: ProgramFee;
  recruitmentCapacity: Nullable<number>; // NOT live remaining seats
  sourceRefs: SourceRef[];
}

export interface UsageRecord {
  id: string;
  programId: Nullable<string>;
  facilityId: Nullable<string>;
  regionId: Nullable<string>;
  sportCode: Nullable<string>;
  voucherType: "sports" | "disability";
  period: ReferencePeriod;
  applicationCount: Nullable<number>; // NOT deduplicated unique persons
  sourceRefs: SourceRef[];
}

export interface RegionalCoverage {
  id: string;
  regionId: string;
  period: ReferencePeriod;
  cohortKey: string;
  targetCount: Nullable<number>;
  beneficiaryCount: Nullable<number>;
  population: Nullable<number>;
  eligibleFacilityCount: Nullable<number>;
  cohortAggregationApproved: boolean;
  numeratorDenominatorCompatible: boolean;
  validationNote: string;
  sourceRefs: SourceRef[];
}

export interface TransitLink {
  id: string;
  facilityId: string;
  stopName: string;
  mode: "bus" | "subway" | "unknown";
  straightDistanceMeters: Nullable<number>;
  walkingDistanceMeters: Nullable<number>;
  walkingSeconds: Nullable<number>;
  sourceRefs: SourceRef[];
}

export interface DataPackage {
  mode: DataMode;
  manifests: DatasetManifest[];
  regions: Region[];
  facilities: Facility[];
  programs: Program[];
  usage: UsageRecord[];
  coverage: RegionalCoverage[];
  transit: TransitLink[];
  capabilities: DataCapabilities;
}

export interface SnapshotSelection {
  // Multiple sources may have different reference dates; never fake one date.
  byDatasetId: Record<string, string>;
}

export interface DataProvider {
  mode: DataMode;
  load(selection: SnapshotSelection): Promise<DataPackage>;
}

export interface BudgetInput {
  totalKrw: number;       // non-negative integer
  plannedPeople: number; // positive integer
  months: number;        // positive integer
}

export type BudgetEvaluation =
  | { status: "not_requested" }
  | { status: "not_calculable"; reason: string }
  | {
      status: "calculated";
      input: BudgetInput;
      monthlyPerPersonKrw: number;
      plannedTuitionKrw: number;
      withinBudget: boolean;
      arithmeticSupportedPeople: Nullable<number>; // null for verified free fee
      note: string;
    };

export interface ProgramQuery {
  snapshots: SnapshotSelection;
  regionId: Nullable<string>;
  facilityId: Nullable<string>;
  targetGroup: Nullable<string>;
  sportCodes: string[];
  voucherType: "all" | "sports" | "disability";
  weekdays: Array<1 | 2 | 3 | 4 | 5 | 6 | 7>;
  timeWindow: Nullable<{ startTime: string; endTime: string }>;
  dateWindow: Nullable<{ startDate: string; endDate: string }>;
  budget: Nullable<BudgetInput>;
  sortBy: "program_name" | "monthly_fee" | "stop_walking_time";
}

export interface ProgramResultRow {
  program: Program;
  facility: Nullable<Facility>;
  nearestStopWalkingSeconds: Nullable<number>;
  budget: BudgetEvaluation;
  rank: number;
}

export interface ProgramSearchResult {
  appliedQuery: ProgramQuery;
  allRows: ProgramResultRow[];
  topThree: ProgramResultRow[];
  matchedFacilityIds: string[];
  excludedCounts: Record<string, number>;
  createdAt: string;
}

export interface MetricValue {
  value: Nullable<number>;
  unit: "people" | "facilities" | "programs" | "ratio" | "krw" | "seconds";
  status: Availability;
  label: string;
  reason: Nullable<string>;
  coverage: Nullable<{ observed: number; expected: number }>;
  sourceRefs: SourceRef[];
}
```

---

# SPORT INSIGHT — Codex 전용 프롬프트 모음

버전: 1.1 / 분리일: 2026-09-11

이 문서는 `sport-insight-codex.zip` 안의 명세·디자인·계약 파일과 함께 사용한다.
공통 규칙은 프로젝트 루트 `AGENTS.md`에 직접 들어 있다.
다른 개발 도구의 지침 파일이나 프롬프트는 필요하지 않다.

## 사용 방법
ZIP 내부 파일을 저장소에 배치하되 기존 지침과 파일을 덮어쓰지 않고 병합한다.
첫 실행은 아래 START만 복사해 전달한다.
그다음 00 → 01 → 02 → 03 → 04 → 05 → 06 순으로 해당 단계만 실행한다.
START가 00을 실행하므로 같은 작업을 다시 지시하지 않는다.
프롬프트가 이미 끝난 단계라면 재생성하지 말고 검증부터 한다.
RESUME은 이어서 작업할 때, REVIEW는 코드 수정 없이 검토할 때 사용한다.

## 고정 범위
대시보드 / 프로그램 분석 / 시설 현황, AI 없음, 별도 보고서 없음, XLSX 내보내기.
화면·데이터·예산·지도 규칙은 각 프롬프트의 읽을 파일을 기준으로 한다.
이 패키지에는 원본 공공데이터와 실제 GeoJSON이 포함되지 않는다.


---

## 복사할 파일: `prompts/START.md`

```text
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
```

---

## 복사할 파일: `prompts/00-bootstrap.md`

```text
# 작업 00 — 저장소 점검 및 공통 레이아웃 | Codex 전용
## 읽을 파일
AGENTS.md, docs/00-scope.md, docs/01-screen-spec.md의 COM,
design/final-ui-reference.png, design/sport-insight-colors.css.

## 작업
1. 저장소의 프레임워크, 패키지 매니저, lockfile, 기존 컴포넌트, 테스트와 실행 명령을 조사해.
2. 기존 스택이 있으면 유지해. 빈 저장소라면 React+TypeScript+Vite 기본안을 사용하되
   설치할 안정 버전과 호환성은 공식 문서/패키지 메타데이터로 확인해.
3. /dashboard, /programs, /facilities의 세 라우트와 /의 리다이렉트를 구현해.
4. 헤더·사이드바·콘텐츠 레이아웃과 공통 카드/표/버튼/상태 컴포넌트를 만들어.
   지금은 보고서, AI, 공지사항, 설정, 회원가입, 예약 메뉴를 만들지 마.
5. 색상은 기존 --si-* 변수를 사용해. CSS를 임의 팔레트로 교체하지 마.
6. 원본 데이터가 없다는 것을 명시한 demo/real 모드 표시를 공통 영역에 마련해.
7. desktop 1440/1280 및 좁은 화면에서 레이아웃이 접근 가능하도록 구성해.
8. 라우팅·포커스·기본 렌더링 테스트와 실제 실행 명령을 README에 기록해.

## 제한
실제 통계, 추천 카드, 예산 로직을 임의 수치로 완성하지 마.
참고 이미지의 3개 화면 콜라주를 하나의 페이지로 만들지 마.
이미 있는 AGENTS.md 등 프로젝트 지침과 사용자 변경을 보존해.
실제 서비스에 LLM SDK를 설치하지 마.
지도 경계 자산은 아직 준비되지 않았으면 미연결 상태로 남겨.

## 완료 조건
세 메뉴 이동과 현재 메뉴 표시가 동작하고 한국어 레이아웃을 확인할 수 있다.
타입 검사·빌드·가능한 기본 테스트를 실행한다.
변경 파일, 사용한 의존성, 명령과 결과, 단계01에 필요한 사항을 보고한다.

## 작업 종료 기록
docs/WORK-STATUS.md에서 이 단계의 상태를 갱신해.
변경 파일, 실제 실행한 검사와 결과, 실행하지 못한 검사와 사유를 기록해.
실데이터·GeoJSON·가격단위 검증이 남아 있으면 해결된 것처럼 표시하지 마.
후속 단계는 자동 실행하지 말고 이번 단계의 결과를 보고한 뒤 멈춰.
```

---

## 복사할 파일: `prompts/01-data-layer.md`

```text
# 작업 01 — 데이터 계약, provider, 순수 계산 함수 | Codex 전용
## 읽을 파일
AGENTS.md, docs/02-data-contract.md, docs/03-calculation-export-map.md,
contracts/domain.ts, docs/04-acceptance-tests.md.

## 작업
1. contracts/domain.ts를 내부 정규화 계약으로 검토해. 원본 헤더라고 가정하지 마.
2. 시설/프로그램/지역통계/이용현황/교통정보 provider 경계를 만들고 UI 계산과 분리해.
3. 실제 파일이 있으면 컬럼·단위·기준시점·인코딩·행정코드·키·중복·이용조건을 검토한 뒤
   source field → normalized field 매핑 문서를 작성해.
   원본이 없으면 real provider는 연결 필요 상태를 반환하고 완료라고 보고하지 마.
4. 실제와 구분된 고정 demo fixture를 만들어.
   시연 시설명은 '시연 체육시설 A' 등으로 명시하고 난수로 통계를 생성하지 마.
5. 순수 함수로 수혜율, 고유시설/강좌 수, 신청인원 합계, 월·1인 가격 평균,
   인접 정류장 최소 도보시간, 예산 계산, 조건검색, 정렬을 구현해.
6. 동일 selector 결과를 요약/상위3개/표/지도/엑셀에서 재사용할 구조를 만들어.
7. capabilities와 출처 metadata를 구현해. null, 실제0, 미검증을 구분해.
8. docs/04의 DATA와 PROG 예산·정렬 테스트를 작성하고 실행해.

## 반드시 지킬 규칙
- 가입/지원 대상자와 신청합계는 다른 지표야.
- 수혜율은 분자/분모의 정의가 맞는 데이터로만 계산해.
- 신청합계를 고유인원으로 바꾸지 마.
- fee가 verified/month/per_person일 때만 월별 예산 계산을 해.
- 이름만 같은 시설과 강좌를 무조건 합치지 마.
- 좌표/영업시간/사진/잔여석/현재 운영 여부를 추정하지 마.
- 지역코드체계를 자동 추측하거나 시점이 다른 통계로 증감률을 만들지 마.

## 완료 조건
계산 함수가 독립 테스트 가능하고 고정 fixture의 예상값을 통과한다.
실제 데이터 매핑이 완료되지 않은 부분을 docs/DECISIONS.md에 기록한다.
변경 파일, 테스트 결과, 실제 연결 상태를 보고한 후 멈춰.

## 작업 종료 기록
docs/WORK-STATUS.md에서 이 단계의 상태를 갱신해.
변경 파일, 실제 실행한 검사와 결과, 실행하지 못한 검사와 사유를 기록해.
실데이터·GeoJSON·가격단위 검증이 남아 있으면 해결된 것처럼 표시하지 마.
후속 단계는 자동 실행하지 말고 이번 단계의 결과를 보고한 뒤 멈춰.
```

---

## 복사할 파일: `prompts/02-dashboard.md`

```text
# 작업 02 — 대시보드 | Codex 전용
## 읽을 파일
AGENTS.md, docs/01-screen-spec.md의 COM/DASH,
docs/03-calculation-export-map.md, design/final-ui-reference.png.

## 구현할 화면
/dashboard에 최종 시안 상단 대시보드의 배치를 구현해.
상단은 자료 기준·지역 필터와 4개 지표 카드,
본문은 대한민국 지도 / 지역별 지원 현황 / 종목별 현황·참고지표로 구성해.

## 상세 작업
1. 필터는 제공되는 스냅샷만 보여주고 적용된 조회 상태를 공통 selector로 관리해.
2. 카드명은 지원대상 인원, 지원 수급인원, 등록시설 수, 등록강좌 수를 사용해.
   '실제 이용자'를 신청합계로 채우지 마.
3. 지도 선택 시 지역별 카드와 하위지역 차트를 갱신해.
   MVP는 시도 선택까지만 하고 시군구 지도 드릴다운은 만들지 마.
4. ECharts 지도 컴포넌트는 실제 검증된 경계 자산이 있을 때 연결해.
   없으면 지역 select와 대응표로 대체하고 미연결 사유를 표시해.
5. 지역차트는 대상인원/수급인원/수혜율 탭으로 만든다.
   종목차트는 신청인원 합계/등록강좌 수 탭으로 만들고 서로 다른 단위를 섞지 마.
6. 전년 배지는 비교 가능한 전년 자료가 있을 때만 표시해.
   지도/카드에 값이 없으면 0이 아니라 확인 필요를 표시해.
7. 대시보드 전체·차트별 내보내기 버튼을 공통 ExportButton에 연결해.
   export 함수가 아직 없으면 인터페이스와 테스트를 먼저 만들고 기능 미완료를 명시해.
8. '선택 지역 프로그램 보기'로 /programs에 지역을 전달해.
9. COM/DASH/MAP 테스트와 화면 확인을 수행해.

## 제외
AI 인사이트, 수혜율 상승 예측, 정책 우선순위 점수, 평균 거주지 접근시간,
별도 보고서 메뉴, 이미지의 고정 수치.

## 완료 조건
모든 영역이 같은 기준자료/선택지역과 일치한다.
지도 실패 시 다른 조회와 대응표는 동작한다.
화면에서 사용한 데이터 selector와 내보낼 데이터가 같다.
실행한 테스트와 아직 필요한 GeoJSON/통계 검증을 보고해.

## 작업 종료 기록
docs/WORK-STATUS.md에서 이 단계의 상태를 갱신해.
변경 파일, 실제 실행한 검사와 결과, 실행하지 못한 검사와 사유를 기록해.
실데이터·GeoJSON·가격단위 검증이 남아 있으면 해결된 것처럼 표시하지 마.
후속 단계는 자동 실행하지 말고 이번 단계의 결과를 보고한 뒤 멈춰.
```

---

## 복사할 파일: `prompts/03-programs.md`

```text
# 작업 03 — 프로그램 분석 / 조건 기반 추천 | Codex 전용
## 읽을 파일
AGENTS.md, docs/01-screen-spec.md의 PROG,
docs/02-data-contract.md, docs/03-calculation-export-map.md의 2~4,
design/final-ui-reference.png.

## 구현할 화면
/programs에 이전 시안의 왼쪽 조건 폼 / 오른쪽 요약·상위3개 카드 /
하단 시설 분포·전체 비교표 레이아웃을 만들어.
시민 개인용 운동 추천 앱이 아니라 담당자의 정책 검토 화면이야.

## 입력
실제 자료 스냅샷, 지역, 대상 구분, 종목, 이용권 구분, 요일/시간, 강좌기간,
수강료 지원예산 B, 계획인원 N, 지원개월 M, 정렬 기준.
예산은 선택값이지만 B를 넣으면 N과 M은 필수야.
강좌 기간 검색과 계획 지원개월을 같은 의미로 취급하지 마.
운영방식은 기존 등록강좌 조회로 고정하고 신규 사업 생성 옵션은 만들지 마.

## 검색 규칙
1. 실제 강좌를 엄격하게 필터링하고 명시된 정렬만 적용해.
2. 상위3개는 같은 전체 결과의 처음3개야. 결과가2개면2개만 보여줘.
3. '강좌명/월·1인 수강료/정류장 도보시간' 중 선택 정렬을 사용해.
4. 같은 값은 강좌명/programId로 안정 정렬해. 임의 점수·추천확률은 없어.
5. 결과없음, 단위미확인, 시설미연계, 좌표미제공을 구분해.

## 예산 규칙
verified=true, month, per_person 가격 P에서만:
계획 소요액=P×N×M, 예산충족=소요액<=B,
산술상 지원가능인원=floor(B/(P×M)).
무료 P=0은 소요0, 지원인원null+별도 안내.
가격 단위가 안 맞으면 추정해서 월단가로 바꾸지 마.
예산 필터 활성 시 계산 가능·예산 충족 결과만 반환하고 제외사유 건수를 알려줘.
세 카드는 동일 예산 기준 독립 비교안이므로 비용이나 인원을 합산하지 마.
수용정원·추가수혜자·사업총운영비·정책효과를 예측하지 마.

## 표시·상호작용
실제 강좌명/시설명/종목/대상/요일/시간/가격과 단위/출처를 표시해.
추천근거 패널, AI 인사이트, '수요 높음/접근성 우수/고효율' 배지를 만들지 마.
등록 이용권·요일 같은 확인된 사실 배지만 허용해.
지도는 유효 좌표만 표시하고 표는 좌표없는 행도 유지해.
전체 표는 정렬·페이지, 시설명 클릭은 시설현황 상세로 연결해.
엑셀은 페이지 밖을 포함한 전체 적용 결과이며 계산 가정과 단위를 포함해.

## 완료 조건
PROG-T01~12를 포함한 테스트를 수행해.
카드·요약·표·지도·export가 동일 applied 결과를 사용해야 해.
수치 생성 없이 동작하고 AI API 요청이 없어야 해.
변경 파일·테스트·단위 미확인으로 제한되는 기능을 보고해.

## 작업 종료 기록
docs/WORK-STATUS.md에서 이 단계의 상태를 갱신해.
변경 파일, 실제 실행한 검사와 결과, 실행하지 못한 검사와 사유를 기록해.
실데이터·GeoJSON·가격단위 검증이 남아 있으면 해결된 것처럼 표시하지 마.
후속 단계는 자동 실행하지 말고 이번 단계의 결과를 보고한 뒤 멈춰.
```

---

## 복사할 파일: `prompts/04-facilities.md`

```text
# 작업 04 — 시설 현황 / 상세 | Codex 전용
## 읽을 파일
AGENTS.md, docs/01-screen-spec.md의 FAC,
docs/02-data-contract.md, docs/03-calculation-export-map.md,
design/final-ui-reference.png.

## 구현
/facilities에 상단 필터 / 왼쪽 시설 목록 / 오른쪽 시설 상세·등록강좌 표를 구현해.
필터는 기준자료, 지역, 확인된 시설유형, 종목, 이용권, 시설명/주소 검색어야.
드래프트와 적용 조건을 구분하고 조회/초기화/Enter를 지원해.

시설 목록에는 이름, 지역, 주소, 주요종목, 연결강좌 수, 자료상 이용권 상태를 표시해.
20/50건 페이지와 명시적인 정렬을 제공하고 전체 필터 결과를 export 대상으로 해.
시설 선택 시 오른쪽 상세를 갱신하고 검색 결과에서 선택시설이 사라지면 선택을 해제해.
facilityId로 직접 진입할 수 있게 하고 잘못된 ID는 명확한 오류와 복귀를 제공해.

상세에는 실제 이름/주소/연락처/등록구분/기준일을 표시해.
확인된 사진이 없으면 플레이스홀더, 시설 운영시간이 없으면 미제공이야.
강좌시간을 영업시간으로 사용하거나 인터넷 임의 사진을 넣지 마.
스포츠와 장애인 이용권 상태는 구분하고 자료 미등장은 '확인 필요'로 처리해.
장애인 가맹을 무장애 인증이나 실제 장애유형 적합성으로 해석하지 마.

선택 시설에 연결된 전체 강좌를 별도 표로 표시해.
시설목록 종목 필터와 상세 전체강좌 범위가 다르다는 라벨을 붙여줘.
원본 모집정원은 잔여석이 아니야.
강좌 연계 자료가 없으면 실제 강좌가0개라고 단정하지 마.
교통정보는 시설↔정류장 거리(m)/도보시간(초→분)만 보여줘.

시설목록 엑셀과 선택시설 등록강좌 엑셀 버튼을 각각 연결해.
두 버튼의 범위·출처·조회조건이 섞이지 않도록 테스트해.

## 완료 조건
FAC-T01~07, 필터/직접진입/초기화, 두 종류 export의 범위가 검증된다.
사진/시간/가맹/좌표 결측을 가짜 값으로 채우지 않는다.
변경 파일·테스트 결과·실데이터 연계 제한을 보고해.

## 작업 종료 기록
docs/WORK-STATUS.md에서 이 단계의 상태를 갱신해.
변경 파일, 실제 실행한 검사와 결과, 실행하지 못한 검사와 사유를 기록해.
실데이터·GeoJSON·가격단위 검증이 남아 있으면 해결된 것처럼 표시하지 마.
후속 단계는 자동 실행하지 말고 이번 단계의 결과를 보고한 뒤 멈춰.
```

---

## 복사할 파일: `prompts/05-export-map.md`

```text
# 작업 05 — XLSX 공통 기능과 지도 연동 마감 | Codex 전용
## 읽을 파일
AGENTS.md, docs/03-calculation-export-map.md의 4~5,
docs/04-acceptance-tests.md의 MAP/XLSX, docs/05-source-register.md의 T03/T04.

## 엑셀
1. 기존 XLSX 구현이 없다면 ExcelJS 문서형 workbook을 공통 유틸로 구성해.
   브라우저에서 Node fs/스트리밍 writer를 쓰지 마.
2. EXP-01~06의 내보내기 범위를 각각 구현해. 현재 페이지만 잘라 내보내지 마.
3. 클릭 시점 applied 결과·스냅샷·정렬을 고정해 저장해.
4. 주제별 데이터 시트와 조회조건_출처 시트를 만든다.
5. 숫자/비율/텍스트형 코드·전화·ID/결측을 올바르게 저장해.
   외부문자열은 수식으로 변환하지 마.
6. demo 워터마크, 0건, 처리중, 실패, 한도초과를 처리해.
7. 파일을 생성한 뒤 다시 읽어 행수·시트·타입·값·선행0·서식을 검증하는 테스트를 만들어.

## 지도
1. 먼저 경계 파일의 출처/이용조건/기준연도/좌표계/지역코드 매핑 기록을 확인해.
2. 준비된 자산이 있으면 ECharts registerMap과 시도 선택을 실제 연결해.
3. 없다면 가짜 한국 경계를 만들지 말고 미연결/fallback 상태를 유지하고 blocker로 기록해.
4. 차트·지도 색은 CSS 변수의 실제 계산된 색상값을 읽어 적용해.
5. 지도 클릭/전체보기/결측색/툴팁/표 대안/ResizeObserver 정리/차트 dispose를 검증해.
6. 프로그램 지도는 좌표 유효시설만 표시하고 n/N을 명시해.
   지도 SDK·타일·길찾기·현재위치 권한을 추가하지 마.

## 완료 조건
내보낸 XLSX 재읽기 검증과 MAP/XLSX 테스트를 수행한다.
화면별 export 버튼이 모두 공통 규칙에 연결된다.
지도 자산이 없으면 지도 완료로 보고하지 않는다.
실행 결과와 실제 미완료 의존성을 명시해.

## 작업 종료 기록
docs/WORK-STATUS.md에서 이 단계의 상태를 갱신해.
변경 파일, 실제 실행한 검사와 결과, 실행하지 못한 검사와 사유를 기록해.
실데이터·GeoJSON·가격단위 검증이 남아 있으면 해결된 것처럼 표시하지 마.
후속 단계는 자동 실행하지 말고 이번 단계의 결과를 보고한 뒤 멈춰.
```

---

## 복사할 파일: `prompts/06-qa.md`

```text
# 작업 06 — 최종 통합 검수 | Codex 전용
제품 기능을 새로 추가하지 말고 아래 범위에서 결함을 검수·수정해.

## 기준
AGENTS.md, docs/00-scope.md, docs/01-screen-spec.md,
docs/02-data-contract.md, docs/03-calculation-export-map.md,
docs/04-acceptance-tests.md, docs/DECISIONS.md, 실제 코드와 git diff.

## 순서
1. 세 라우트의 필터/적용상태/정렬/페이지/시설 상세/뒤로가기/새로고침을 검증해.
2. 지표의 통계 기준시점, 분자분모, 중복, 가격 단위, 좌표, 교통 구간 의미를 점검해.
3. 예산 P×N×M과 floor 산식, 무료/미확인/범위초과를 테스트해.
4. 모든 XLSX 버튼의 전체범위/타입/출처/demo표시를 재읽기 테스트로 확인해.
5. 지도 클릭 및 GeoJSON 미연결 fallback을 테스트해.
6. AI SDK/API/추천이유/가짜 점수/효과예측/보고서 메뉴가 없는지 검사해.
7. 실제 모드가 demo나0으로 결측을 숨기지 않는지 검사해.
8. 접근성·키보드·1440/1280/좁은 화면을 확인해.
9. 저장소의 타입검사·린트·단위테스트·빌드·E2E 명령을 실행해.
10. 실제 실행 화면을 캡처하고 QA 결과를 파일로 남겨. 시안 이미지를 완료 증거로 쓰지 마.

## 결과 형식
- 발견 이슈: 심각도, 파일/화면, 재현 단계, 원인, 수정.
- 검증: 명령, 통과/실패/미실행, 실제 로그 요약.
- 산출물: 변경파일과 실제 캡처·테스트 결과 위치.
- 남은 의존성: 원본/컬럼/가격단위/지역경계/보안운영 요구.
명세 범위를 변경해야 하면 먼저 결정사항으로 제시하고 임의 확대하지 마.
미실행 항목은 통과했다고 쓰지 마.

## 작업 종료 기록
docs/WORK-STATUS.md에서 이 단계의 상태를 갱신해.
변경 파일, 실제 실행한 검사와 결과, 실행하지 못한 검사와 사유를 기록해.
실데이터·GeoJSON·가격단위 검증이 남아 있으면 해결된 것처럼 표시하지 마.
후속 단계는 자동 실행하지 말고 이번 단계의 결과를 보고한 뒤 멈춰.
```

---

## 복사할 파일: `prompts/RESUME.md`

```text
# Codex 이어서 작업하는 프롬프트

프로젝트의 AGENTS.md, docs/WORK-STATUS.md, docs/DECISIONS.md,
현재 코드와 git status/diff를 읽고 SPORT INSIGHT 개발 상태를 점검해.

이번에 요청할 단계는 아래 한 개야.
단계 파일: prompts/02-dashboard.md
※ 실제로 진행할 단계의 파일 경로로 이 줄을 바꾼 뒤 실행해.

해당 단계의 읽을 파일과 선행 조건을 확인해.
상태표만 믿고 완료로 판단하지 말고 실제 코드·테스트 결과와 대조해.
선행 단계가 안 돼 있으면 필요한 의존성과 가능한 작업 범위를 명확히 알려줘.
이미 있는 코드를 지우거나 처음부터 재생성하지 마.

지정된 단계 안에서 필요한 변경만 구현하고 가능한 검증을 실행해.
원본 데이터·가격단위·지도 자산이 없으면 미연결 상태로 남겨.
제품의 AI 기능이나 별도 보고서를 추가하지 마.

작업 후 변경 파일, 실행 명령·결과, 미실행 사유, 남은 의존성을 보고해.
docs/WORK-STATUS.md를 갱신하고 다음 단계는 자동 실행하지 마.
```

---

## 복사할 파일: `prompts/REVIEW.md`

```text
# Codex 코드 검토 프롬프트
현재 저장소의 변경사항을 검토해.
AGENTS.md, 해당 작업 프롬프트, docs/01-screen-spec.md, docs/02-data-contract.md, docs/03-calculation-export-map.md, docs/04-acceptance-tests.md와 git diff를 읽고 리뷰해.
이번에는 코드 수정 없이 발견사항을 먼저 보고해.

핵심 검토:
- 사용자 요구와 범위 일치: 3개 메뉴, AI 없음, 보고서 없음, XLSX 있음.
- 데이터 의미: 신청합계/실인원, 모집인원/잔여석, 가격/운영비, 정류장/거주지 접근시간.
- 실제 원본 매핑 근거와 demo/real 분리.
- 필터·카드·표·지도·내보내기 모집단 일치.
- 무료/결측/정렬동률/분모0/단위미확인/범위초과.
- 스냅샷/지역코드/중복시설·강좌 처리.
- 테스트가 실제 로직을 검증하는지, 테스트 통과 주장에 실행 증거가 있는지.

이슈는 중요도 순으로 파일·라인·재현 조건·영향·수정 제안을 써줘.
문제가 없더라도 검토 범위와 실행하지 못한 테스트를 명시해.
기존 변경을 덮어쓰거나 새 기능을 제안하지 마.
```
