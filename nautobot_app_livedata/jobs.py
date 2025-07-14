"""Jobs for the Nautobot App Livedata API."""

from datetime import datetime

from django.utils import timezone
from django.utils.timezone import make_aware
import jinja2
from nautobot.apps.jobs import DryRunVar, IntegerVar, Job, register_jobs
from nautobot.dcim.models import Device, Interface, VirtualChassis
from nautobot.extras.models import JobResult
from nautobot_plugin_nornir.constants import NORNIR_SETTINGS
from nautobot_plugin_nornir.plugins.inventory.nautobot_orm import NautobotORMInventory
from netutils.interface import abbreviated_interface_name, split_interface
from nornir import InitNornir
from nornir.core.exceptions import NornirExecutionError
from nornir.core.plugins.inventory import InventoryPluginRegister

from nautobot_app_livedata.utilities.primarydevice import PrimaryDeviceUtils

from .nornir_plays.processor import ProcessLivedata
from .urls import APP_NAME, PLUGIN_SETTINGS
from .utilities.output_filter import apply_output_filter

# Groupname: Livedata
name = GROUP_NAME = APP_NAME  # pylint: disable=invalid-name

InventoryPluginRegister.register("nautobot-inventory", NautobotORMInventory)

# Constants for repeated strings
PRIMARY_DEVICE_ID = "primary_device_id"
INTERFACE_ID = "interface_id"
CALL_OBJECT_TYPE = "call_object_type"
COMMANDS_J2 = "commands_j2"
REMOTE_ADDR = "remote_addr"
X_FORWARDED_FOR = "x_forwarded_for"
VIRTUAL_CHASSIS_ID = "virtual_chassis_id"
DEVICE_ID = "device_id"
JOB_NAME_CLEANUP = "livedata_cleanup_job_results"
JOB_STATUS_SUCCESS = "SUCCESS"


