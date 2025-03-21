"""Nautobot App Livedata API URLs."""

# Filepath: nautobot_app_livedata/api/urls.py

from django.urls import path

from .views import LivedataPrimaryDeviceApiView, LivedataQueryDeviceApiView, LivedataQueryInterfaceApiView

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
    path(
        "managed-device/<uuid:pk>/<str:object_type>/",
        LivedataPrimaryDeviceApiView.as_view(),
        name="livedata-managed-device-api",
    ),
]
