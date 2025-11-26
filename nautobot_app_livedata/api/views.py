"""Views for the Livedata API."""

from abc import ABC, abstractmethod
from http import HTTPStatus
import logging
from typing import Any, Optional

from django.core.exceptions import ObjectDoesNotExist
from nautobot.dcim.models import Device, Interface
from nautobot.extras.jobs import RunJobTaskFailed
from nautobot.extras.models import Job, JobResult
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from nautobot_app_livedata.api.serializers import LivedataSerializer
from nautobot_app_livedata.urls import PLUGIN_SETTINGS
from nautobot_app_livedata.utilities.primarydevice import (
    get_livedata_commands_for_device,
    get_livedata_commands_for_interface,
)

logger = logging.getLogger("nautobot_app_livedata")

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


class LivedataQueryApiView(GenericAPIView, ABC):
    """Abstract Livedata Query API view.

    Base class for all Livedata Query API views. Provides common functionality
    for queuing livedata jobs to execute commands on network devices.
    Subclasses must implement get_object_type() and get_commands() methods.
    """

    serializer_class = LivedataSerializer
    permission_classes = []  # Custom permission checking in get() method

    @abstractmethod
    def get_object_type(self) -> str:
        """Get the object type for the view.

        Must be implemented by subclasses to identify the type of object
        being queried (e.g., 'dcim.interface' or 'dcim.device').

        Returns:
            str: The object type in format 'app_label.model_name'.
        """

    @abstractmethod
    def get_commands(self, instance: Any) -> list[str]:
        """Get the commands to be executed for the given instance.

        Must be implemented by subclasses to retrieve the appropriate commands
        based on the instance type and its platform configuration.

        Args:
            instance (Model): The model instance (Device or Interface) to query.

        Returns:
            list[str]: List of command strings to be executed on the device.
        """

    def get(self, request: Any, *args: Any, pk: Optional[Any] = None, **kwargs: Any) -> Response:  # pylint: disable=R0911
        """Handle GET request for Livedata Query API.

        The get method is used to enqueue the Livedata Query Job.

        To access the JobResult object, use the jobresult_id returned in the response
        and make a GET request to the JobResult endpoint.

        For Example:
            GET /api/extras/job-results/{jobresult_id}/

        Args:
            request (Request): The request object.
            pk (uuid): The primary key of the model instance.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
            jobresult_id: The job result ID of the job that was enqueued.

        Raises:
            Response: If the user does not have permission to execute 'livedata' on the instance.
            Response: If the serializer is not valid.
            Response: If the job Livedata Api-Job is not found.
            Response: If the job failed to run.
        """
        logger.info(
            "Resolved view=%s queryset_model=%s",
            self.__class__.__name__,
            getattr(getattr(self, "queryset", None), "model", None),
        )
        payload = self._build_serializer_payload(request, pk)
        serializer = self.get_serializer(data=payload)
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=HTTPStatus.BAD_REQUEST,
            )
        # Check if user has permission to interact with the interface
        if not self._user_can_interact(request.user):
            return Response(
                {
                    "error": (
                        "You do not have the permission 'can_interact' for 'dcim.device'. Contact your administrator."
                    )
                },
                status=HTTPStatus.FORBIDDEN,  # 403
            )

        try:
            primary_device_info = serializer.validated_data
            instance = self._resolve_instance(payload["object_type"], pk, primary_device_info)
            job_kwargs = self._build_job_kwargs(request, primary_device_info, payload["object_type"], instance)
        except ValueError as error:
            logger.error("Error during Livedata Query API: %s", error)
            return Response(
                "An error occurred during the Livedata Query API request.",
                status=HTTPStatus.BAD_REQUEST,
            )
        except ObjectDoesNotExist:
            return Response(
                "An error occurred during the Livedata Query API request.",
                status=HTTPStatus.NOT_FOUND,
            )
        except Exception as error:  # pylint: disable=broad-exception-caught
            logger.error("Unexpected error during Livedata Query API: %s", error)
            return Response(
                "An unexpected error occurred during the Livedata Query API request.",
                status=HTTPStatus.INTERNAL_SERVER_ERROR,
            )

        job = self._get_livedata_job()
        if job is None:
            return Response(
                f"{PLUGIN_SETTINGS['query_job_name']} not found",
                status=HTTPStatus.NOT_FOUND,  # 404
            )

        try:
            jobres = self._enqueue_job(job, request.user, job_kwargs)
            logger.debug("Enqueued %s: %s", PLUGIN_SETTINGS["query_job_name"], jobres.id)
            return Response(
                content_type="application/json",
                data={"jobresult_id": jobres.id},
                status=HTTPStatus.OK,  # 200
            )
        except RunJobTaskFailed as error:
            logger.error("Failed to run %s: %s", PLUGIN_SETTINGS["query_job_name"], error)

            return Response(
                "An internal error has occurred while running the job.",
                status=HTTPStatus.INTERNAL_SERVER_ERROR,  # 500
            )

    def _build_serializer_payload(self, request: Any, pk: Optional[Any]) -> dict[str, Any]:
        """Return serializer payload populated with object metadata."""

        request_data = request.data if request.data is not None else {}
        payload = request_data.copy() if hasattr(request_data, "copy") else dict(request_data)
        payload["pk"] = pk
        payload["object_type"] = self.get_object_type()
        return payload

    def _user_can_interact(self, user: Any) -> bool:
        """Check whether the requesting user may interact with devices."""

        return user.has_perm("dcim.can_interact_device")

    def _resolve_instance(
        self,
        object_type: str,
        pk: Optional[Any],
        primary_device_info: dict[str, Any],
    ) -> Any:
        """Return the model instance for the given object_type."""

        if not primary_device_info:
            raise ValueError("Primary device information is missing.")

        if object_type == "dcim.interface":
            self.queryset = Interface.objects.all()
            return Interface.objects.get(pk=pk)
        if object_type == "dcim.device":
            self.queryset = Device.objects.all()
            return Device.objects.get(pk=primary_device_info["primary_device"])
        queryset = self.get_queryset()
        return queryset.get(pk=pk)

    def _get_livedata_job(self) -> Job | None:
        """Fetch the configured Livedata job if available."""

        return Job.objects.filter(name=PLUGIN_SETTINGS["query_job_name"]).first()

    def _build_job_kwargs(
        self,
        request: Any,
        primary_device_info: dict[str, Any],
        object_type: str,
        instance: Any,
    ) -> dict[str, Any]:
        """Assemble keyword arguments required to enqueue the job."""

        commands = self.get_commands(instance)
        return {
            "commands_j2": commands,
            "device_id": primary_device_info["device"],
            "interface_id": primary_device_info.get("interface"),
            "primary_device_id": primary_device_info["primary_device"],
            "remote_addr": request.META.get("REMOTE_ADDR"),
            "virtual_chassis_id": primary_device_info.get("virtual_chassis"),
            "x_forwarded_for": request.META.get("HTTP_X_FORWARDED_FOR"),
            "call_object_type": object_type,
        }

    def _enqueue_job(self, job: Job, user: Any, job_kwargs: dict[str, Any]) -> JobResult:
        """Enqueue the configured job and return the resulting JobResult."""

        return JobResult.enqueue_job(
            job,
            user=user,
            task_queue=PLUGIN_SETTINGS["query_job_task_queue"],
            **job_kwargs,
        )


