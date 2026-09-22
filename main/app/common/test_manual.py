from django.template import Context, Template
from django.test import SimpleTestCase


class ManualControlTests(SimpleTestCase):
    def test_manual_contains_each_screen_guide_and_always_starts_with_overview(self):
        output = Template(
            "{% include 'components/manual_control.html' %}"
        ).render(Context({"page": "programs"}))

        self.assertIn("이용 가이드", output)
        self.assertIn('data-default-section="overview"', output)
        self.assertIn('src="/static/image/logo/logo.png"', output)
        self.assertIn("프로그램 설계", output)
        self.assertIn("프로그램 현황", output)
        self.assertIn("시설 현황", output)
        self.assertIn("데이터 최신화", output)
        self.assertIn("데이터 기준", output)
        self.assertEqual(output.count('class="manual-nav-number"'), 6)
        for number in ("01", "02", "03", "04", "05", "06"):
            self.assertIn(f'<span class="manual-nav-number">{number}</span>', output)
        self.assertNotIn("화면별 사용 방법과 데이터 기준", output)
        self.assertNotIn("프로그램 설계 열기", output)
        self.assertNotIn("프로그램 현황 열기", output)
        self.assertNotIn("시설 현황 열기", output)
        self.assertIn('src="/static/manual.js?', output)
