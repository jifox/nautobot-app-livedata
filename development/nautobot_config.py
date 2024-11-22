"""Nautobot development configuration file."""

import os
from re import template
import sys

from nautobot.core.settings import *  # noqa: F403  # pylint: disable=wildcard-import,unused-wildcard-import
from nautobot.core.settings_funcs import is_truthy, parse_redis_connection


#
# Allowed CIDR - Allow CIDR IP address in ALLOWED_HOSTS
# see: https://github.com/mozmeao/django-allow-cidr

DJANGO_ALLOW_CIDR_ENABLED = is_truthy(os.getenv("NAUTOBOT_DJANGO_ALLOW_CIDR_ENABLED", "True"))
if DJANGO_ALLOW_CIDR_ENABLED:
    from allow_cidr import middleware  # noqa F401,F403 # type: ignore



#
# Debug
#

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

DJANGO_ALLOWED_CIDR_NETWORKS_DEFINED = os.getenv("NAUTOBOT_ALLOWED_CIDR_NETS", "")
if DJANGO_ALLOW_CIDR_ENABLED:
    ALLOWED_CIDR_NETS = []

    # Add the middleware to the top of the list
    if "allow_cidr.middleware.AllowCIDRMiddleware" not in MIDDLEWARE:  # noqa: F405
        MIDDLEWARE.insert(0, "allow_cidr.middleware.AllowCIDRMiddleware")  # noqa: F405
    # Get the CIDR networks from the environment variable and add them to the list
    if DJANGO_ALLOWED_CIDR_NETWORKS_DEFINED:
        ALLOWED_CIDR_NETS = os.getenv("NAUTOBOT_ALLOWED_CIDR_NETS", "").split(",")
    else:
        print("WARNING: No CIDR networks defined in NAUTOBOT_ALLOWED_CIDR_NETS environment variable.")



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
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": parse_redis_connection(redis_database=0),
        "TIMEOUT": 300,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
    }
}

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
                "format": "%(asctime)s.%(msecs)03d %(levelname)-7s %(name)s : %(message)s",
                "datefmt": "%H:%M:%S",
            },
            "verbose": {
                "format": "%(asctime)s.%(msecs)03d %(levelname)-7s %(name)-20s %(filename)-15s %(funcName)30s() : %(message)s",
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
PLUGINS = ["livedata"]

# Apps configuration settings. These settings are used by various Apps that the user may have installed.
# Each key in the dictionary is the name of an installed App and its value is a dictionary of settings.
# PLUGINS_CONFIG = {
#     'livedata': {
#         'foo': 'bar',
#         'buzz': 'bazz'
#     }
# }
if "livedata" in PLUGINS:
    if "PLUGINS_CONFIG" not in locals():
        PLUGINS_CONFIG = {}
    if "livedata" not in PLUGINS_CONFIG:
    	PLUGINS_CONFIG["livedata"] = {}

PLUGINS_CONFIG = {
    'livedata': {
    }
}


#
# App: Django Auth LDAP
#
# see: https://nautobot.readthedocs.io/en/latest/configuration/authentication/ldap/
#

DJANGO_AUTH_LDAP_ENABLED = is_truthy(os.getenv("NAUTOBOT_DJANGO_AUTH_LDAP_ENABLED", "True"))

# Server URI
# When using Windows Server 2012 you may need to specify a port on
# AUTH_LDAP_SERVER_URI. Use 3269 for secure, or 3268 for non-secure.
AUTH_LDAP_SERVER_URI = os.getenv("NAUTOBOT_AUTH_LDAP_SERVER_URI", None)

if DJANGO_AUTH_LDAP_ENABLED and AUTH_LDAP_SERVER_URI:
    import ldap  # type:ignore
    from django_auth_ldap.config import (  # type:ignore
        GroupOfNamesType,
        LDAPSearch,
        LDAPSearchUnion,
    )

    ldap_logger = {
        "django_auth_ldap": {
            "handlers": ["normal_console"],
            "level": LOG_LEVEL,
        },
    }
    LOGGING.get("loggers").update(ldap_logger)  # type: ignore

    AUTHENTICATION_BACKENDS = [
        "django_auth_ldap.backend.LDAPBackend",
        "nautobot.core.authentication.ObjectPermissionBackend",
    ]

    # The following may be needed if you are binding to Active Directory.
    AUTH_LDAP_CONNECTION_OPTIONS = {ldap.OPT_REFERRALS: 0}  # type: ignore

    # Set the DN and password for the Nautobot service account.
    AUTH_LDAP_BIND_DN = os.getenv("NAUTOBOT_AUTH_LDAP_BIND_DN")
    AUTH_LDAP_BIND_PASSWORD = os.getenv("NAUTOBOT_AUTH_LDAP_BIND_PASSWORD")

    # Include this `ldap.set_option` call if you want to ignore certificate errors.
    # This might be needed to accept a self-signed cert.
    ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)  # type: ignore

    #
    # LDAP User Authentication
    #

    # Base DN to search for user groups
    AUTH_LDAP_GROUP_SEARCH = os.getenv("NAUTOBOT_AUTH_LDAP_GROUP_SEARCH", None)

    # This search matches users with the sAMAccountName equal to the provided username.
    # This is required if the user's username is not in their DN (Active Directory).
    AUTH_LDAP_USER_SEARCH_DN = os.getenv("NAUTOBOT_AUTH_LDAP_USER_SEARCH_DN", None)

    # This search matches users with the sAMAccountName equal to the provided username.
    if AUTH_LDAP_USER_SEARCH_DN:
        user_search_dn_list = str(AUTH_LDAP_USER_SEARCH_DN).split(";")
        lds = []
        for sdn in user_search_dn_list:
            lds.append(LDAPSearch(sdn.strip(), ldap.SCOPE_SUBTREE, "(sAMAccountName=%(user)s)"))  # type: ignore
        AUTH_LDAP_USER_SEARCH = LDAPSearchUnion(*lds)
    else:
        AUTH_LDAP_USER_SEARCH = None

    # You can map user attributes to Django attributes as so.
    AUTH_LDAP_USER_ATTR_MAP = {
        # "username": "sAMAccountName",
        "first_name": "givenName",
        "last_name": "sn",
        "email": "mail",
    }

    #
    # LDAP User Groups for Permissions
    #

    # If a user's DN is producible from their username, we don't need to search.
    # AUTH_LDAP_USER_DN_TEMPLATE = "uid=%(user)s,ou=users,dc=example,dc=com"

    # This search ought to return all groups to which the user belongs.
    # django_auth_ldap uses this to determine group hierarchy.
    # AUTH_LDAP_GROUP_TYPE = GroupOfNamesType(name_attr="cn")
    # AUTH_LDAP_GROUP_TYPE = ActiveDirectoryGroupType()
    AUTH_LDAP_GROUP_TYPE = GroupOfNamesType()

    # All users must be mapped to at least this group to enable authentication.
    # Without this, users cannot log in.
    AUTH_LDAP_REQUIRE_GROUP = os.getenv("NAUTOBOT_AUTH_LDAP_REQUIRE_GROUP")

    # Users mapped to this group are enabled for access to the administration tools;
    # this is the equivalent of checking the "staff status" box on a manually created user.
    # This doesn't grant any specific permissions.
    AUTH_LDAP_USER_IS_STUFF_GROUP = os.getenv("NAUTOBOT_AUTH_LDAP_USER_IS_STUFF_GROUP")

    # Users mapped to this group will be granted superuser status.
    # Superusers are implicitly granted all permissions.
    AUTH_LDAP_USER_IS_SUPERUSER_GROUP = os.getenv("NAUTOBOT_AUTH_LDAP_USER_IS_SUPERUSER_GROUP")

    # Assign new users to default group
    EXTERNAL_AUTH_DEFAULT_GROUPS = []
    EXTERNAL_AUTH_DEFAULT_GROUP_NAMES = os.getenv("NAUTOBOT_EXTERNAL_AUTH_DEFAULT_GROUPS", "")
    if EXTERNAL_AUTH_DEFAULT_GROUP_NAMES:
        for gnam in EXTERNAL_AUTH_DEFAULT_GROUP_NAMES.split(","):
            EXTERNAL_AUTH_DEFAULT_GROUPS.append(gnam.strip())

    # Use LDAP group membership to calculate group permissions.
    # AUTH_LDAP_FIND_GROUP_PERMS = True

    # Define special user types using groups. Exercise great caution when assigning superuser status.
    #   is_active -  All users must be mapped to at least this group to enable
    #                authentication. Without this, users cannot log in.
    #   is_staff -   Users mapped to this group are enabled for access to the
    #                administration tools; this is the equivalent of checking the "staff status"
    #                box on a manually created user. This doesn't grant any specific permissions.
    #   is_superuser - Users mapped to this group will be granted superuser status. Superusers
    #                are implicitly granted all permissions.
    AUTH_LDAP_USER_FLAGS_BY_GROUP = {
        "is_active": AUTH_LDAP_REQUIRE_GROUP,
        "is_staff": AUTH_LDAP_USER_IS_STUFF_GROUP,
        "is_superuser": AUTH_LDAP_USER_IS_SUPERUSER_GROUP,
    }

    # For more granular permissions, we can map LDAP groups to Django groups.
    AUTH_LDAP_FIND_GROUP_PERMS = False

    # Cache groups for one hour to reduce LDAP traffic
    AUTH_LDAP_CACHE_TIMEOUT = 3600



