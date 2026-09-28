import fs from 'node:fs/promises';
import {createRequire} from 'node:module';
const require=createRequire('C:/Users/User/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/');

const dir=new URL('.',import.meta.url);
const C={navy:'#19324F',blue:'#148BDD',green:'#0FA580',purple:'#8562D9',orange:'#DB8121',gray:'#617792'};
const esc=s=>s.replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;');
let body='';
function text(x,y,s,size=25,color=C.navy,weight=400){body+=`<text x="${x}" y="${y}" font-size="${size}" fill="${color}" font-weight="${weight}">${esc(s)}</text>`;}
function box(x,y,w,h,title,lines,color){body+=`<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="16" fill="white" stroke="${color}" stroke-width="2"/><rect x="${x}" y="${y}" width="${w}" height="62" rx="15" fill="${color}"/>`;text(x+24,y+42,title,28,'white',700);lines.forEach((s,i)=>text(x+24,y+106+i*42,s));}
function arrow(d,color=C.blue,label='',x=0,y=0){body+=`<path d="${d}" fill="none" stroke="${color}" stroke-width="3" marker-end="url(#${Object.keys(C).find(k=>C[k]===color)})"/>`;if(label)text(x,y,label,22,color,700);}
function begin(title,sub){body='';text(48,70,title,44,C.navy,700);text(48,118,sub,25,C.gray);}
function foot(head,desc){body+=`<rect x="48" y="882" width="1704" height="76" rx="14" fill="${C.navy}"/>`;text(70,930,head,26,'white',700);text(330,930,desc,24,'white');}
async function save(name){const markers=Object.entries(C).map(([k,c])=>`<marker id="${k}" markerWidth="9" markerHeight="9" refX="8" refY="4.5" orient="auto"><path d="M0 0L9 4.5L0 9Z" fill="${c}"/></marker>`).join('');const svg=`<svg xmlns="http://www.w3.org/2000/svg" width="1800" height="1000" viewBox="0 0 1800 1000"><defs>${markers}</defs><rect width="1800" height="1000" fill="#F5F8FC"/><g font-family="Malgun Gothic, sans-serif">${body}</g></svg>`;await fs.writeFile(new URL(name+'.svg',dir),svg);}
begin('스포링 · 프로그램 설계 흐름','지역 현황 확인부터 종목·시설 선택, AI 검토와 계획서 완성까지');
box(48,185,520,250,'01  지역 선택·조회',['지도·행정구역에서 지역 조회','시설·강좌·신청 실적 확인','지역 AI 분석은 버튼 클릭 시 선택 실행'],C.blue);
box(640,185,520,250,'02  종목·시설 선택',['종목에 맞는 정상운영 후보 조회','시설 상세·교통 확인, 최대 20곳 선택','후보가 없을 때만 동의 후 시설 미정'],C.blue);
box(1232,185,520,250,'03  프로그램 정보 입력',['프로그램명·대상·기간·내용 입력','시설별 모집인원·수강료 입력','현재 입력으로 AI 분석 여부 선택'],C.blue);
arrow('M568 305H630');arrow('M1160 305H1222');
box(1232,550,520,260,'04  AI 검토 또는 생략',['AI 검토: 의견 확인·포함 여부 선택','AI 미사용: AI 없이 생성하기 선택','동일 입력의 유효 결과는 재분석 제한','입력 변경 시 재검토 또는 AI 생략'],C.orange);
box(640,550,520,260,'05  계획서 완성',['현재 입력·선택 시설·검토 토큰 검증','선택한 유효 AI 의견만 계획서에 반영','생성 후에도 STEP 03과 입력값 유지','생성 과정에서 AI를 다시 호출하지 않음'],C.green);
box(48,550,520,260,'06  인쇄·최근 목록',['이미지 준비 후 계획서 인쇄','생성 당시 결과를 브라우저 5건 보관','최근 항목 복원 시 서명 확인','처음으로: 입력·AI 화면 초기화'],C.purple);
arrow('M1492 435V538',C.orange);arrow('M1232 680H1172',C.green);arrow('M640 680H580',C.purple);
foot('사용자 결정 유지','AI 의견은 참고 자료입니다. 최종 프로그램 기획과 운영 판단은 담당자가 수행합니다.');await save('program-design-flow');
begin('스포링 · AI 연동 구조','사용자 분석 요청 → 근거 구성 → Gemini 호출 → 검증된 의견을 화면과 계획서에 반영');
box(48,185,520,270,'01  사용자 분석 요청',['지역 현황: AI로 분석하기','STEP 03: 프로그램 AI 검토','분석 중 로딩·중복 클릭 제한','조회만으로 AI를 호출하지 않음'],C.blue);
box(640,185,520,270,'02  서버의 분석 근거 구성',['지역 집계·종목 분포·자료 기간','프로그램 검토: 선택 시설·입력 계획','분석 지침·JSON 응답 스키마 준비','유효한 지역 캐시가 있으면 재사용'],C.green);
box(1232,185,520,270,'03  Gemini API 호출',['서버에서 google-genai SDK 사용','API 키는 서버 환경변수로 관리','지침·근거·스키마를 요청으로 전달','일시적 오류만 제한적으로 재시도'],C.orange);
arrow('M568 320H630',C.blue);arrow('M1160 320H1222',C.orange);
box(1232,565,520,245,'04  응답 검증·결과 계산',['JSON 구조·근거 키·점수 검사','프로그램 종합 점수·등급 계산','검증 실패 시 분석 실패 안내'],C.green);
box(640,565,520,245,'05  검증 결과 보관',['지역 요약: 파일 캐시 24시간','프로그램 검토: 서명 토큰 1시간','입력·선택 시설과 결과 일치 검사'],C.purple);
box(48,565,520,245,'06  화면·계획서 반영',['지역 해석·프로그램 검토 결과 표시','선택한 유효 검토만 계획서에 포함','생성·인쇄·복원 시 AI 재호출 없음'],C.blue);
arrow('M1492 455V553',C.green);arrow('M1232 680H1172',C.purple);arrow('M640 680H580',C.blue);
foot('분석 범위','집계·선택 정보로 참고 의견을 제공합니다. 원본 CSV 전체 업로드나 사전 학습은 하지 않습니다.');await save('ai-integration');
begin('스포링 · CSV 정제와 사전 적재','매월 1일 01:00 한국 시간(Asia/Seoul) 예약 · 원본 변경 확인 · 검증 완료 후 메모리 갱신');
box(48,185,520,265,'01  원본 CSV 4종',['프로그램 / 이용현황 / 시설 / 교통','data/ 원본 파일과 필수 열 확인','예약·수동·기동 경로에서 배치 실행','변경이 없으면 재정제 생략 가능'],C.purple);
box(640,185,520,265,'02  지역 정제·준비본',['실행 잠금으로 중복 배치 제한','서울 추출·지역 코드 품질 검사','잘못된 행 제외·사유별 건수 기록','.part 파일 작성 후 flush·fsync'],C.purple);
box(1232,185,520,265,'03  검증·서비스 CSV 게시',['대상 지역·0건·준비본 검증','검증 후 파일별 최종 CSV 교체','data/Batch/ 서비스 파일 반영','전체 파일 일괄 트랜잭션은 아님'],C.purple);
arrow('M568 315H630',C.purple);arrow('M1160 315H1222',C.purple);
box(1232,565,520,245,'04  manifest 발행',['파일 교체 후 마지막에 발행','generation / 크기 / 수정시각','SHA-256·행 수·제외 건수 기록'],C.purple);
box(640,565,520,245,'05  runtime 적재·갱신',['워커 초기화 뒤 최초 사전 적재','세대 변경 감지 후 새 데이터 적재','적재 전후 세대·파일 서명 확인'],C.green);
box(48,565,520,245,'06  메모리 스냅샷 조회',['적재 완료된 스냅샷으로 교체','정상 캐시가 있으면 갱신 중 조회 유지','재적재 실패 시 기존 정상 캐시 유지'],C.blue);
arrow('M1492 450V553',C.purple);arrow('M1232 680H1172',C.green);arrow('M640 680H580',C.blue);
foot('운영 전제','서버 중지 중 예약 실행은 보장하지 않습니다. 최초 적재 실패 시 유지할 기존 캐시는 없습니다.');await save('csv-pipeline');
console.log('Generated diagram SVG files');
