"""Policy caching and dialog regressions.

The crawler itself lives in app.common and is covered there; here the external
read is mocked so only this module's caching and rendering are under test.
"""
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings
from django.urls import resolve, reverse

from ..common import crawler
from ..common.tests import SOURCE
from . import models, views

ONE = [{'title': '테스트 정책', 'url': 'https://example.test/site/policy/view.jsp'}]


@override_settings(POLICY_SOURCE=SOURCE)
class PolicyCacheTests(SimpleTestCase):
    def setUp(self):
        models.cache_clear()
        self.addCleanup(models.cache_clear)

    def test_a_success_is_read_once_and_reused(self):
        with patch('app.policies.models.crawler.crawl', return_value=(ONE, '')) as read:
            models.policies()
            models.policies()
        read.assert_called_once()

    def test_force_bypasses_the_cache(self):
        with patch('app.policies.models.crawler.crawl', return_value=(ONE, '')) as read:
            models.policies()
            models.policies(force=True)
        self.assertEqual(read.call_count, 2)

    def test_a_failure_is_retried_sooner_than_a_success_is_refreshed(self):
        # A site that recovers must show up on the next open, not 15 minutes later.
        with patch('app.policies.models.crawler.crawl', return_value=([], 'down')):
            models.policies()
        with patch('app.policies.models.time.monotonic',
                   return_value=models._cache['at'] + SOURCE['retry_seconds'] + 1), \
             patch('app.policies.models.crawler.crawl', return_value=(ONE, '')) as read:
            result = models.policies()
        read.assert_called_once()
        self.assertEqual(result['error'], '')

    def test_the_source_name_and_address_come_from_settings(self):
        with patch('app.policies.models.crawler.crawl', return_value=(ONE, '')):
            result = models.policies()
        self.assertEqual(result['source'], SOURCE['name'])
        self.assertEqual(result['source_url'], crawler.list_url(SOURCE))


@override_settings(POLICY_SOURCE=SOURCE)
class PolicyViewTests(SimpleTestCase):
    def setUp(self):
        models.cache_clear()
        self.addCleanup(models.cache_clear)

    def _get(self, **extra):
        with patch('app.policies.models.crawler.crawl', return_value=(ONE, '')):
            return self.client.get(reverse('policies'), **extra)

    def test_route_resolves_and_the_dialog_gets_only_the_fragment(self):
        self.assertIs(resolve('/policies').func, views.policies)
        fragment = self._get(HTTP_HX_REQUEST='true')
        self.assertTemplateUsed(fragment, 'policies/_list.html')
        self.assertTemplateNotUsed(fragment, 'base.html')
        self.assertContains(fragment, '최신 정책 1건')
        self.assertContains(fragment, 'data-close-dialog')

    def test_navigating_to_the_url_renders_a_full_page_without_a_close_button(self):
        page = self._get()
        self.assertTemplateUsed(page, 'policies/index.html')
        self.assertTemplateUsed(page, 'base.html')
        self.assertContains(page, '최신 정책 1건')
        self.assertNotContains(page, 'data-close-dialog')

    def test_every_screen_offers_the_button_and_hosts_the_dialog(self):
        with patch('app.dashboard.models.usage_snapshot',
                   return_value={'areas': [], 'months': [], 'ledger_rows': 0,
                                 'unidentified': 0, 'source': 'x.csv'}):
            response = self.client.get('/dashboard')
        self.assertContains(response, 'hx-target="#policy-dialog-body"')
        self.assertContains(response, 'id="policy-dialog"')
        # The listing is only read when the dialog is opened.
        self.assertNotContains(response, '최신 정책')

    def test_an_unreachable_source_shows_a_message_and_the_original_link(self):
        with patch('app.policies.models.crawler.crawl', return_value=([], crawler.NETWORK_ERROR)):
            fragment = self.client.get(reverse('policies'), HTTP_HX_REQUEST='true')
        self.assertContains(fragment, crawler.NETWORK_ERROR)
        self.assertContains(fragment, 'https://example.test/site/policy/list.jsp?pType=07')
        self.assertEqual(fragment.status_code, 200)

    def test_titles_from_the_source_are_escaped(self):
        with patch('app.policies.models.crawler.crawl',
                   return_value=([{'title': '<script>x</script>',
                                   'url': 'https://example.test/site/policy/v'}], '')):
            fragment = self.client.get(reverse('policies'), HTTP_HX_REQUEST='true')
        self.assertContains(fragment, '&lt;script&gt;')
        self.assertNotContains(fragment, '<script>x</script>')