#
# App: Nautobot Secrets Providers
#
# see: https://github.com/nautobot/nautobot-app-secrets-providers
# see: https://github.com/DelineaXPM/python-tss-sdk
#

SECRETS_PROVIDERS_ENABLED = is_truthy(os.getenv("NAUTOBOT_SECRETS_PROVIDERS_ENABLED", "True"))
SECRET_SERVER_BASE_URL = os.getenv("SECRET_SERVER_BASE_URL", None)

if SECRETS_PROVIDERS_ENABLED and SECRET_SERVER_BASE_URL:
    if "nautobot_secrets_providers" not in PLUGINS:
        PLUGINS.append("nautobot_secrets_providers")
        print("INFO: nautobot_secrets_providers plugin enabled.")  # noqa: T001

    if "nautobot_secrets_providers" not in PLUGINS_CONFIG or "delinea" not in PLUGINS_CONFIG.get(
        "nautobot_secrets_providers"
    ):  # type: ignore
        delinea_seetings = {
            "delinea": {
                "base_url": os.getenv("SECRET_SERVER_BASE_URL"),
                "ca_bundle_path": os.getenv("REQUESTS_CA_BUNDLE", ""),
                "cloud_based": is_truthy(os.getenv("SECRET_SERVER_IS_CLOUD_BASED", "False")),
                "domain": os.getenv("SECRET_SERVER_DOMAIN", ""),
                "password": os.getenv("SECRET_SERVER_PASSWORD", ""),
                # tenant: required when cloud_based == True
                "tenant": os.getenv("SECRET_SERVER_TENANT", ""),
                "token": os.getenv("SECRET_SERVER_TOKEN", ""),
                "username": os.getenv("SECRET_SERVER_USERNAME", ""),

                # ca_bundle_path: (optional) Path to trusted certificates file.
                #     This must be set as environment variable.
                #     see: https://docs.python-requests.org/en/master/user/advanced/

            }
        }

        if "nautobot_secrets_providers" in PLUGINS_CONFIG:  # type: ignore
            PLUGINS_CONFIG.get("nautobot_secrets_providers").update(delinea_seetings)  # type: ignore
            print("INFO: nautobot_secrets_providers plugin updated.")  # noqa: T001
        else:
            PLUGINS_CONFIG.update({"nautobot_secrets_providers": delinea_seetings})  # type: ignore
            print("INFO: nautobot_secrets_providers plugin configured.")



