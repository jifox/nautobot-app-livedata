"""Live Data view for results."""

# filepath: nautobot_app_livedata/views.py

from datetime import datetime

from django.utils.timezone import make_aware
from nautobot.apps.views import ObjectView
from nautobot.dcim.models import Interface


class LivedataInterfaceExtraTabView(ObjectView):
    """Live Data view for results."""

    queryset = Interface.objects.all()
    template_name = "nautobot_app_livedata/interface_live_data.html"

    def get_extra_context(self, request, instance):
        """Get extra context for the view.

        Args:
            request (HttpRequest): The request object.
            instance (Interface): The interface instance.

        Returns:
            dict: The extra context for the view.
        """
        now = make_aware(datetime.now())
        extra_context = {}
        extra_context["interface"] = instance
        extra_context["now"] = now.strftime("%Y-%m-%d %H:%M:%S")
        permissions = request.user.get_all_permissions()
        extra_context["permissions"] = permissions
        if request.user.is_staff or request.user.is_superuser:
            extra_context["has_permission"] = True
        else:
            extra_context["has_permission"] = (
                "dcim.can_interact_device" in permissions and "extras.run_job" in permissions
            )
        return extra_context
