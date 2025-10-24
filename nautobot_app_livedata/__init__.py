"""App declaration for nautobot_app_livedata."""

# Metadata is inherited from Nautobot. If not including Nautobot in the environment, this should be added
from importlib import metadata

from nautobot.apps import nautobot_database_ready, NautobotAppConfig

from .signals import nautobot_database_ready_callback  # pylint: disable=unused-import, wrong-import-position

__version__ = metadata.version(__name__)


class LivedataConfig(NautobotAppConfig):
    """App configuration for the nautobot_app_livedata app."""

    name = "nautobot_app_livedata"  # Raw app name; same as the app's source directory
    verbose_name = "Nautobot App Livedata"
    version = __version__
    author = "Josef Fuchs"
    description = "Nautobot App Livedata is a Nautobot app that provides a live view of the network data.."
    required_settings = [
        "query_job_name",
    ]
    min_version = "2.4.0"
    max_version = "2.9999"
    default_settings = {}
    caching_config = {}
    docs_view_name = "plugins:nautobot_app_livedata:docs"

    def ready(self):
        """Callback when this app is loaded."""
        super().ready()
        # Connect the nautobot_database_ready_callback() function to the nautobot_database_ready signal.
        # This is by no means a requirement for all Apps, but is a useful way for an App to perform
        # database operations such as defining CustomFields, Relationships, etc. at the appropriate time.
        nautobot_database_ready.connect(nautobot_database_ready_callback, sender=self)


config = LivedataConfig  # pylint:disable=invalid-name