#
# App: Nautobot-SSOT-Plugin Plugin-Settings
#
# see: https://docs.nautobot.com/projects/ssot/en/latest/admin/install/
#

SSOT_ENABLED = is_truthy(os.getenv("NAUTOBOT_SSOT_ENABLED", "True"))
if SSOT_ENABLED:
    if "nautobot_ssot" not in PLUGINS:
        PLUGINS.append("nautobot_ssot")

    if "nautobot_ssot" not in PLUGINS_CONFIG:
        # For more information on the settings, see the documentation:
        #   https://docs.nautobot.com/projects/ssot/en/latest/admin/integrations/
        PLUGINS_CONFIG.update({"nautobot_ssot": {
            "hide_example_jobs": True
        }})



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
                        "credentials": "nautobot_plugin_nornir.plugins.credentials.nautobot_secrets.CredentialsNautobotSecrets",
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
                    # "secret_access_type": "GENERIC",  # (default: GENERIC|CONSOLE|GNMI|HTTP|NETCONF|REST|RESTCONF|SNMP|SSH")
                }
            }
        )
        



#
# App: Device Onboarding
#
# see: https://docs.nautobot.com/projects/device-onboarding/en/latest/admin/install/
#

DEVICE_ONBOARDING_ENABLED = is_truthy(os.getenv("NAUTOBOT_DEVICE_ONBOARDING_ENABLED", "True"))
if DEVICE_ONBOARDING_ENABLED:
    if "nautobot_device_onboarding" not in PLUGINS:
        # Enable installed plugins. Add the name of each plugin to the list.
        PLUGINS.append("nautobot_device_onboarding")

    if "nautobot_device_onboarding" not in PLUGINS_CONFIG:
        # Plugins configuration settings. These settings are used by various plugins that the user may have installed.
        # Each key in the dictionary is the name of an installed plugin and its value is a dictionary of settings.
        PLUGINS_CONFIG.update(
            {
                "nautobot_device_onboarding": {
                    "default_device_role_color": "0000FF",
                    "default_device_role": "edge-switch",
                    "skip_device_type_on_update": True,
                    "default_management_prefix_length": 23,
                    "assign_secrets_group": True,
                    # "platform_map": {
                    #     <Netmiko Platform>: <Nautobot Slug>
                    # },
                },
            }
        )