class LivedataQueryInterfaceApiView(LivedataQueryApiView):
    """Livedata Query Interface API view.

    API endpoint for executing live data commands on a specific interface.
    Retrieves commands from the device platform's 'livedata_interface_commands' custom field.
    """

    serializer_class = LivedataSerializer
    queryset = Interface.objects.all()

    def get_object_type(self) -> str:
        """Return the object type for interface queries.

        Returns:
            str: Always returns 'dcim.interface'.
        """
        return "dcim.interface"

    def get_commands(self, instance) -> list:
        """Get livedata commands for the interface.

        Args:
            instance (Interface): The interface instance to query.

        Returns:
            list[str]: List of commands from the platform's livedata_interface_commands field.
        """
        return get_livedata_commands_for_interface(instance)


class LivedataQueryDeviceApiView(LivedataQueryApiView):
    """Livedata Query Device API view.

    API endpoint for executing live data commands on a specific device.
    Retrieves commands from the device platform's 'livedata_device_commands' custom field.
    Restricts access to devices the user has 'can_interact_device' permission for.
    """

    serializer_class = LivedataSerializer
    queryset = Device.objects.all()

    def get_queryset(self) -> Any:
        """Filter queryset to devices the user can interact with.

        Returns:
            QuerySet: Device queryset restricted by user's can_interact_device permission.
        """
        # Restrict devices to those the user can interact with
        qs = super().get_queryset()
        return qs.restrict(self.request.user, action="can_interact_device")

    def get_object_type(self) -> str:
        """Return the object type for device queries.

        Returns:
            str: Always returns 'dcim.device'.
        """
        return "dcim.device"

    def get_commands(self, instance) -> list:
        """Get livedata commands for the device.

        Args:
            instance (Device): The device instance to query.

        Returns:
            list[str]: List of commands from the platform's livedata_device_commands field.
        """
        return get_livedata_commands_for_device(instance)


# @permission_required(get_permission_for_model(Device, "can_interact"), raise_exception=True)
class LivedataPrimaryDeviceApiView(GenericAPIView):
    """Nautobot App Livedata API Primary Device view.

    API endpoint for retrieving the primary device for a given object (device, interface, or virtual chassis).
    The primary device is the device with an active status and primary IP address that can be used
    to establish a connection for executing commands.

    Returns information about the object hierarchy including device, interface, virtual chassis,
    and the determined primary device.
    """

    serializer_class = LivedataSerializer
    queryset = Device.objects.all()
    permission_classes = []  # No DRF permission checks - this view doesn't require authentication

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
            PermissionDenied: If the user does not have permission to access the object.
            NotFound: If the object does not exist.
        """
        # Check if user has permission to interact with devices
        if not request.user.has_perm("dcim.can_interact_device"):
            return Response(
                {
                    "error": (
                        "You do not have the permission 'can_interact' for 'dcim.device'. Contact your administrator."
                    )
                },
                status=HTTPStatus.FORBIDDEN,  # 403
            )

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
