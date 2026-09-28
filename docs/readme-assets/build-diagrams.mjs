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
begin('스포링 · AI 공급자 교체 구조','공통 요청·응답 계약을 유지하고 공급자별 SDK와 오류 처리를 어댑터로 분리');
box(48,185,520,270,'01  업무 서비스·AIRequest',['지역 분석 / 프로그램 검토','분석 지침·집계 근거·입력 계획 구성','응답 스키마와 요청 ID 전달','원본 CSV 전체 업로드·학습 없음'],C.green);
box(640,185,520,270,'02  팩토리·공통 인터페이스',['모드·공급자·모델 설정 확인','factory.create_provider()','AIProvider.generate(request)','선택한 공급자의 SDK만 로딩'],C.green);
box(1232,185,520,270,'03  현재 구현된 공급자',['GeminiProvider: google-genai 호출','DummyProvider: 외부 호출 없는 예시','공급자 오류를 공통 오류 코드로 변환','재시도는 공급자 어댑터에서 처리'],C.orange);
arrow('M568 320H630',C.green);arrow('M1160 320H1222',C.orange);
box(1232,565,520,245,'04  AIResponse·공통 검증',['data / provider / model 반환','JSON 구조·근거 키·점수 검증','검증된 결과만 업무 서비스에 전달'],C.green);
box(640,565,520,245,'05  결과 반영·보관',['지역 분석: 공급자별 파일 캐시','프로그램 검토: 입력 연결 서명 토큰','완성 계획서: 생성 당시 결과 유지'],C.purple);
box(48,565,520,245,'확장 지점 · GPT / Claude',['전용 어댑터 구현 + 팩토리 등록 필요','공통 요청·응답·오류 규약 준수','미구현 공급자 설정만으로 호출 불가'],C.orange);
arrow('M1492 455V553',C.green);arrow('M1232 680H1172',C.purple);
foot('공급자 확장 범위','Gemini·더미를 구현했습니다. 장애 시 다른 공급자로 자동 전환하지 않습니다.');await save('ai-provider-structure');
begin('스포링 · CSV 정제와 사전 적재','매일 00:00 한국 시간(Asia/Seoul) 예약 · 원본 변경 확인 · 검증 완료 후 메모리 갱신');
box(48,185,520,265,'01  원본 CSV 4종',['프로그램 / 이용현황 / 시설 / 교통','data/ 원본 파일과 필수 열 확인','예약·수동·기동 경로에서 배치 실행','변경이 없으면 재정제 생략 가능'],C.purple);
box(640,185,520,265,'02  지역 정제·준비본',['실행 잠금으로 중복 배치 제한','서울 추출·지역 코드 품질 검사','잘못된 행 제외·사유별 건수 기록','.part 파일 작성 후 flush·fsync'],C.purple);
box(1232,185,520,265,'03  검증·서비스 CSV 게시',['대상 지역·0건·준비본 검증','검증 후 파일별 최종 CSV 교체','data/Batch/ 서비스 파일 반영','전체 파일 일괄 트랜잭션은 아님'],C.purple);
arrow('M568 315H630',C.purple);arrow('M1160 315H1222',C.purple);
box(1232,565,520,245,'04  manifest 발행',['파일 교체 후 마지막에 발행','generation / 크기 / 수정시각','SHA-256·행 수·제외 건수 기록'],C.purple);
box(640,565,520,245,'05  runtime 적재·갱신',['워커 초기화 뒤 최초 사전 적재','세대 변경 감지 후 새 데이터 적재','적재 전후 세대·파일 서명 확인'],C.green);
box(48,565,520,245,'06  메모리 스냅샷 조회',['적재 완료된 스냅샷으로 교체','정상 캐시가 있으면 갱신 중 조회 유지','재적재 실패 시 기존 정상 캐시 유지'],C.blue);
arrow('M1492 450V553',C.purple);arrow('M1232 680H1172',C.green);arrow('M640 680H580',C.blue);
foot('운영 전제','서버 중지 중 예약 실행은 보장하지 않습니다. 최초 적재 실패 시 유지할 기존 캐시는 없습니다.');await save('csv-pipeline');
const readme=new URL('../../README.md',dir);let md=await fs.readFile(readme,'utf8');
for(const [title,name] of [['프로그램 설계 흐름','program-design-flow'],['AI 공급자 교체 구조','ai-provider-structure'],['CSV 정제·사전 적재','csv-pipeline']]){
 const start=md.indexOf('### '+title);const code=md.indexOf('```mermaid',start);const end=md.indexOf('```',code+3)+3;
 if(start<0||code<0||end<3)throw new Error('Missing '+title);
 md=md.slice(0,code)+`![${title}](docs/readme-assets/${name}.png)\n\n[이미지 크게 보기](docs/readme-assets/${name}.png) · [SVG 원본](docs/readme-assets/${name}.svg)`+md.slice(end);
}
await fs.writeFile(readme,md);console.log('Generated 3 PNG/SVG diagrams and updated README');


