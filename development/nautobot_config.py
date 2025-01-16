"""Nautobot development configuration file."""

import os
import sys

from nautobot.core.settings import *  # noqa: F403  # pylint: disable=wildcard-import,unused-wildcard-import
from nautobot.core.settings_funcs import is_truthy

#
# Debug
#

TEST_USE_FACTORIES = True

DEBUG = is_truthy(os.getenv("NAUTOBOT_DEBUG", "false"))
_TESTING = len(sys.argv) > 1 and sys.argv[1] == "test"

if DEBUG and not _TESTING:
    DEBUG_TOOLBAR_CONFIG = {"SHOW_TOOLBAR_CALLBACK": lambda _request: True}

    if "debug_toolbar" not in INSTALLED_APPS:  # noqa: F405
        INSTALLED_APPS.append("debug_toolbar")  # noqa: F405
    if "debug_toolbar.middleware.DebugToolbarMiddleware" not in MIDDLEWARE:  # noqa: F405
        MIDDLEWARE.insert(0, "debug_toolbar.middleware.DebugToolbarMiddleware")  # noqa: F405

#
# Misc. settings
#

ALLOWED_HOSTS = os.getenv("NAUTOBOT_ALLOWED_HOSTS", "").split(" ")
SECRET_KEY = os.getenv("NAUTOBOT_SECRET_KEY", "")


#
# Django Middleware Settings
#


#
# Database
#

nautobot_db_engine = os.getenv("NAUTOBOT_DB_ENGINE", "django.db.backends.postgresql")
default_db_settings = {
    "django.db.backends.postgresql": {
        "NAUTOBOT_DB_PORT": "5432",
    },
    "django.db.backends.mysql": {
        "NAUTOBOT_DB_PORT": "3306",
    },
}
DATABASES = {
    "default": {
        "NAME": os.getenv("NAUTOBOT_DB_NAME", "nautobot"),  # Database name
        "USER": os.getenv("NAUTOBOT_DB_USER", ""),  # Database username
        "PASSWORD": os.getenv("NAUTOBOT_DB_PASSWORD", ""),  # Database password
        "HOST": os.getenv("NAUTOBOT_DB_HOST", "localhost"),  # Database server
        "PORT": os.getenv(
            "NAUTOBOT_DB_PORT", default_db_settings[nautobot_db_engine]["NAUTOBOT_DB_PORT"]
        ),  # Database port, default to postgres
        "CONN_MAX_AGE": int(os.getenv("NAUTOBOT_DB_TIMEOUT", "300")),  # Database timeout
        "ENGINE": nautobot_db_engine,
    }
}

# Ensure proper Unicode handling for MySQL
if DATABASES["default"]["ENGINE"] == "django.db.backends.mysql":
    DATABASES["default"]["OPTIONS"] = {"charset": "utf8mb4"}

#
# Redis
#

# The django-redis cache is used to establish concurrent locks using Redis.
# Inherited from nautobot.core.settings
# CACHES = {....}

#
# Celery settings are not defined here because they can be overloaded with
# environment variables. By default they use `CACHES["default"]["LOCATION"]`.
#

#
# Logging
#

LOG_LEVEL = "DEBUG" if DEBUG else "INFO"

# Verbose logging during normal development operation, but quiet logging during unit test execution
if not _TESTING:
    LOGGING = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "normal": {
                "format": ("%(asctime)s.%(msecs)03d %(levelname)-7s %(name)s : " "%(message)s"),
                "datefmt": "%H:%M:%S",
            },
            "verbose": {
                "format": (
                    "%(asctime)s.%(msecs)03d %(levelname)-7s %(name)-20s %(filename)-15s "
                    "%(funcName)30s() : %(message)s"
                ),
                "datefmt": "%H:%M:%S",
            },
        },
        "handlers": {
            "normal_console": {
                "level": "INFO",
                "class": "logging.StreamHandler",
                "formatter": "normal",
            },
            "verbose_console": {
                "level": "DEBUG",
                "class": "logging.StreamHandler",
                "formatter": "verbose",
            },
        },
        "loggers": {
            "django": {"handlers": ["normal_console"], "level": "INFO"},
            "nautobot": {
                "handlers": ["verbose_console" if DEBUG else "normal_console"],
                "level": LOG_LEVEL,
            },
        },
    }

#
# Apps
#

# Enable installed Apps. Add the name of each App to the list.
if not PLUGINS:  # noqa: F405
    PLUGINS = []
PLUGINS.append("nautobot_app_livedata")

if "PLUGINS_CONFIG" not in locals():
    PLUGINS_CONFIG = {}

if "nautobot_app_livedata" not in PLUGINS_CONFIG:
    PLUGINS_CONFIG.update(
        {
            "nautobot_app_livedata": {
                "query_interface_job_name": os.getenv(
                    "LIVEDATA_QUERY_INTERFACE_JOB_NAME", "Livedata Query Interface Job"
                ),
                "query_interface_job_description": os.getenv(
                    "LIVEDATA_QUERY_INTERFACE_JOB_DESCRIPTION", "Job to query live data on an interface."
                ),
                "query_interface_job_soft_time_limit": int(
                    os.getenv("LIVEDATA_QUERY_INTERFACE_JOB_SOFT_TIME_LIMIT", "30")
                ),
                "query_interface_job_task_queue": os.getenv("LIVEDATA_QUERY_INTERFACE_JOB_TASK_QUEUE", None),
                "query_interface_job_hidden": is_truthy(os.getenv("LIVEDATA_QUERY_INTERFACE_JOB_HIDDEN", "True")),
                "query_interface_job_has_sensitive_variables": is_truthy(
                    os.getenv("LIVEDATA_QUERY_INTERFACE_JOB_HAS_SENSITIVE_VARIABLES", "False")
                ),
            }
        }
    )


#
# App: Nautobot Plugin Nornir
#
# see: https://docs.nautobot.com/projects/plugin-nornir/en/latest/admin/install/#install-guide
#

NORNIR_ENABLED = is_truthy(os.getenv("NAUTOBOT_NORNIR_ENABLED", "True"))
if NORNIR_ENABLED:
    if "nautobot_plugin_nornir" not in PLUGINS:
        # Append 'nautobot_plugin_nornir' to PLUGINS
        # (if not already present)
        PLUGINS.append("nautobot_plugin_nornir")

    if "nautobot_plugin_nornir" not in PLUGINS_CONFIG:  # type: ignore
        PLUGINS_CONFIG.update(  # type: ignore
            {
                "nautobot_plugin_nornir": {
                    "allowed_location_types": ["region", "site"],
                    "denied_location_types": ["rack"],
                    "nornir_settings": {
                        "credentials": (
                            "nautobot_plugin_nornir.plugins.credentials." "nautobot_secrets.CredentialsNautobotSecrets"
                        ),
                        "runner": {
                            "plugin": "threaded",
                            "options": {
                                "num_workers": 20,
                            },
                        },
                        "napalm": {
                            "extras": {"optional_args": {"global_delay_factor": 5}},
                        },
                        "jobs": {
                            "jinja_env": {
                                "undefined": "jinja2.StrictUndefined",
                                "trim_blocks": True,
                                "lstrip_blocks": False,
                            },
                        },
                    },
                    # "secret_access_type": "GENERIC",
                    #    (default: GENERIC|CONSOLE|GNMI|HTTP|NETCONF|REST|RESTCONF|SNMP|SSH")
                }
            }
        )
