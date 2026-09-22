# AI 공급자 구조와 환경 설정 가이드

## 이번 변경

지역 현황 요약과 프로그램 검토가 동일한 공급자 인터페이스를 사용합니다.
화면 URL, 검토 토큰 서명 형식과 유효기간, 최근 계획서 스냅샷 형식은 유지합니다.
지역 요약 캐시에는 공급자 식별자를 추가했으므로 배포 후 최초 분석은 다시 호출될 수 있습니다.

```text
Dashboard View
  ├─ 프로그램 검토 → services.py
  └─ 지역 요약 → region_service.py (24시간 파일 캐시)
                   ↓
           factory.create_provider()
                   ↓
 AIRequest → AIProvider.generate() → AIResponse
                   ↓
       providers/gemini.py 또는 dummy.py
                   ↓
         공통 검증 · 점수 · 토큰 · 보고서
```

- `contracts.py`: 요청(task, instruction, evidence, schema, request_id), 응답(data, provider, model).
- `factory.py`: 환경 설정 호환, 공급자 레지스트리, 선택 SDK 지연 로딩.
- `errors.py`: 공급자와 관계없는 안전한 오류 코드.
- `providers/gemini.py`: SDK 호출·JSON 파싱·API 오류 변환·SDK 재시도.
- `providers/dummy.py`: 외부 호출 없이 두 업무의 동일한 응답 형식을 반환.
- 업무 서비스는 응답 검증과 점수 계산을 담당하며 SDK를 직접 참조하지 않습니다.
- 재시도는 어댑터에서만 수행합니다. 공통 서비스는 중복 재시도하지 않습니다.
- 공급자별 SDK의 응답 형식·지원 스키마 차이는 해당 어댑터에서 변환합니다.

## 기존 환경 그대로 배포해도 되나요?

**네. 기존 Gemini 환경변수는 계속 지원합니다.** 실제 키가 든 로컬 `.env`는 이번 작업에서
수정하지 않았습니다. `.env.example`만 새 공통 설정 예시로 갱신했습니다.
추가 패키지나 DB 마이그레이션은 필요하지 않습니다. 기존 requirements.txt를 사용합니다.

| 권장 설정 | 기본값 / 의미 | 기존 설정과 관계 |
|---|---|---|
| AI_MODE | live / dummy | 미지정 시 AI_REVIEW_MODE=gemini → live, dummy → dummy |
| AI_PROVIDER | gemini | 현재 실제 공급자는 gemini만 구현 |
| AI_MODEL | gemini-3.1-flash-lite | 미지정·Gemini 선택 시 GEMINI_MODEL 사용 |
| AI_TIMEOUT_SECONDS | 25 | 미지정 시 GEMINI_TIMEOUT_SECONDS 사용; 1~60초 |
| AI_MAX_RETRIES | 10 | 0~10; 최초 호출 별도, 10이면 최대 11회 시도 |
| GEMINI_API_KEY | 실제 키 | 이름 변경 없음 |
| AI_REVIEW_INCLUDE_TRANSIT | false | 기존 선택적 교통 분석 설정 유지 |

동일 설정에 새 이름과 기존 이름이 함께 있으면 새 이름을 우선합니다.
예를 들어 AI_MODE=live가 있으면 AI_REVIEW_MODE=dummy는 적용되지 않습니다.
환경변수 이름별로 OS/Render에 이미 있는 값이 `.env`보다 우선합니다.
다른 이름을 쓰는 기존 변수와 새 변수 사이에는 위의 새 설정 우선 규칙이 적용됩니다.
혼동을 피하려면 이행 후 기존 이름은 정리하는 것을 권장합니다.

## 로컬 .env 권장 예시

프로젝트 루트 `D:\workspace\kspo\.env`에 아래 설정을 사용합니다.
**기존 API 키를 지우거나 예시 문자열로 덮어쓰지 마세요.**

```dotenv
AI_MODE=live
AI_PROVIDER=gemini
AI_MODEL=gemini-3.1-flash-lite
AI_TIMEOUT_SECONDS=25
AI_MAX_RETRIES=10
GEMINI_API_KEY=실제_발급받은_키
AI_REVIEW_INCLUDE_TRANSIT=false
```

저장 후 개발 서버를 재시작합니다. `.env`는 Git에 추가하지 않습니다.
외부 호출 없이 확인할 때는 AI_MODE=dummy로 변경합니다. 더미에는 SDK와 키가 필요하지 않으며
화면에는 데모 표시가 유지됩니다. 실제 호출 실패를 더미 결과로 대체하지 않습니다.

## Render 설정

1. 변경 코드를 연결된 배포 브랜치에 반영하고 배포합니다. 이번 작업에서 배포는 수행하지 않습니다.
2. Render Dashboard → 해당 Web Service → Environment에서 위 Key/Value를 등록하거나 수정합니다.
3. GEMINI_API_KEY 값은 기존 값을 유지합니다. Value에는 따옴표 없이 입력합니다.
4. 새 공통 설정으로 이행했다면 AI_REVIEW_MODE, GEMINI_MODEL, GEMINI_TIMEOUT_SECONDS는 제거해도 됩니다.
5. 환경변수 변경은 Save and deploy로 반영합니다. Save only는 다음 배포 전까지 반영되지 않습니다.
6. AI 요약 또는 검토를 호출하고 로그에서 mode=live, provider=gemini, model, key_configured=True를 확인합니다.

기존 Gemini 설정만 유지해도 동작하므로 Render 변수 변경은 필수 사항이 아닙니다.
key_configured=True는 값이 있다는 뜻이며 실제 권한·할당량은 API 응답으로 확인합니다.
API 키와 사용자 본문은 로그에 출력하지 않습니다.

## GPT·Claude 추가 절차

이번 변경은 교체 구조를 마련한 것이며 OpenAI·Anthropic 실호출 어댑터는 아직 구현하지 않았습니다.
AI_PROVIDER만 openai/anthropic으로 바꾸면 unsupported_provider로 안전하게 실패합니다.

1. providers/openai.py 또는 providers/anthropic.py에 generate(AIRequest) → AIResponse를 구현합니다.
2. 각 SDK의 구조화 응답·시간 제한·재시도를 config에 맞게 변환합니다.
3. 공급자 오류를 ReviewError의 공통 코드로 변환하고 비밀·본문을 로그에서 제외합니다.
4. factory.PROVIDERS에 공급자 ID, 모듈 경로, 클래스, 키 환경변수명을 등록합니다.
5. 필요한 SDK를 의존성에 추가하고 공통 계약·예외 테스트를 작성합니다.
6. AI_PROVIDER, AI_MODEL, 해당 공급자의 API 키를 설정합니다.

자동으로 다른 공급자에 재전송하지 않습니다. UI와 보고서 점수 계산은 공급자 어댑터에 넣지 않습니다.

## 검증·운영 한계

테스트는 SDK 응답을 모의 처리합니다. 실제 키로 외부 API를 호출하지 않았습니다.
서명된 과거 계획서 HTML은 그대로 복원되고 검토 토큰의 기존 salt·형식도 유지됩니다.
최대 10회 재시도는 기존과 동일하며 전체 처리 시간은 수 분이 될 수 있습니다.
캐시와 동시 호출 제한은 여러 서버·프로세스 사이에 전역 공유되지 않습니다.
