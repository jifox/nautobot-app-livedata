"""Django urlpatterns declaration for nautobot_app_livedata app."""

from django.templatetags.static import static
from django.urls import path
from django.views.generic import RedirectView
from nautobot.apps.urls import NautobotUIViewSetRouter


# Uncomment the following line if you have views to import
# from nautobot_app_livedata import views


router = NautobotUIViewSetRouter()

# Here is an example of how to register a viewset, you will want to replace views.LivedataUIViewSet with your viewset
# router.register("nautobot_app_livedata", views.LivedataUIViewSet)


urlpatterns = [
    path("docs/", RedirectView.as_view(url=static("nautobot_app_livedata/docs/index.html")), name="docs"),
]

urlpatterns += router.urls
