from unittest.mock import patch

from django.core import signing
from django.test import Client, SimpleTestCase

from ..facilities.tests import facility
from .planning import candidates, facility_token


class PlanningTests(SimpleTestCase):
    def setUp(self):
        self.row = facility(id='facility-1', name='농구센터', region='서울특별시',
                            district='중구', facility_type='농구장', state='정상운영')
        self.rows = [self.row, self.row._replace(id='facility-2', district='강남구'),
                     self.row._replace(id='facility-3', state='폐업'),
                     self.row._replace(id='facility-4', facility_type='종합체육관'),
                     self.row._replace(id='facility-5', region='부산광역시')]
        self.enterContext(patch('app.dashboard.planning.facilities.facilities', return_value=self.rows))
        self.enterContext(patch('app.dashboard.planning.dashboard_data', return_value={
            'region_options': ['서울', '부산'],
            'region_district_options': {'서울': ['중구', '강남구']},
            'facilities': 5, 'courses': 10, 'requests': 120,
            'period': ['2025-01 ~ 2025-12'], 'sports': [('농구', 120)],
        }))
        self.scope = dict(region='서울', district='중구', sport='농구')
        self.payload = dict(**self.scope, name='청소년 농구', capacity='20', fee='0',
                            fee_unit='월', description='기초 농구 수업',
                            facilities=[facility_token(self.row)])

    def test_candidates_require_region_sport_evidence_and_operating_state(self):
        self.assertEqual(candidates(**self.scope), [self.row])
        self.assertEqual(len(candidates('서울', '', '농구')), 2)
        self.assertEqual(candidates('', '', '농구'), [])

    def test_list_is_paginated_searchable_and_does_not_load_transport(self):
        with patch('app.dashboard.plan_views.facility_transit') as transit:
            response = self.client.get('/dashboard/plan/facilities', self.scope)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['count'], 1)
        self.assertEqual(response.json()['rows'][0]['id'], self.row.id)
        transit.assert_not_called()
        empty = self.client.get('/dashboard/plan/facilities', dict(self.scope, q='없는시설'))
        self.assertEqual(empty.json()['count'], 0)
        self.assertIn('no-store', response['Cache-Control'])

    def test_list_rejects_invalid_scope(self):
        for change in ({'region': ''}, {'district': '해운대구'}, {'sport': 'unknown'}):
            with self.subTest(change=change):
                result = self.client.get('/dashboard/plan/facilities', dict(self.scope, **change))
                self.assertEqual(result.status_code, 400)

    def test_details_only_allow_a_facility_in_current_scope(self):
        with patch('app.dashboard.plan_views.facility_transit', return_value={'reason': 'not_public'}) as transit:
            good = self.client.get('/dashboard/plan/facility', dict(self.scope, id=self.row.id))
            bad = self.client.get('/dashboard/plan/facility', dict(self.scope, id='facility-2'))
        self.assertContains(good, '농구센터')
        self.assertContains(good, '인접 대중교통')
        self.assertEqual(bad.status_code, 404)
        transit.assert_called_once_with(self.row)

    def test_preview_accepts_free_program_without_database_or_session(self):
        response = self.client.post('/dashboard/plan/preview', self.payload)
        self.assertContains(response, '청소년 농구')
        self.assertContains(response, '합계 20명')
        self.assertContains(response, '0원 / 월')
        self.assertContains(response, '120명')
        self.assertIn('no-store', response['Cache-Control'])
        self.assertNotIn('sessionid', response.cookies)

    def test_preview_escapes_user_content(self):
        response = self.client.post('/dashboard/plan/preview', dict(self.payload, name='<script>alert(1)</script>'))
        self.assertContains(response, '&lt;script&gt;')
        self.assertNotContains(response, '<script>alert')

    def test_invalid_numbers_blank_names_and_units_rejected(self):
        for change in ({'capacity': '0'}, {'capacity': '1.5'}, {'fee': '-1'},
                       {'name': '  '}, {'description': ' '}, {'fee_unit': '년'}):
            with self.subTest(change=change):
                response = self.client.post('/dashboard/plan/preview', dict(self.payload, **change))
                self.assertEqual(response.status_code, 400)

    def test_missing_duplicate_tampered_or_wrong_region_facilities_rejected(self):
        for tokens in ([], self.payload['facilities'] * 2, ['tampered'], [facility_token(self.rows[-1])]):
            with self.subTest(tokens=tokens):
                result = self.client.post('/dashboard/plan/preview', dict(self.payload, facilities=tokens))
                self.assertEqual(result.status_code, 400)

    def test_changed_source_identity_and_expired_token_rejected(self):
        token = facility_token(self.row._replace(name='예전 시설'))
        self.assertEqual(self.client.post('/dashboard/plan/preview', dict(self.payload, facilities=[token])).status_code, 400)
        with patch('app.dashboard.planning.signing.loads', side_effect=signing.SignatureExpired('expired')):
            self.assertEqual(self.client.post('/dashboard/plan/preview', self.payload).status_code, 400)

    def test_csrf_and_method_are_enforced(self):
        self.assertEqual(Client(enforce_csrf_checks=True).post('/dashboard/plan/preview', self.payload).status_code, 403)
        self.assertEqual(self.client.get('/dashboard/plan/preview').status_code, 405)

    def test_operating_dates_and_target_are_included_and_order_validated(self):
        data = dict(self.payload, target='초등학생', start='2026-10-01', end='2026-12-31')
        response = self.client.post('/dashboard/plan/preview', data)
        self.assertContains(response, '초등학생')
        self.assertContains(response, '2026-10-01 ~ 2026-12-31')
        data['end'] = '2026-09-01'
        self.assertEqual(self.client.post('/dashboard/plan/preview', data).status_code, 400)
