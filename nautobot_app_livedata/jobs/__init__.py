"""Job registration for nautobot_app_livedata."""

from nautobot.apps.jobs import register_jobs

from nautobot_app_livedata.jobs.jobs import (
    EnforceDefaultJobQueueJob,
    LivedataCleanupJobResultsJob,
    LivedataQueryJob,
)

registered_job_classes = [
    LivedataQueryJob,
    LivedataCleanupJobResultsJob,
    EnforceDefaultJobQueueJob,
]

# Preserve historical job_class_path values so queued jobs keep working.
for job_class in registered_job_classes:
    job_class.__module__ = __name__

register_jobs(*registered_job_classes)

__all__ = [
    "EnforceDefaultJobQueueJob",
    "LivedataCleanupJobResultsJob",
    "LivedataQueryJob",
    "registered_job_classes",
]
