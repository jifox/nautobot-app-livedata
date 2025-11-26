"""Tests covering Nautobot App Livedata configuration defaults."""

from django.conf import settings
from nautobot.apps.testing import TestCase


class PluginConfigTests(TestCase):
    """Validate plugin configuration wiring."""

    def test_default_task_queue_present(self):
        """Ensure the task queue setting always has a value."""
        config = settings.PLUGINS_CONFIG.get("nautobot_app_livedata", {})
        self.assertIn("query_job_task_queue", config)
        self.assertTrue(config["query_job_task_queue"])
