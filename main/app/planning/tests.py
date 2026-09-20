"""패키지 분리 전 브라우저 보관 규약과의 호환성을 검증한다."""
from unittest.mock import patch

from django.core import signing
from django.test import SimpleTestCase

from .snapshots import decode_snapshot, encode_snapshot


class SnapshotCompatibilityTests(SimpleTestCase):
    def test_existing_v1_snapshot_still_opens_at_original_url(self):
        # 이전 plan_views가 발행하던 규약을 새 모듈 상수에 의존하지 않고 고정한다.
        payload = {'version': 1, 'html': '<article>기존 설계서</article>',
                   'summary': {'name': '기존 설계서', 'created': '2026-09-20T09:00:00+09:00'}}
        with patch('time.time', return_value=1_700_000_000):
            old_token = signing.dumps(payload, salt='program-plan-result-v1', compress=True)
        response = self.client.post('/dashboard/plan/restore', {'snapshot': old_token})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'html': payload['html'], 'summary': payload['summary']})

    def test_new_snapshot_keeps_old_schema_and_signature(self):
        summary = {'name': '설계서', 'capacity': 20, 'fee': 0, 'facilities': ['시설']}
        token = encode_snapshot('<article>설계서</article>', summary)
        legacy_payload = signing.loads(token, salt='program-plan-result-v1')
        self.assertEqual(legacy_payload, {'version': 1, 'html': '<article>설계서</article>', 'summary': summary})
        self.assertEqual(decode_snapshot(token)['summary'], summary)

    def test_oversize_snapshot_skips_storage_without_failing_preview(self):
        with patch('app.planning.snapshots.SNAPSHOT_LIMIT', 10):
            self.assertIsNone(encode_snapshot('<article>설계서</article>', {'name': '설계서'}))
