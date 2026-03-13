"""Job registration for nautobot_app_livedata."""

from nautobot.apps.jobs import register_jobs

from nautobot_app_livedata.jobs.jobs import (
    EnforceDefaultJobQueueJob,
    LivedataCleanupJobResultsJob,
    LivedataQueryJob,
)

# Nautobot expects an iterable named `jobs` in the jobs module
jobs = [
    LivedataQueryJob,
    LivedataCleanupJobResultsJob,
    EnforceDefaultJobQueueJob,
]

# Preserve historical job_class_path values so queued jobs keep working.
for job_class in jobs:
    job_class.__module__ = __name__

register_jobs(*jobs)

__all__ = [
    "EnforceDefaultJobQueueJob",
    "LivedataCleanupJobResultsJob",
    "LivedataQueryJob",
    "jobs",
]
