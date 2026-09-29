from unittest import TestCase
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from unittest.mock import MagicMock, patch

from django.test import override_settings
from django.conf import settings
from apscheduler.triggers.cron import CronTrigger

from . import scheduler as scheduler_module


class RegionBatchSchedulerTests(TestCase):
    def test_default_schedule_fires_monthly_at_one_am_korean_time(self):
        self.assertEqual(settings.TIME_ZONE, "Asia/Seoul")
        trigger = CronTrigger(**settings.BATCH_SCHEDULE, timezone=settings.TIME_ZONE)
        zone = ZoneInfo("Asia/Seoul")
        now = datetime(2026, 9, 28, 12, tzinfo=zone)
        previous = None
        for year, month in [(2026, 10), (2026, 11), (2026, 12), (2027, 1), (2027, 2), (2027, 3)]:
            expected = datetime(year, month, 1, 1, tzinfo=zone)
            actual = trigger.get_next_fire_time(previous, now)
            self.assertEqual(actual, expected)
            previous = actual
            now = actual + timedelta(seconds=1)

    def tearDown(self):
        scheduler_module._scheduler = None

    @override_settings(
        TIME_ZONE="Asia/Seoul",
        BATCH_REGION_KEY="seoul",
        BATCH_SCHEDULE={"day": 15, "hour": 2, "minute": 30},
    )
    @patch.object(scheduler_module, "CronTrigger")
    @patch.object(scheduler_module, "BackgroundScheduler")
    def test_scheduler_uses_configured_monthly_time(self, scheduler_class, trigger_class):
        instance = MagicMock()
        instance.running = False
        scheduler_class.return_value = instance
        trigger = trigger_class.return_value

        result = scheduler_module.start_scheduler()

        trigger_class.assert_called_once_with(
            day=15, hour=2, minute=30, timezone="Asia/Seoul"
        )
        instance.add_job.assert_called_once_with(
            scheduler_module._run_region_batch,
            trigger=trigger,
            id="regional_data_batch",
            replace_existing=True,
            coalesce=True,
            max_instances=1,
            misfire_grace_time=24 * 60 * 60,
        )
        instance.start.assert_called_once_with()
        self.assertIs(result, instance)

    @patch.object(scheduler_module, "BackgroundScheduler")
    def test_running_scheduler_is_reused(self, scheduler_class):
        instance = MagicMock()
        instance.running = True
        scheduler_module._scheduler = instance

        result = scheduler_module.start_scheduler()

        self.assertIs(result, instance)
        scheduler_class.assert_not_called()
