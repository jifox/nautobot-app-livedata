"""Tests for the EnforceDefaultJobQueueJob helper."""

from __future__ import annotations

import logging

from nautobot.apps.testing import TestCase
from nautobot.extras.choices import JobQueueTypeChoices
from nautobot.extras.models import Job as JobModel, JobQueue

from nautobot_app_livedata.jobs.jobs import EnforceDefaultJobQueueJob


class EnforceDefaultJobQueueJobTestCase(TestCase):
    """Verify that the queue alignment job enforces the default queue."""

    databases = ("default", "job_logs")

    def setUp(self) -> None:
        """Create baseline queues and jobs for each test."""
        super().setUp()
        self.default_queue, _ = JobQueue.objects.get_or_create(
            name="default",
            defaults={"queue_type": JobQueueTypeChoices.TYPE_CELERY},
        )
        self.alt_queue = JobQueue.objects.create(name="alt", queue_type=JobQueueTypeChoices.TYPE_CELERY)
        self.job = JobModel.objects.create(
            module_name="test.module",
            job_class_name="SampleJob",
            grouping="Tests",
            name="Sample Job",
            description="",
            default_job_queue=self.alt_queue,
            enabled=True,
        )
        self.job.job_queues.set([self.alt_queue])
        self.runner = EnforceDefaultJobQueueJob()
        self.runner.logger = logging.getLogger(__name__)

    def test_aligns_jobs_to_default_queue(self) -> None:
        """Running in non dry-run mode assigns the default queue everywhere."""
        summary = self.runner.run(dry_run=False)
        self.job.refresh_from_db()
        self.assertIn("updated", summary.lower())
        self.assertEqual(self.job.default_job_queue, self.default_queue)
        self.assertEqual(list(self.job.job_queues.all()), [self.default_queue])
        self.assertTrue(self.job.default_job_queue_override)
        self.assertTrue(self.job.job_queues_override)

    def test_dry_run_reports_without_changes(self) -> None:
        """Dry-run mode leaves the database untouched."""
        summary = self.runner.run(dry_run=True)
        self.job.refresh_from_db()
        self.assertIn("would update", summary.lower())
        self.assertEqual(self.job.default_job_queue, self.alt_queue)
        self.assertEqual(list(self.job.job_queues.all()), [self.alt_queue])

    def test_creates_default_queue_when_missing(self) -> None:
        """The job creates and normalizes the default queue if it does not exist."""
        JobQueue.objects.filter(name="default").update(name="default-renamed")
        self.assertFalse(JobQueue.objects.filter(name="default").exists())

        summary = self.runner.run(dry_run=False)
        self.assertIn("updated", summary.lower())
        created_queue = JobQueue.objects.get(name="default")
        self.assertEqual(created_queue.queue_type, JobQueueTypeChoices.TYPE_CELERY)

    def test_accepts_explicit_queue_selection(self) -> None:
        """Operators can provide an explicit queue instance to enforce."""
        custom_queue = JobQueue.objects.create(name="custom", queue_type=JobQueueTypeChoices.TYPE_KUBERNETES)
        self.runner.run(dry_run=False, job_queue=custom_queue)
        custom_queue.refresh_from_db()
        self.assertEqual(custom_queue.queue_type, JobQueueTypeChoices.TYPE_CELERY)
        self.job.refresh_from_db()
        self.assertEqual(self.job.default_job_queue, custom_queue)
        self.assertEqual(list(self.job.job_queues.all()), [custom_queue])
