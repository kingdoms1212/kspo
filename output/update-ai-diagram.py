from pathlib import Path
p=Path('docs/readme-assets/build-diagrams.mjs')
s=p.read_text(encoding='utf-8-sig')
a=s.index("begin('스포링 · AI 공급자 교체 구조'")
b=s.index("begin('스포링 · CSV",a)
s=s[:a]+'''begin('스포링 · AI 연동 구조','사용자 분석 요청 → 근거 구성 → Gemini 호출 → 검증된 의견을 화면과 계획서에 반영');
box(48,185,520,270,'01  사용자 분석 요청',['지역 현황: AI로 분석하기','STEP 03: 프로그램 AI 검토','분석 중 로딩·중복 클릭 제한','조회만으로 AI를 호출하지 않음'],C.blue);
box(640,185,520,270,'02  서버의 분석 근거 구성',['지역 집계·종목 분포·자료 기간','프로그램 검토: 선택 시설·입력 계획','분석 지침·JSON 응답 스키마 준비','유효한 지역 캐시가 있으면 재사용'],C.green);
box(1232,185,520,270,'03  Gemini API 호출',['서버에서 google-genai SDK 사용','API 키는 서버 환경변수로 관리','지침·근거·스키마를 요청으로 전달','일시적 오류만 제한적으로 재시도'],C.orange);
arrow('M568 320H630',C.blue);arrow('M1160 320H1222',C.orange);
box(1232,565,520,245,'04  응답 검증·결과 계산',['JSON 구조·근거 키·점수 검사','프로그램 종합 점수·등급 계산','검증 실패 시 분석 실패 안내'],C.green);
box(640,565,520,245,'05  검증 결과 보관',['지역 요약: 파일 캐시 24시간','프로그램 검토: 서명 토큰 1시간','입력·선택 시설과 결과 일치 검사'],C.purple);
box(48,565,520,245,'06  화면·계획서 반영',['지역 해석·프로그램 검토 결과 표시','선택한 유효 검토만 계획서에 포함','생성·인쇄·복원 시 AI 재호출 없음'],C.blue);
arrow('M1492 455V553',C.green);arrow('M1232 680H1172',C.purple);arrow('M640 680H580',C.blue);
foot('분석 범위','집계·선택 정보로 참고 의견을 제공합니다. 원본 CSV 전체 업로드나 사전 학습은 하지 않습니다.');await save('ai-integration');
''' + s[b:]
s=s[:s.index('const readme=new URL')]+"console.log('Generated diagram SVG files');\n"
p.write_text(s,encoding='utf-8')
