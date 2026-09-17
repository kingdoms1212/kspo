from unittest import TestCase
from unittest.mock import MagicMock, patch

from django.test import override_settings

from . import scheduler as scheduler_module


class RegionBatchSchedulerTests(TestCase):
    def tearDown(self):
        scheduler_module._scheduler = None

    @override_settings(
        TIME_ZONE="Asia/Seoul",
        BATCH_REGION_KEY="seoul",
        BATCH_SCHEDULE={"day_of_week": "sun", "hour": 0, "minute": 0},
    )
    @patch.object(scheduler_module, "CronTrigger")
    @patch.object(scheduler_module, "BackgroundScheduler")
    def test_scheduler_uses_configured_weekly_time(self, scheduler_class, trigger_class):
        instance = MagicMock()
        instance.running = False
        scheduler_class.return_value = instance
        trigger = trigger_class.return_value

        result = scheduler_module.start_scheduler()

        trigger_class.assert_called_once_with(
            day_of_week="sun", hour=0, minute=0, timezone="Asia/Seoul"
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