class LivedataQueryJob(Job):  # pylint: disable=too-many-instance-attributes
    """Job to query live data on an interface.

    For more information on implementing jobs, refer to the Nautobot job documentation:
    https://docs.nautobot.com/projects/core/en/stable/development/jobs/

    Args:
        commands_j2 (List[str]): The commands to execute in jinja2 syntax.
        device_id (int): The device ID.
        interface_id (int): The interface ID.
        primary_device_id (int): The primary device ID with management ip.
        remote_addr (str): The request.META.get("REMOTE_ADDR").
        virtual_chassis_id (int): The virtual chassis ID.
        x_forwarded_for (str): The request.META.get("HTTP_X_FORWARDED_FOR").
        *args: Additional arguments.
        **kwargs: Additional keyword arguments.
    """

    class Meta:  # pylint: disable=too-few-public-methods
        """Metadata for the Livedata Query Interface Job."""

        name = PLUGIN_SETTINGS.get("query_job_name")
        description = PLUGIN_SETTINGS.get("query_job_description")
        has_sensitive_variables = False
        hidden = PLUGIN_SETTINGS.get("query_job_hidden")
        soft_time_limit = PLUGIN_SETTINGS.get("query_job_soft_time_limit")
        enabled = True

    def __init__(self, *args, **kwargs):
        """Initialize the Livedata Query Interface Job variables."""
        super().__init__(*args, **kwargs)  # defines self.logger
        self.callername = None  # The user who initiated the job
        self.commands = []  # The commands to execute
        self.device = None
        self.interface = None  # The interface object
        self.remote_addr = None  # The remote address request.META.get("REMOTE_ADDR")
        self.primary_device = None  # The primary device object that will be used to execute the commands
        self.virtual_chassis = None  # The virtual chassis object if applicable
        self.x_forwarded_for = None  # The forwarded address request.META.get("HTTP_X_FORWARDED_FOR")
        self.results = []  # The results of the command execution
        self.intf_name = None  # The interface name (e.g. "GigabitEthernet1/0/10")
        self.intf_name_only = None  # The interface name without the number (e.g. "GigabitEthernet")
        self.intf_number = None  # The interface number (e.g. "1/0/10")
        self.intf_abbrev = None  # The abbreviated interface name (e.g. "Gi1/0/10")
        self.device_name = None  # The device name of the device where the interface is located
        self.device_ip = None  # The primary IP address of the primary device
        self.execution_timestamp = None  # The current timestamp in the format "YYYY-MM-DD HH:MM:SS"
        self.now = None  # The current timestamp
        self.call_object_type = None  # The object type of the call

    def parse_commands(self, commands_j2):
        """Replace jinja2 variables in the commands with the interface-specific context.

        Args:
            commands_j2 (List[str]): The commands to execute in jinja2 syntax.

        Returns:
            List[str]: The parsed commands.
        """
        # Initialize jinja2 environment with interface context
        j2env = jinja2.Environment(
            loader=jinja2.BaseLoader(),
            autoescape=False,  # noqa: S701 # no HTML is involved
            undefined=jinja2.StrictUndefined,
        )
        # Create a context with interface-specific variables
        context = {
            "intf_name": self.intf_name,
            "intf_name_only": self.intf_name_only,
            "intf_number": self.intf_number,
            "intf_abbrev": self.intf_abbrev,
            "device_name": self.device_name,
            "primary_device": self.primary_device.name,  # type: ignore
            "device_ip": self.device_ip,
            "obj": self.interface,
            "timestamp": self.execution_timestamp,
            "call_object_type": self.call_object_type,
        }

        # Render each command with the context
        parsed_commands = [j2env.from_string(command).render(context) for command in commands_j2]
        return parsed_commands

    # if you need to use the logger, you must define it here
    def before_start(self, task_id, args, kwargs):
        """Job-specific setup before the run() method is called.

        Args:
            task_id: The task ID. Will always be identical to self.request.id
            args: Will generally be empty
            kwargs: Any user-specified variables passed into the Job execution

        Returns:
                The return value is ignored, but if it raises any exception,
                    the Job execution will be marked as a failure and run() will
                    not be called.

        Raises:
            ValueError: If the interface_id is not provided.
            ValueError: If the commands_j2 is not provided.
            ValueError: If the interface with the provided interface_id is not found.
            ValueError: If the primary device with the provided primary_device_id is not found.
            ValueError: If the call_object_type is not provided.
        """
        super().before_start(task_id, args, kwargs)
        self._initialize_variables(kwargs)
        self._initialize_interface(kwargs)
        self._initialize_primary_device(kwargs)
        self._initialize_device(kwargs)
        self._initialize_virtual_chassis(kwargs)
        self._initialize_commands(kwargs)

    def _initialize_variables(self, kwargs):
        """Initialize common variables."""
        self.callername = self.user.username  # type: ignore
        self.now = make_aware(datetime.now())
        self.remote_addr = kwargs.get(REMOTE_ADDR)
        self.x_forwarded_for = kwargs.get(X_FORWARDED_FOR)
        self.call_object_type = kwargs.get(CALL_OBJECT_TYPE)
        if not self.call_object_type:
            raise ValueError(f"{CALL_OBJECT_TYPE} is required.")
        # Defensive: ensure self.now is not None
        if self.now:
            self.execution_timestamp = self.now.strftime("%Y-%m-%d %H:%M:%S")
        else:
            self.execution_timestamp = None

    def _initialize_virtual_chassis(self, kwargs):
        """Initialize the virtual chassis object if applicable."""
        if VIRTUAL_CHASSIS_ID in kwargs:
            virtual_chassis_id = kwargs.get(VIRTUAL_CHASSIS_ID)
            if virtual_chassis_id:
                self.virtual_chassis = VirtualChassis.objects.get(pk=virtual_chassis_id)
            else:
                if self.device and hasattr(self.device, "virtual_chassis") and self.device.virtual_chassis:
                    self.virtual_chassis = self.device.virtual_chassis

    def _initialize_device(self, kwargs):  # pylint: disable=possibly-used-before-assignment
        """Initialize the device object."""
        if DEVICE_ID in kwargs:
            device_id = kwargs.get(DEVICE_ID)
        else:
            device_id = (
                self.interface.device.id  # type: ignore[attr-defined]
                if self.interface and hasattr(self.interface, "device")
                else None
            )
        if device_id:
            self.device = Device.objects.get(pk=device_id)
            self.device_name = self.device.name

    def _initialize_primary_device(self, kwargs):
        """Initialize the primary device object."""
        if PRIMARY_DEVICE_ID not in kwargs:
            if self.interface and hasattr(self.interface, "id"):
                primary_device_id = (
                    PrimaryDeviceUtils("dcim.interface", str(self.interface.id)).primary_device.id  # type: ignore
                )
            else:
                primary_device_id = None
        else:
            primary_device_id = kwargs.get(PRIMARY_DEVICE_ID)
        try:
            if primary_device_id:
                self.primary_device = Device.objects.get(pk=primary_device_id)
                self.device_ip = self.primary_device.primary_ip.address  # type: ignore
        except Device.DoesNotExist as exc:
            raise ValueError(f"Primary Device with ID {primary_device_id} not found.") from exc  # pylint: disable=raise-missing-from

    def _initialize_interface(self, kwargs):
        """Initialize the interface object."""
        if kwargs.get(CALL_OBJECT_TYPE) == "dcim.interface":
            if INTERFACE_ID not in kwargs:
                raise ValueError("Interface_id is required.")
            try:
                self.interface = Interface.objects.get(pk=kwargs.get(INTERFACE_ID))
            except Interface.DoesNotExist as error:
                raise ValueError(f"Interface with ID {kwargs.get(INTERFACE_ID)} not found.") from error

    def _initialize_commands(self, kwargs):
        """Initialize the commands to be executed."""
        if COMMANDS_J2 not in kwargs:
            raise ValueError(f"{COMMANDS_J2} is required.")
        if self.call_object_type == "dcim.interface":
            if self.interface and hasattr(self.interface, "name"):
                self.intf_name = self.interface.name
                self.intf_name_only, self.intf_number = split_interface(self.intf_name)
                self.intf_abbrev = abbreviated_interface_name(self.interface.name)
            else:
                self.intf_name = self.intf_name_only = self.intf_number = self.intf_abbrev = None
        self.commands = self.parse_commands(kwargs.get(COMMANDS_J2))

    # If both before_start() and run() are successful, the on_success() method
    # will be called next, if implemented.

    # def on_success(self, retval, task_id, args, kwargs):
    #     return super().on_success(retval, task_id, args, kwargs)

    # def on_retry(self, exc, task_id, args, kwargs, einfo):
    #     """Reserved as a future special method for handling retries."""
    #     return super().on_retry(exc, task_id, args, kwargs, einfo)

    # def on_failure(self, exc, task_id, args, kwargs, einfo):
    #     # If either before_start() or run() raises any unhandled exception,
    #     # the on_failure() method will be called next, if implemented.
    #     return super().on_failure(exc, task_id, args, kwargs, einfo)

    # The run() method is the primary worker of any Job, and must be implemented.
    # After the self argument, it should accept keyword arguments for any variables
    # defined on the job.
    # If run() returns any value (even the implicit None), the Job execution
    # will be marked as a success and the returned value will be stored in
    # the associated JobResult database record.

    def run(  # pylint: disable=too-many-locals
        self,
        *args,
        **kwargs,
    ):
        """Run the job to query live data on an interface.

        Args:
            commands (List[str]): The commands to execute
            device_id (int): The device ID.
            interface_id (int): The interface ID.
            primary_device (int): The primary device ID.
            remote_addr (str): The remote address.
            virtual_chassis_id (int): The virtual chassis ID.
            x_forwarded_for (str): The forwarded address.
            *args: Additional arguments.
            extras (Dict): Additional information
                - object_type (str): The object type.
                - call_object_type (str): The call object type.
            **kwargs: Additional keyword arguments.

        Returns:
            jobresult_id: The job result ID of the job that was enqueued.
        """
        # The job-specific variables are initialized in the before_start() method
        # Example commands:
        #   self.logger.info(
        #       f"Livedata Query Interface Job for interface {self.intf_name} on {self.device_name} started.",
        #       extra={"grouping": f"Query: {self.device_name}, {self.intf_name}", "object": self.job_result},
        #   )
        #   logger.info("This job is running!", extra={"grouping": "myjobisrunning", "object": self.job_result})
        #   self.create_file("greeting.txt", "Hello world!")
        #   self.create_file("farewell.txt", b"Goodbye for now!")  # content can be a str or bytes

        callername = self.user.username  # type: ignore
        # PrimaryDevice is the device that is manageabe

        now = make_aware(datetime.now())
        qs = Device.objects.filter(id=self.primary_device.id).distinct()  # type: ignore

        data = {
            "now": now,
            "caller": callername,
            "interface": self.interface,
            "intf": self.interface,
            "device_name": self.device_name,
            "device_ip": self.primary_device.primary_ip.address,  # type: ignore
            "call_object_type": self.call_object_type,
        }

        inventory = {
            "plugin": "nautobot-inventory",
            "options": {
                "credentials_class": NORNIR_SETTINGS.get("credentials"),
                "params": NORNIR_SETTINGS.get("inventory_params"),
                "queryset": qs,
                "defaults": {"data": data},
            },
        }

        # list of nornir results
        results = []
        with InitNornir(
            # runner={"plugin": "threadedrunner", "options": {"num_workers": 1}}
            runner={"plugin": "serial"},  # Serial runner has no options num_workers
            logging={"enabled": False},  # Disable logging because we are using our own logger
            inventory=inventory,
        ) as nornir_obj:
            nr_with_processors = nornir_obj.with_processors([ProcessLivedata(self.logger)])
            # Establish the connection once
            try:
                connection = (
                    nr_with_processors.filter(name=self.primary_device.name)  # type: ignore
                    .inventory.hosts[self.primary_device.name]  # type: ignore
                    .get_connection("netmiko", nr_with_processors.config)
                )
            except KeyError as error:
                raise ValueError(f"Device {self.primary_device.name} not found in Nornir inventory.") from error
            try:
                for command in self.commands:
                    # Support for !! filter syntax
                    if "!!" in command:
                        base_command, filter_part = command.split("!!", 1)
                        filter_instruction = filter_part.strip("!")
                        command_to_send = base_command.strip()
                    else:
                        command_to_send = command
                        filter_instruction = None
                    try:
                        self.logger.debug(f"Executing '{command_to_send}' on device {self.device_name}")
                        task_result = connection.send_command(command_to_send)
                        # Apply filter if present
                        if filter_instruction:
                            task_result = apply_output_filter(task_result, filter_instruction)
                        results.append({"command": command, "task_result": task_result})
                    except NornirExecutionError as error:
                        raise ValueError(f"`E3001:` {error}") from error
            finally:
                connection.disconnect()
        return_values = []
        for res in results:
            result = res["task_result"]
            value = {
                "command": res["command"],
                "stdout": result,
                "stderr": "",  # Adjust if needed based on actual result structure
            }
            return_values.append(value)
            self.logger.debug("Livedata results for interface: \n```%s\n```", value)
        # Return the results
        return return_values


