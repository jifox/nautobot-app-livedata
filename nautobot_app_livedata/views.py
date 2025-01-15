"""Live Data view for results."""

# filepath: nautobot_app_livedata/views.py

from datetime import datetime

from django.utils.timezone import make_aware
from nautobot.apps import views
from nautobot.dcim.models import Interface


class LivedataInterfaceExtraTabView(views.ObjectView):
    """Live Data view for results."""

    queryset = Interface.objects.all()
    template_name = "nautobot_app_livedata/interface_live_data.html"

    def get_context_data(self, **kwargs):
        """Get context data for the view."""
        now = make_aware(datetime.now())

        context = super().get_context_data(**kwargs)  # type: ignore
        context["interface"] = self
        context["now"] = now.strftime("%Y-%m-%d %H:%M:%S")

        return context
