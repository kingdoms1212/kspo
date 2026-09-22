# Gemini 지역·프로그램 적합성 분석

## 흐름과 변경 범위

기존 `POST /dashboard/plan/preview` → `PlanForm` 입력 검증 → 보고서 통계/시설 구성 →
`report_context` → `_plan_result.html` → 서명된 HTML 스냅샷 반환 흐름을 유지합니다.
`ai_review=on`인 경우에만 `review_plan`을 호출합니다. AI 결과도 같은 HTML에 포함되어
인쇄 및 최근 5건 복원 시 재호출 없이 유지됩니다. 새 DB나 학습 배치는 없습니다.

### 파일

| 파일 | 역할 |
|---|---|
| app/ai_review/client.py | google-genai SDK 호출, 키·시간 제한·응답 크기 제한, 안전한 오류 코드 |
| app/ai_review/prompts.py | 영어 공통 System Instruction, 한국어 출력·근거 제한 |
| app/ai_review/schemas.py | 공식 JSON Schema 및 서버 응답 검증·종합 점수 계산 |
| app/ai_review/services.py | 데이터 매핑, 단일 프로세스 동시 호출 1건 제한, 실패 처리 |
| app/ai_review/tests.py | 외부 통신 없는 API·스키마·매핑 테스트 |
| app/dashboard/views.py | 화면의 실제/더미 모드 전달 |
| app/dashboard/test_planning.py | 실제 모드 모의 결과 및 스냅샷 회귀 테스트 |
| main/settings.py | 모드·모델·시간 제한·교통 포함 여부 설정 |
| static/program-planner.js | AI 선택 시 분석 중 상태 표시 |
| templates/dashboard/_planner.html | Gemini 데이터 전달 안내, 더미 모드 구분 |
| templates/dashboard/_plan_ai_review.html | 종합 점수·평가 범위·항목별 의견·강점·리스크 |
| .env.example | 빈 API 키 설정 예시 |

기존 ai_review 패키지를 확장했습니다. `google-genai==2.24.0` 공식 SDK의
`client.models.generate_content()`를 사용합니다. 모델/계정의 실제 이용 가능 여부는 운영에서 확인해야 합니다.

## 환경변수

Render Environment에 다음을 설정합니다.

```text
GEMINI_API_KEY=<Google AI Studio에서 발급한 키>
AI_REVIEW_MODE=gemini
GEMINI_MODEL=gemini-3.1-flash-lite
GEMINI_TIMEOUT_SECONDS=25
AI_REVIEW_INCLUDE_TRANSIT=false
```

키 외에는 위 값이 기본값입니다. 모델은 해당 계정에서 사용할 수 있는 Structured Output 지원
모델로 변경할 수 있습니다. 시간 제한은 1~60초 범위이며 HTTP 소켓 대기 제한입니다.
전체 처리 시간에는 CSV/교통 조회 및 렌더링도 포함되므로 동일한 총 실행 시간 보장은 아닙니다.
프로젝트 루트 `.env`를 자동으로 로드하며 기존 환경변수가 우선합니다. `.env`는 Git 제외 대상입니다. 비밀 키를 테스트 출력·URL·로그에 기록하지 않습니다.

키 누락이면 네트워크 호출 전에 종료합니다. `AI_REVIEW_MODE=dummy`에서는 키 없이 예시 결과를
사용하며 화면·인쇄물에 데모 표시를 유지합니다. 운영에서 실패했다고 더미로 대체하지 않습니다.

## 요청 구조

`GenerateContentConfig.system_instruction`에는 공통 영어 규칙을, `contents`에는
아래 구조의 JSON 문자열만 넣습니다. 데이터는 브라우저에서 직접 전송하지 않고 Django가 구성합니다.

실제 데이터가 있는 키만 전달합니다. 인구·복지·참여율·총예산·운영 회차 등
현재 데이터에 없는 항목은 null 자리표시자 없이 제외합니다.
`available_criteria`와 응답 JSON Schema도 요청마다 근거가 있는 평가 항목만 포함합니다.
시설 미지정 시 시설 적합성, 교통 자료가 없으면 교통 접근성도 제외합니다.
사용자가 작성한 프로그램 대상·기간·정원·수강료·설명은 계획 입력으로 유지합니다.

예를 들어 종목 신청 실적만 있는 요청에서는 다음과 같이 평가합니다.

```json
{
  "summary": "이용 실적을 바탕으로 검토했습니다.",
  "evaluations": {
    "sports_demand": {"score":65,"reason":"제공된 신청 실적에 근거한 참고 의견입니다.","evidence_keys":["sport_requests"]}
  },
  "strengths": [],
  "risks": [],
  "recommendations": ["실제 모집 수요를 확인하세요."],
  "limitations": ["신청 실적은 지역 전체 수요가 아닙니다."]
}
```

점수는 정수 0~100 또는 null입니다. 제공하지 않은 근거를 참조하거나 자료 없는 항목을 채점하면
전체 AI 응답을 거부하고 기본 보고서만 유지합니다. 입력 자료가 있는 항목도 AI가 판단할 수 없어 null을 반환하면 해당 상세 항목은 화면에서 제외합니다.
근거 키 검증은 문장 자체의 사실성을 완전히 보장하지는 않으므로 실제 운영 전 샘플 검토가 필요합니다.

