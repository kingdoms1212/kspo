# Render 배포

저장소 루트의 `render.yaml`로 Blueprint를 생성하거나 Python Web Service에서 아래 값을 입력한다.

| 항목 | 값 |
|---|---|
| Root Directory | 비워두기 |
| Build Command | `python scripts/build_render.py` |
| Start Command | `python scripts/start_render.py` |
| Health Check Path | `/healthz/` |
| Python | `PYTHON_VERSION=3.13.15` |

## 환경변수와 도메인

- `SECRET_KEY`: Render의 Generate로 생성한 충분히 긴 임의의 값. Blueprint에서는 자동 생성한다.
- `DEBUG=false`: 운영 오류 상세 정보 노출을 끈다.
- Render 기본 도메인은 `RENDER_EXTERNAL_HOSTNAME`에서 자동으로 허용 호스트와 CSRF origin에 추가한다.
- 사용자 도메인은 Render의 Custom Domains 및 DNS를 설정하고 `ALLOWED_HOSTS=example.org,www.example.org`, `CSRF_TRUSTED_ORIGINS=https://example.org,https://www.example.org`를 추가한다. 실제 도메인으로 바꿔야 한다.
- `BATCH_REGION_KEY=seoul`, `BATCH_STORAGE_MODE=csv`: 현재 화면에 맞는 기본값이다.

환경변수는 Render 설정 화면에서 등록한다. `.env` 파일을 자동으로 읽지는 않는다.

## CSV는 빌드에서 자동 준비

수동 압축 해제나 대용량 CSV의 Git 추가는 필요 없다. `data/origin.zip`을 저장소에 포함한다.

1. 의존성을 설치하고 Django 설정을 검사한다.
2. 압축의 `origin/` 안에 있는 원본 CSV 4개만 `data/`에 해제한다. 압축 해제는 스트리밍하며, 기존 파일이 있어도 현재 압축의 내용으로 교체한다.
3. 기존 지역 배치로 `data/Batch/*_seoul.csv`와 manifest를 생성한다.
4. `collectstatic`으로 CSS, JS, 이미지, 폰트를 수집한다. 운영에서는 WhiteNoise가 제공한다.

압축의 원본은 약 1.08GB이며, 지역 CSV와 정적 파일 공간도 추가로 필요하다. 빌드 시간과 실행 메모리는 선택한 Render 인스턴스에서 확인해야 한다.
새 원본을 적용하려면 `origin.zip`을 갱신하고 다시 배포한다. 예약 배치는 배포된 원본을 다시 가공하며 외부에서 새로운 원본을 다운로드하지 않는다.
압축 누락, CSV 누락, 배치 검증 실패 시 빌드가 실패하므로 빈 데이터로 배포되지 않는다.

## 시작과 예약 실행

시작 스크립트가 Django 기본 테이블을 migrate한 뒤 Gunicorn으로 프로세스를 교체한다.
Gunicorn은 `0.0.0.0:$PORT`에서 worker 1개, thread 4개로 실행하며 worker 초기화 후 APScheduler를 시작한다.
주간 배치는 기존 설정대로 일요일 00:00(Asia/Seoul)에 실행한다. `BATCH_SCHEDULER_ENABLED=false`로 끌 수 있다.
빌드에서 CSV를 준비하므로 서버 시작 때마다 대용량 압축 해제를 반복하지 않는다.

이 구성은 서비스 인스턴스 1개를 전제로 한다. 여러 worker/인스턴스로 확장하려면 스케줄러와 데이터 저장소를 별도 서비스로 분리해야 한다.
서비스가 중지되거나 잠든 동안에는 예약 배치가 실행되지 않는다. 재배포 시에는 빌드에서 다시 생성한다.

기본 SQLite와 실행 중 생성한 로그/CSV 변경은 Render의 임시 파일시스템에 저장된다. 재배포·인스턴스 교체 후에도
관리자 계정 등 DB 변경을 보존하려면 영구 디스크를 연결하고 `SQLITE_PATH`를 그 디스크의 파일 경로로 설정하거나 PostgreSQL 연동을 별도로 구성한다.
현재 CSV 조회에는 PostgreSQL이 필요하지 않다. 기본 SQLite는 시작할 때 테이블만 초기화되며 관리자 계정을 자동 생성하지 않는다.

## 검증

### 500 오류 로그 확인

`DataGenerationPending: CSV 교체가 진행 중입니다`가 배포 직후 계속 발생했던 문제는
빌드와 실행 환경에서 CSV 수정시각이 달라지면 manifest 비교가 실패하는 데서 발생했다.
배치는 이제 CSV의 SHA-256도 manifest에 기록하며, 읽는 쪽은 수정시각이 달라도 크기와
해시가 일치하면 동일한 데이터로 인정한다. 해시는 파일이 바뀔 때만 다시 계산한다.
내용이 다른 파일은 계속 거부하므로 배치 교체 중 불완전한 데이터 적재를 방지한다.
이 수정 적용 시 기존 서버 재시작만 하지 말고 새 빌드를 포함해 재배포해야 한다.
기존 manifest에는 해시가 없으므로 `python scripts/build_render.py`로 다시 생성해야 한다.

`DEBUG=false`에서도 Django의 요청 오류와 Traceback은 stderr로 출력되어 Render의 Logs에 표시된다.
로그에는 시각, 수준, 로거 이름, 프로세스 ID, 오류 메시지와 예외 스택이 포함된다.
배치 및 APScheduler 로그도 같은 출력으로 모은다. 요청 헤더·쿠키·본문을 별도로 덤프하지 않는다.
예외 메시지 자체에는 데이터가 포함될 수 있으므로 로그 공유 전 민감한 값은 가린다.
브라우저에는 일반 500 화면을 유지하며, 원인을 보기 위해 DEBUG를 켤 필요가 없다.

배포 후 오류 페이지를 다시 열고 `ERROR django.request` 및 바로 뒤의 `Traceback`부터
마지막 예외 줄까지 확인한다. 접근 로그의 `GET ... 500` 한 줄은 원인 로그가 아니다.

```text
python main/manage.py check
python main/manage.py test app
```

실제 배포 후 `/healthz/`, `/dashboard`, `/programs`, `/facilities` 및 정적 파일 응답을 확인한다.
Gunicorn은 Linux용이며 Windows 개발 환경에서는 기존 `python main/manage.py runserver`를 사용한다.

공식 문서: https://render.com/docs/deploy-django
