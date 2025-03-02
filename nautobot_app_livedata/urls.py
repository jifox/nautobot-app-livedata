"""Django urlpatterns declaration for Nautobot App Livedata."""

# filepath: nautobot_app_livedata/urls.py

from django.conf import settings
from django.templatetags.static import static
from django.urls import path
from django.views.generic import RedirectView
from nautobot.apps.urls import NautobotUIViewSetRouter

from nautobot_app_livedata import (
    views,  # Add this import
)

APP_NAME = "nautobot_app_livedata"

PLUGIN_SETTINGS = settings.PLUGINS_CONFIG[APP_NAME]

app_name = APP_NAME
router = NautobotUIViewSetRouter()

urlpatterns = [
    path("docs/", RedirectView.as_view(url=static("nautobot_app_livedata/docs/index.html")), name="docs"),
    path(
        "interfaces/<uuid:pk>/interface_detail_tab/",
        views.LivedataInterfaceExtraTabView.as_view(),
        name="interface_detail_tab",
    ),
    path(
        "devices/<uuid:pk>/device_detail_tab/",
        views.LivedataDeviceExtraTabView.as_view(),
        name="device_detail_tab",
    ),
]

urlpatterns += router.urls
