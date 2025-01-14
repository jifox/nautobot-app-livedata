"""App declaration for nautobot_app_livedata."""

# Metadata is inherited from Nautobot. If not including Nautobot in the environment, this should be added
from importlib import metadata

from nautobot.apps import NautobotAppConfig

__version__ = metadata.version(__name__)


class LivedataConfig(NautobotAppConfig):
    """App configuration for the nautobot_app_livedata app."""

    name = "nautobot_app_livedata"
    verbose_name = "Nautobot App Livedata"
    version = __version__
    author = "Josef Fuchs"
    description = "Nautobot App Livedata is a Nautobot app that provides a live view of the network data.."
    base_url = "livedata"
    required_settings = []
    min_version = "2.0.0"
    max_version = "2.9999"
    default_settings = {}
    caching_config = {}
    docs_view_name = "plugins:nautobot_app_livedata:docs"


config = LivedataConfig  # pylint:disable=invalid-name