class LivedataCleanupJobResultsJob(Job):
    """Job to cleanup the Livedata Query Interface Job results.

    For more information on implementing jobs, refer to the Nautobot job documentation:
    https://docs.nautobot.com/projects/core/en/stable/development/jobs/

    Args:
        *args: Additional arguments.
        **kwargs: Additional keyword arguments.
    """

    class Meta:  # pylint: disable=too-few-public-methods
        """Metadata for the Livedata Cleanup Job Results Job."""

        name = "Livedata Cleanup job results"
        description = "Cleanup the Livedata Query Interface Job results."
        dry_run_default = False
        has_sensitive_variables = False
        hidden = False
        soft_time_limit = 60
        enabled = True

    days_to_keep = IntegerVar(
        description="Number of days to keep job results",
        default=30,
        min_value=1,
    )

    dry_run = DryRunVar(
        description="If true, display the count of records that will be deleted without actually deleting them",
        default=False,
    )

    def run(  # pylint: disable=arguments-differ
        self,
        days_to_keep,
        dry_run,
        *args,
        **kwargs,
    ):
        """Run the job to cleanup the Livedata Query Interface Job results.

        Args:
            days_to_keep (int): Number of days to keep job results.
            dry_run (bool): If true, display the count of records that will be deleted without actually deleting them.
            *args: Additional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
            str: Cleanup status message.
        """
        if not days_to_keep:
            days_to_keep = 30
        cutoff_date = timezone.now() - timezone.timedelta(days=days_to_keep)
        job_results = JobResult.objects.filter(
            date_done__lt=cutoff_date,
            job_model__name=PLUGIN_SETTINGS["query_job_name"],
            status=JOB_STATUS_SUCCESS,
        )
        cleanup_job_results = JobResult.objects.filter(
            date_done__lt=cutoff_date,
            job_model__name=JOB_NAME_CLEANUP,
            status=JOB_STATUS_SUCCESS,
        )

        if dry_run:
            job_results_feedback = (
                f"{job_results.count()} job results older than {days_to_keep} days would be deleted. "
                f"{cleanup_job_results.count()} cleanup job results would also be deleted."
            )
        else:
            deleted_count, _ = job_results.delete()
            cleaned_count, _ = cleanup_job_results.delete()
            job_results_feedback = (
                f"Deleted {deleted_count} job results older than {days_to_keep} days. "
                f"Deleted {cleaned_count} cleanup job results."
            )

        return job_results_feedback


register_jobs(LivedataQueryJob, LivedataCleanupJobResultsJob)
