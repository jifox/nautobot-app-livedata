"""Django urlpatterns declaration for livedata app."""

from django.templatetags.static import static
from django.urls import path
from django.views.generic import RedirectView
from nautobot.apps.urls import NautobotUIViewSetRouter


# Uncomment the following line if you have views to import
# from livedata import views


router = NautobotUIViewSetRouter()

# Here is an example of how to register a viewset, you will want to replace views.LiveDataUIViewSet with your viewset
# router.register("livedata", views.LiveDataUIViewSet)


urlpatterns = [
    path("docs/", RedirectView.as_view(url=static("livedata/docs/index.html")), name="docs"),
]

urlpatterns += router.urls
