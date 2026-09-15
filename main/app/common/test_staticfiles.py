from pathlib import Path
import re
from urllib.parse import urljoin, urlparse

from django.conf import settings
from django.contrib.staticfiles import finders
from django.contrib.staticfiles.views import serve
from django.test import RequestFactory, SimpleTestCase, override_settings


class SharedThemeTests(SimpleTestCase):
    @override_settings(DEBUG=True)
    def test_font_css_urls_resolve_to_served_static_files(self):
        css = Path(finders.find('fonts.css')).read_text(encoding='utf-8')
        urls = re.findall(r"url\(['\"]?([^'\")]+)", css)
        self.assertEqual(len(urls), 9)
        for url in urls:
            resolved = urlparse(urljoin('/static/fonts.css', url)).path
            with self.subTest(url=url):
                self.assertTrue(resolved.startswith('/static/'), resolved)
                response = serve(RequestFactory().get(resolved), resolved.removeprefix('/static/'))
                self.assertEqual(response.status_code, 200)
                response.close()

    def test_theme_uses_root_source(self):
        self.assertEqual(Path(finders.find('theme/sport-insight-colors.css')),
                         settings.BASE_DIR.parent / 'theme' / 'sport-insight-colors.css')

    @override_settings(DEBUG=True)
    def test_local_font_url_is_served(self):
        for weight in ('Thin', 'ExtraLight', 'Light', 'Regular', 'Medium',
                       'SemiBold', 'Bold', 'ExtraBold', 'Black'):
            with self.subTest(weight=weight):
                path = f'fonts/NotoSansKR-{weight}.ttf'
                response = serve(RequestFactory().get('/static/' + path), path)
                self.assertEqual(response.status_code, 200)
                response.close()
