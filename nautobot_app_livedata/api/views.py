"""Views for the Livedata API."""

# filepath: livedata/api/views.py

import logging
from http import HTTPStatus
from typing import Any, Optional

from nautobot.apps.views import ObjectPermissionRequiredMixin
from nautobot.dcim.models import Device, Interface
from nautobot.extras.jobs import RunJobTaskFailed
from nautobot.extras.models import Job, JobResult
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from nautobot_app_livedata.urls import PLUGIN_SETTINGS
from nautobot_app_livedata.utilities.primarydevice import get_livedata_commands_for_interface

from .serializers import LivedataSerializer

logger = logging.getLogger(__name__)

# Check that napalm is installed
try:
    import napalm  # pylint: disable=unused-import # noqa: F401
except ImportError:
    raise ImportError(  # pylint: disable=raise-missing-from
        "ERROR NAPALM is not installed. Please see the documentation for instructions."
    )


# Check that celery worker is installed
try:
    from nautobot.core.celery import nautobot_task  # pylint: disable=unused-import,ungrouped-imports # noqa: F401

    CELERY_WORKER = True
except ImportError as err:
    print("ERROR in nautobot_app_livedata: Celery is not Installed.")
    logger.error(  # pylint: disable=raise-missing-from  # type: ignore
        "ERROR in nautobot_app_livedata: Celery is not Installed."
    )
    raise ImportError from err


class LivedataQueryInterfaceApiView(ObjectPermissionRequiredMixin, GenericAPIView):
    """Livedata Query-Device API Result view.

    For more information on implementing jobs, refer to the Nautobot job documentation:
    https://docs.nautobot.com/projects/core/en/stable/development/jobs/
    """

    # LivedataPrimaryDeviceSerializer is used to get the primary device
    # for the Interface provided in pk.
    serializer_class = LivedataSerializer
    queryset = Interface.objects.all()

    def get_required_permission(self) -> str:
        """Get the required permission for the view.

        Format: app_label.action_model

        Returns:
            str: The permission required to access the view.
        """
        return "dcim.can_interact_device"

    def get(self, request: Any, *args: Any, pk: Optional[int] = None, **kwargs: Any) -> Response:
        """Handle GET request for Livedata Query Interface API.

        The get method is used to enqueue the Livedata Query Interface Job.

        To access the JobResult object, use the jobresult_id returned in the response
        and make a GET request to the JobResult endpoint.

        For Example:
            GET /api/extras/job-results/{jobresult_id}/

        Args:
            request (Request): The request object.
            pk (uuid): The primary key of the Interface object.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
            jobresult_id: The job result ID of the job that was enqueued.

        Raises:
            Response: If the user does not have permission to execute 'livedata' on an interface.
            Response: If the serializer is not valid.
            Response: If the job Livedata Api-Job is not found.
            Response: If the job failed to run.
        """
        data = request.data
        data["pk"] = pk
        data["object_type"] = "dcim.interface"
        serializer = self.get_serializer(data=data)
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=HTTPStatus.BAD_REQUEST,  # 400
            )
        try:
            primary_device_info = serializer.validated_data
            interface = Interface.objects.get(pk=pk)
            show_commands_j2_array = get_livedata_commands_for_interface(interface)
        except (ValueError, Interface.DoesNotExist) as error:
            status = HTTPStatus.BAD_REQUEST if isinstance(error, ValueError) else HTTPStatus.NOT_FOUND
            return Response(
                f"Error during Livedata Query Interface API: {error}",
                status=status,
            )

        job = Job.objects.filter(name=PLUGIN_SETTINGS["query_interface_job_name"]).first()
        if job is None:
            return Response(
                f"{PLUGIN_SETTINGS['query_interface_job_name']} not found",
                status=HTTPStatus.NOT_FOUND,  # 404
            )

        job_kwargs = {
            "commands_j2": show_commands_j2_array,
            "device_id": primary_device_info["device"],
            "interface_id": primary_device_info["interface"],
            "primary_device_id": primary_device_info["primary_device"],
            "remote_addr": request.META.get("REMOTE_ADDR"),
            "virtual_chassis_id": primary_device_info["virtual_chassis"],
            "x_forwarded_for": request.META.get("HTTP_X_FORWARDED_FOR"),
            "extra": {"object": f"Query-Intf: {interface.device.name}, {interface.name}"},
        }

        try:
            jobres = JobResult.enqueue_job(
                job,
                user=request.user,
                task_queue=PLUGIN_SETTINGS["query_interface_job_task_queue"],
                **job_kwargs,
            )

            return Response(
                content_type="application/json",
                data={"jobresult_id": jobres.id},
                status=HTTPStatus.OK,  # 200
            )

        except RunJobTaskFailed as error:
            return Response(
                f"Failed to run {PLUGIN_SETTINGS['query_interface_job_name']}: {error}",
                status=HTTPStatus.INTERNAL_SERVER_ERROR,  # 500
            )


# @permission_required(get_permission_for_model(Device, "can_interact"), raise_exception=True)
class LivedataPrimaryDeviceApiView(ObjectPermissionRequiredMixin, GenericAPIView):
    """Nautobot App Livedata API Primary Device view.

    For more information on implementing jobs, refer to the Nautobot job documentation:
    https://docs.nautobot.com/projects/core/en/stable/development/jobs/
    """

    serializer_class = LivedataSerializer
    queryset = Device.objects.all()

    def get_required_permission(self) -> str:
        """Get the required permission for the view.

        Format: app_label.action_model

        Returns:
            str: The permission required to access the view.
        """
        return "dcim.can_interact_device"

    def get(
        self, request: Any, *args: Any, pk: Optional[int] = None, object_type: Optional[str] = None, **kwargs: Any
    ) -> Response:
        """Handle GET request for Livedata Primary Device API.

        Args:
            request (HttpRequest): The request object.
            pk: The primary key of the object.
            object_type (str): The object type.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
            Response: The response object. "application/json"

                data = {
                    "object_type": "The object type to get the primary device for",
                    "pk": "The primary key",
                    "device": "The device ID of the device that is referred in object_type",
                    "interface": "The interface ID if the object type is 'dcim.interface'",
                    "virtual_chassis": "The virtual chassis ID if the object type is 'dcim.virtualchassis'",
                    "primary_device": "The primary device ID"
                }

        Raises:
            Response: If the user does not have permission to execute 'livedata' on an interface.
            Response: If the serializer is not valid.
            Response: If the primary device is not found.
        """
        data = request.data
        data["pk"] = pk
        data["object_type"] = object_type
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            # Return error response if serializer is not valid
            return Response(
                {
                    "error": "Invalid data provided",
                    "details": serializer.errors,
                },
                status=HTTPStatus.BAD_REQUEST,  # 400
            )
        try:
            result = serializer.validated_data
        except ValueError as error:
            return Response(
                f"Failed to get primary device: {error}",
                status=HTTPStatus.BAD_REQUEST,  # 400
            )
        return Response(data=result, status=HTTPStatus.OK)  # 200
