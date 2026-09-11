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
