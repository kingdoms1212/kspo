from django.template import Context, Template
from django.test import SimpleTestCase


class ManualControlTests(SimpleTestCase):
    def test_manual_contains_each_screen_guide_and_uses_current_page(self):
        output = Template(
            "{% include 'components/manual_control.html' %}"
        ).render(Context({"page": "programs"}))

        self.assertIn("이용 가이드", output)
        self.assertIn('data-default-section="programs"', output)
        self.assertIn("프로그램 설계", output)
        self.assertIn("프로그램 현황", output)
        self.assertIn("시설 현황", output)
        self.assertIn("데이터 최신화", output)
        self.assertIn("데이터 기준", output)
        self.assertIn('src="/static/manual.js?', output)
