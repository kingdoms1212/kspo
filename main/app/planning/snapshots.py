"""브라우저에 보관하는 설계서 결과의 서명·검증 규약. HTTP/CSV에 의존하지 않는다."""
from django.core import signing

# 기존 localStorage에 보관된 결과를 계속 열 수 있도록 규약을 유지한다.
SNAPSHOT_SALT = 'program-plan-result-v1'
SNAPSHOT_LIMIT = 1_000_000


class InvalidSnapshot(ValueError):
    """화면에 전달할 수 있는 보관 결과 검증 오류."""


def encode_snapshot(html, summary):
    """서버 템플릿에서 이스케이프된 결과만 전달한다. 크기 초과 시 보관만 생략한다."""
    token = signing.dumps({'version': 1, 'html': html, 'summary': summary},
                          salt=SNAPSHOT_SALT, compress=True)
    return token if len(token) <= SNAPSHOT_LIMIT else None


def decode_snapshot(token):
    if not token or len(token) > SNAPSHOT_LIMIT:
        raise InvalidSnapshot('저장된 계획서를 읽을 수 없습니다.')
    try:
        snapshot = signing.loads(token, salt=SNAPSHOT_SALT)
        if (not isinstance(snapshot, dict) or snapshot.get('version') != 1
                or not isinstance(snapshot.get('html'), str)
                or not isinstance(snapshot.get('summary'), dict)):
            raise ValueError('Invalid snapshot')
    except (signing.BadSignature, ValueError, TypeError) as error:
        raise InvalidSnapshot('저장된 계획서가 손상되었거나 서버 설정이 변경되어 열 수 없습니다.') from error
    return {'html': snapshot['html'], 'summary': snapshot['summary']}
