import json
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


class OfflineMapAssetTests(SimpleTestCase):
    """The map draws on closed government networks, so nothing is fetched from
    a CDN at runtime and the boundary files cannot drift on someone else's
    branch. Copies live in `static/vendor/`."""

    VENDOR = ('vendor/echarts.min.js',
              'vendor/skorea_provinces_geo_simple.json',
              'vendor/skorea_municipalities_geo_simple.json')

    @override_settings(DEBUG=True)
    def test_vendored_map_assets_are_served(self):
        for path in self.VENDOR:
            with self.subTest(path=path):
                response = serve(RequestFactory().get('/static/' + path), path)
                self.assertEqual(response.status_code, 200)
                response.close()

    def test_map_script_requests_no_external_host(self):
        source = Path(finders.find('region-map.js')).read_text(encoding='utf-8')
        code = re.sub(r'/\*.*?\*/', '', source, flags=re.S)
        code = re.sub(r'(?m)^\s*//.*$', '', code)
        self.assertEqual(re.findall(r'https?://\S+', code), [])

    def test_boundary_codes_let_the_drilldown_match_every_province(self):
        # region-map.js selects a province's municipalities by the first two
        # digits of the KOSTAT code, so the two files must agree on that key.
        def features(name):
            path = finders.find('vendor/skorea_' + name + '_geo_simple.json')
            return json.loads(Path(path).read_text(encoding='utf-8'))['features']

        provinces, municipalities = features('provinces'), features('municipalities')
        self.assertEqual(len(provinces), 17)
        self.assertEqual(len(municipalities), 251)
        self.assertEqual({row['properties']['code'][:2] for row in municipalities},
                         {row['properties']['code'] for row in provinces})
