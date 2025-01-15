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

# Uncomment the following line if you have views to import
# from nautobot_app_livedata import views


router = NautobotUIViewSetRouter()

# Here is an example of how to register a viewset, you will want to replace views.LivedataUIViewSet with your viewset
# router.register("nautobot_app_livedata", views.LivedataUIViewSet)


urlpatterns = [
    path("docs/", RedirectView.as_view(url=static("nautobot_app_livedata/docs/index.html")), name="docs"),
    path(
        "interface/<uuid:pk>/interface_detail_tab/",
        views.LivedataInterfaceExtraTabView.as_view(),
        name="interface_detail_tab",
    ),
    # path("api/", include("nautobot_app_livedata.api.urls")),  # Add this line to include the API URLs
]

urlpatterns += router.urls
