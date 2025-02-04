"""Utility functions for the Livedata API."""

import logging

logger = logging.getLogger(__name__)

# Check that napalm is installed
try:
    import napalm  # pylint: disable=unused-import # noqa: F401
except ImportError:
    raise ImportError(  # pylint: disable=raise-missing-from
        "ERROR NAPALM is not installed. Please see the documentation for instructions."
    )

# Check that celery worker is installed
try:
    from nautobot.core.celery import nautobot_task  # pylint: disable=unused-import,ungrouped-imports # noqa: F401

    CELERY_WORKER = True
except ImportError as err:
    print("ERROR in livedata_device_worker: Celery is not Installed.")
    logger.error(  # pylint: disable=raise-missing-from  # type: ignore
        "ERROR in livedata_device_worker: Celery is not Installed."
    )
    raise ImportError from err
