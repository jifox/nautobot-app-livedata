"""App declaration for livedata."""

# Metadata is inherited from Nautobot. If not including Nautobot in the environment, this should be added
from importlib import metadata

from nautobot.apps import NautobotAppConfig

__version__ = metadata.version(__name__)


class LiveDataConfig(NautobotAppConfig):
    """App configuration for the livedata app."""

    name = "livedata"
    verbose_name = "Live Data"
    version = __version__
    author = "Josef Fuchs"
    description = "LiveData is a Nautobot plugin that provides a live view of the network data.."
    base_url = "livedata"
    required_settings = []
    min_version = "2.0.0"
    max_version = "2.9999"
    default_settings = {}
    caching_config = {}
    docs_view_name = "plugins:livedata:docs"


config = LiveDataConfig  # pylint:disable=invalid-name
