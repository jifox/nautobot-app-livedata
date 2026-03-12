"""Test settings for nautobot_app_livedata."""

# pylint: disable=all

import os

from nautobot.core import settings as nautobot_settings
from nautobot.core.settings_funcs import parse_redis_connection

for setting_name in dir(nautobot_settings):
    if setting_name.isupper():
        globals()[setting_name] = getattr(nautobot_settings, setting_name)


ALLOWED_HOSTS = ["*"]
SECRET_KEY = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"  # nosec

DATABASES = {
    "default": {
        "NAME": os.getenv("NAUTOBOT_DB_NAME", "nautobot"),
        "USER": os.getenv("NAUTOBOT_DB_USER", ""),
        "PASSWORD": os.getenv("NAUTOBOT_DB_PASSWORD", ""),
        "HOST": os.getenv("NAUTOBOT_DB_HOST", "localhost"),
        "PORT": os.getenv("NAUTOBOT_DB_PORT", "5432"),
        "CONN_MAX_AGE": int(os.getenv("NAUTOBOT_DB_TIMEOUT", "300")),
        "ENGINE": os.getenv("NAUTOBOT_DB_ENGINE", "django.db.backends.postgresql"),
    }
}

if DATABASES["default"]["ENGINE"] == "django.db.backends.mysql":
    DATABASES["default"]["OPTIONS"] = {"charset": "utf8mb4"}

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": parse_redis_connection(redis_database=2),
        "TIMEOUT": 300,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
    }
}

CACHEOPS_REDIS = parse_redis_connection(redis_database=3)

PLUGINS = ["nautobot_app_livedata"]
PLUGINS_CONFIG = {
    "nautobot_app_livedata": {
        "query_job_name": "Livedata Query Interface",
        "query_job_description": "Execute the Livedata interface query job in tests.",
        "query_job_hidden": False,
        "query_job_soft_time_limit": 60,
    }
}
