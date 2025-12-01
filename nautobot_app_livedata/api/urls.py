"""Nautobot App Livedata API URLs."""

# Filepath: nautobot_app_livedata/api/urls.py

import logging

from django.urls import path

from .views import (
    LivedataPrimaryDeviceApiView,
    LivedataQueryDeviceApiView,
    LivedataQueryInterfaceApiView,
)

logger = logging.getLogger(__name__)


def _deprecated_managed_device_view(request, *args, **kwargs):
    """Wrapper for the deprecated managed-device endpoint.

    Logs a deprecation warning and forwards the request to the current
    LivedataPrimaryDeviceApiView. Also sets a deprecation warning header on
    the response to help API consumers notice the change.
    """
    logger.warning(
        "Deprecated endpoint '/api/plugins/livedata/managed-device/' called; "
        "use '/api/plugins/livedata/primary-device/' instead. Caller: %s",
        request.META.get("REMOTE_ADDR"),
    )
    view = LivedataPrimaryDeviceApiView.as_view()
    response = view(request, *args, **kwargs)
    # Try to set a deprecation header if the response supports headers
    try:
        response["Warning"] = '299 - "Deprecated API: use /api/plugins/livedata/primary-device/"'
        response["Deprecation"] = "true"
    except (TypeError, AttributeError, KeyError) as exc:
        # If the view returned something unexpected (e.g. doesn't support header assignment),
        # avoid crashing the request but log the specific error for debugging.
        logger.debug(
            "Unable to set deprecation headers on response of type %s: %s",
            type(response),
            exc,
        )
    return response


urlpatterns = [
    path(
        "intf/<uuid:pk>/",  # interface_id
        LivedataQueryInterfaceApiView.as_view(),
        name="livedata-query-intf-api",
    ),
    path(
        "device/<uuid:pk>/",  # device_id
        LivedataQueryDeviceApiView.as_view(),
        name="livedata-query-device-api",
    ),
    path(  # Deprecated URL path for backward compatibility
        "managed-device/<uuid:pk>/<str:object_type>/",
        _deprecated_managed_device_view,
        name="livedata-managed-device-api-deprecated",
    ),
    path(
        "primary-device/<uuid:pk>/<str:object_type>/",
        LivedataPrimaryDeviceApiView.as_view(),
        name="livedata-primary-device-api",
    ),
]