종합 점수는 평가된 항목의 동일 가중 평균을 반올림합니다. null은 평균에서 제외하며, 평가 항목이
없으면 총점도 null입니다. 80 이상 매우 적합, 60 이상 적합, 40 이상 검토 필요, 그 미만 부적합입니다.
화면에는 평가 가능 항목 수를 함께 표시하므로 일부 자료만으로 산출된 점수임을 알 수 있습니다.

## 오류·운영 영향

키 없음, 429, HTTP 오류, 네트워크/시간 초과, 빈/잘린 응답, JSON/스키마 오류를 처리합니다.
로그에는 모드·안전한 오류 코드·경과 시간만 남기고 공급자의 오류 본문이나 사용자 입력을 출력하지 않습니다.
자동 재시도하지 않습니다. 한 프로세스에서 AI 동시 실행은 1건이고 다른 요청은 기본 보고서를 반환합니다.
이 제한은 전체 호출량/비용 상한이 아니며, 공개 운영 시 사용자별 제한·외부 API 할당량도 설정해야 합니다.

현재는 기존 preview 요청에서 동기로 호출하므로 요청 1개가 응답 대기 동안 점유됩니다. 체크하지 않으면
기존 경로 그대로이며, 실패해도 기본 보고서와 스냅샷을 생성합니다. 향후 이용량 증가 시 별도 작업 큐로
분리해야 합니다. 실제 모드에도 기존 인쇄 스타일과 HTML 이스케이프가 적용됩니다.
저장된 보고서는 그대로 복원하며 새 모델/통계로 자동 재분석하지 않습니다.

## 검증

```powershell
cd main
..\.venv-render\Scripts\python.exe manage.py test app.ai_review app.dashboard.test_planning app.planning --noinput
```

테스트는 외부 네트워크를 모의 처리합니다. 실제 키를 읽거나 유료 요청을 보내지 않습니다.
화면은 `/dashboard`에서 지역·종목·시설·프로그램을 선택하고 AI 검토를 체크해 생성합니다.
요청 URL은 `POST /dashboard/plan/preview`, 보관 복원은 `POST /dashboard/plan/restore`입니다.
API 호출의 실제 계정 권한·할당량·응답 품질은 키 설정 후 별도 확인이 필요합니다.

공식 참고: https://ai.google.dev/api/generate-content
공식 구조화 응답: https://ai.google.dev/gemini-api/docs/generate-content/structured-output

## 로컬 .env 설정

프로젝트 루트 `D:\workspace\kspo\.env`에 다음을 저장합니다.

```dotenv
GEMINI_API_KEY=발급받은_API_키
AI_REVIEW_MODE=gemini
```

이후 기존 방식으로 서버를 실행하면 됩니다. 키 변경 후 서버를 재시작합니다.
Django 설정 로딩 시 실행 위치와 관계없이 루트 `.env`를 읽습니다.
이미 설정된 환경변수(Render 포함)가 `.env`보다 우선합니다.
`.env`는 Git 제외 대상입니다. 다른 가상환경을 사용한다면
`python -m pip install -r main/requirements.txt`로 의존성을 설치합니다.

## 운영 AI 연동 로그

Render 로그에서 `AI_REVIEW`를 검색하고 같은 `request_id`로 한 요청을 추적합니다.

- `start`: 모드, 모델, 키 설정 여부, 타임아웃
- `request`: 요청 준비 완료, 평가 항목 키, 시설 수, 준비 소요 시간
- `response`: 응답 JSON 수신·파싱 완료, API 소요 시간 (내용 검증 전)
- `completed`: 응답 검증 완료, 채점 항목 수, 전체 소요 시간
- `unavailable`: 실패 단계(configuration/evidence/api/validation), 오류 코드와 예외 유형

`missing_key`는 키 누락, `busy`는 다른 분석 진행 중, `timeout`은 대기 시간 초과,
`network`는 연결 오류, `rate_limit`은 HTTP 429, `http_403` 등은 HTTP 상태 코드입니다.
`invalid_json`/`incomplete_response`는 응답 형식·완료 문제,
`validation_or_internal`은 응답 검증 또는 내부 오류입니다. 함께 기록한 stage로 구분합니다.
키 값, 요청·응답 본문, 사용자 작성 내용, 원본 오류 메시지는 기록하지 않습니다.
더미 모드의 response 로그는 모의 응답이며 실제 통신이 아닙니다.

## 공식 SDK 호출 설정

`GenerateContentConfig(response_mime_type="application/json", response_json_schema=...)`로
JSON 응답을 요청합니다. `.env`와 모델 환경변수 사용 방법은 동일합니다.
SDK 시간 제한은 밀리초 단위로 변환하며 attempts=11로 최초 호출 이후 최대 10회 재시도합니다.
429, 500, 502, 503, 504만 재시도하며 대기 간격은 1초부터 증가하여 최대 5초입니다.
25초 제한은 호출 1회 기준이므로 반복 실패 시 전체 대기가 수 분으로 늘어날 수 있습니다.
요청마다 SDK 클라이언트를 닫아 연결을 정리합니다. 실제 API 호출은 별도 확인이 필요합니다.
기존 HTTP 400 로그만으로는 요청 구조, 모델 또는 키의 문제 중 하나로 확정할 수 없습니다.