#
# App: Data Validation Engine
#
# see: https://docs.nautobot.com/projects/data-validation/en/latest/admin/install/#install-guide
#

DATA_VALIDATION_ENGINE_ENABLED = is_truthy(os.getenv("NAUTOBOT_DATA_VALIDATION_ENGINE_ENABLED", "False"))
if DATA_VALIDATION_ENGINE_ENABLED:
    if "nautobot_data_validation_engine" not in PLUGINS:
        # Enable installed plugins. Add the name of each plugin to the list.
        PLUGINS.append("nautobot_data_validation_engine")

    if "nautobot_data_validation_engine" not in PLUGINS_CONFIG:
        # Plugins configuration settings. These settings are used by various plugins that the user may have installed.
        # Each key in the dictionary is the name of an installed plugin and its value is a dictionary of settings.
        PLUGINS_CONFIG.update(
            {
                "nautobot_data_validation_engine": {},
            }
        )



#
# App: Golden Config
#
#
# see: https://docs.nautobot.com/projects/golden-config/en/latest/admin/install/#install-guide

GOLDEN_CONFIG_ENABLED = is_truthy(os.getenv("NAUTOBOT_GOLDEN_CONFIG_ENABLED", "False"))
if GOLDEN_CONFIG_ENABLED:
    if "nautobot_golden_config" not in PLUGINS:
        # Enable installed plugins. Add the name of each plugin to the list.
        PLUGINS.append("nautobot_golden_config")

    if "nautobot_golden_config" not in PLUGINS_CONFIG:
        # Plugins configuration settings. These settings are used by various plugins that the user may have installed.
        # Each key in the dictionary is the name of an installed plugin and its value is a dictionary of settings.
        PLUGINS_CONFIG.update(
            {
                "nautobot_golden_config": {
                    "per_feature_bar_width": 0.15,
                    "per_feature_width": 13,
                    "per_feature_height": 4,
                    "enable_backup": True,
                    "enable_compliance": False,
                    "enable_intended": False,
                    "enable_sotagg": False,
                    "enable_plan": False,
                    "enable_deploy": False,
                    "enable_postprocessing": False,
                    "sot_agg_transposer": None,
                    "postprocessing_callables": [],
                    "postprocessing_subscribed": [],
                    "jinja_env": {
                        "undefined": "jinja2.StrictUndefined",
                        "trim_blocks": True,
                        "lstrip_blocks": False,
                    },
                    # "default_deploy_status": "Not Approved",
                    # "get_custom_compliance": "my.custom_compliance.func"
                },
            }
        )

