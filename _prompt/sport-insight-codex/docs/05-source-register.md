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
