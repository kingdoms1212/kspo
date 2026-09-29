import fs from 'node:fs/promises';
let p='README.md'; let t=await fs.readFile(p,'utf8');
t=t.replace('예약 배치의 일요일 00시는 서버 설정 UTC 기준입니다.','현재 예약 배치는 **매월 1일 01:00 한국 시간(Asia/Seoul)**입니다. 첨부 이미지의 일요일 예약 표기는 변경 전 설정입니다.');
t=t.replace('**[수기 입력: 확정된 ERD와 엔터티·PK·FK·관계 설명]**',`### CSV 파일 구성과 역할

현재 업무 데이터는 관계형 테이블 대신 CSV 파일로 관리합니다. 아래 표는 원본과 서울 서비스 파일의 대응 관계이며, DB의 PK·FK 제약을 의미하지 않습니다.

| 자료 | 원본 파일 (data/) | 서비스 파일 (data/Batch/) | 파일 설명 |
|---|---|---|---|
| 공공체육시설 프로그램 | public_sports_program.csv | public_sports_program_seoul.csv | 기존 강좌의 명칭·종목·요일·수강료 등. 프로그램 검색·비교에 사용 |
| 스포츠강좌이용권 이용현황 | sports_voucher_usage.csv | sports_voucher_usage_seoul.csv | 시설·강좌·개설월별 이용 기록. 지역·종목별 신청 실적 집계와 AI 통계 근거 |
| 체육시설 현황 | sports_facility_status.csv | sports_facility_status_seoul.csv | 시설명·주소·유형·운영상태 등. 상세 조회와 정상운영 설계 후보 선정 |
| 시설 인접 교통 | facility_transit.csv | facility_transit_seoul.csv | 시설 위치와 인접 교통 정보. 연결 가능한 시설의 교통 상세 조회 |

파일명의 _seoul은 서울 범위로 정제한 서비스 산출물이라는 뜻입니다. 배치는 원본을 지역별로 추출하며, 중복 제거·상태 필터·집계는 각 조회 모듈에서도 수행합니다.

### 파일 간 연결 기준

| 연결 대상 | 사용 기준 | 주의점 |
|---|---|---|
| 이용현황 내부 시설·강좌 | 지역 코드·시군구 코드·시설명·주소·상세주소, 강좌번호 | 집계용 식별 기준이며 다른 CSV의 공통 FK가 아님 |
| 시설 현황과 교통 | 정규화 시설명 + 위도·경도 소수점 6자리 | 이름만 같다고 연결하지 않음. 미연결은 주변 교통 부재를 의미하지 않음 |
| 선택 종목과 시설 후보 | 종목·시설유형/업종 대응표 + 지역 + 정상운영 | 업무 규칙에 따른 후보 선정이며 원본 파일 간 외래키 관계가 아님 |
| CSV와 manifest | generation·파일 크기·수정시각·SHA-256 | 게시 세대·파일 변경 검증용 메타데이터 |

**[수기 입력: 별도 DB 설계 시 확정 ERD와 엔터티·PK·FK·관계 설명]**`);
t=t.replace('### CSV 정제·사전 적재\n','### CSV 정제·사전 적재\n\n**정기 실행: 매월 1일 01:00, 한국 시간(Asia/Seoul).** 서버 프로세스 안의 APScheduler가 실행합니다. 서버가 중지된 동안의 예약 실행을 보장하지 않으며, 원본 변경이 없으면 재정제를 생략할 수 있습니다.\n');
await fs.writeFile(p,t);
p='main/templates/overview/index.html'; t=await fs.readFile(p,'utf8'); t=t.replaceAll('일요일 00:00 UTC','매월 1일 01:00 한국 시간(Asia/Seoul)').replaceAll('예약은 일요일 00:00이며 <code>settings.TIME_ZONE=UTC</code>','예약은 매월 1일 01:00이며 <code>settings.TIME_ZONE=Asia/Seoul</code>'); await fs.writeFile(p,t);
p='docs/RENDER-DEPLOYMENT.md'; t=await fs.readFile(p,'utf8'); t=t.replace('주간 배치는 기존 설정대로 일요일 00:00(Asia/Seoul)에 실행한다.','정기 배치는 매월 1일 01:00(Asia/Seoul, 한국 시간)에 실행한다. 프로세스 내 예약이므로 서비스가 중지된 동안의 실행은 보장하지 않는다.'); await fs.writeFile(p,t);
