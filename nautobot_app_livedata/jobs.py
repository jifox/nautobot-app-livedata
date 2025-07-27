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
    """Job to query live data on an interface."""

    class Meta:  # pylint: disable=too-few-public-methods
        """Metadata for the Livedata Query Interface Job."""

        name = PLUGIN_SETTINGS.get("query_job_name")
        description = PLUGIN_SETTINGS.get("query_job_description")
        has_sensitive_variables = False
        hidden = PLUGIN_SETTINGS.get("query_job_hidden")
        soft_time_limit = PLUGIN_SETTINGS.get("query_job_soft_time_limit")
        enabled = True

    def __init__(self, *args, **kwargs):
        """Initialize job variables."""
        super().__init__(*args, **kwargs)
        # Instance attributes for job context and results
        self.callername = None
        self.commands = []
        self.device = None
        self.interface = None
        self.remote_addr = None
        self.primary_device = None
        self.virtual_chassis = None
        self.x_forwarded_for = None
        self.results = []
        self.intf_name = None
        self.intf_name_only = None
        self.intf_number = None
        self.intf_abbrev = None
        self.device_name = None
        self.device_ip = None
        self.execution_timestamp = None
        self.now = None
        self.call_object_type = None

    def parse_commands(self, commands_j2):
        """Render Jinja2 commands with interface/device context.

        Raises:
            ValueError: If Jinja2 rendering fails.
        """
        j2env = jinja2.Environment(
            loader=jinja2.BaseLoader(),
            autoescape=False,  # No HTML involved # type: ignore  # noqa: S701
            undefined=jinja2.StrictUndefined,
        )
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

        parsed_commands = []
        for command in commands_j2:
            try:
                parsed_command = j2env.from_string(command).render(context)
                parsed_commands.append(parsed_command)
            except jinja2.TemplateError as exc:
                raise ValueError(f"Failed to render Jinja2 command template: '{command}'. Error: {exc}") from exc
        return parsed_commands

    def before_start(self, task_id, args, kwargs):
        """Setup job context before execution.

        Raises:
            ValueError: If required variables are missing or invalid.
        """
        super().before_start(task_id, args, kwargs)
        self._initialize_variables(kwargs)
        self._initialize_interface(kwargs)
        self._initialize_primary_device(kwargs)
        self._initialize_device(kwargs)
        self._initialize_virtual_chassis(kwargs)
        self._initialize_commands(kwargs)

    def _initialize_variables(self, kwargs):
        """Initialize common context variables."""
        self.callername = self.user.username  # type: ignore
        self.now = make_aware(datetime.now())
        self.remote_addr = kwargs.get(REMOTE_ADDR)
        self.x_forwarded_for = kwargs.get(X_FORWARDED_FOR)
        self.call_object_type = kwargs.get(CALL_OBJECT_TYPE)
        if not self.call_object_type:
            raise ValueError(f"{CALL_OBJECT_TYPE} is required.")
        self.execution_timestamp = self.now.strftime("%Y-%m-%d %H:%M:%S") if self.now else None

    def _initialize_virtual_chassis(self, kwargs):
        """Set virtual chassis if provided or available on device."""
        if VIRTUAL_CHASSIS_ID in kwargs:
            virtual_chassis_id = kwargs.get(VIRTUAL_CHASSIS_ID)
            if virtual_chassis_id:
                self.virtual_chassis = VirtualChassis.objects.get(pk=virtual_chassis_id)
            elif self.device and hasattr(self.device, "virtual_chassis") and self.device.virtual_chassis:
                self.virtual_chassis = self.device.virtual_chassis

    def _initialize_device(self, kwargs):
        """Set device object from kwargs or interface."""
        device_id = kwargs.get(DEVICE_ID) or (
            self.interface.device.id if self.interface and hasattr(self.interface, "device") else None
        )
        if device_id:
            self.device = Device.objects.get(pk=device_id)
            self.device_name = self.device.name

    def _initialize_primary_device(self, kwargs):
        """Set primary device object from kwargs or via utility."""
        if PRIMARY_DEVICE_ID not in kwargs and self.interface and hasattr(self.interface, "id"):
            primary_device_id = PrimaryDeviceUtils("dcim.interface", str(self.interface.id)).primary_device.id  # type: ignore
        else:
            primary_device_id = kwargs.get(PRIMARY_DEVICE_ID)
        try:
            if primary_device_id:
                self.primary_device = Device.objects.get(pk=primary_device_id)
                self.device_ip = self.primary_device.primary_ip.address  # type: ignore
        except Device.DoesNotExist as exc:
            raise ValueError(f"Primary Device with ID {primary_device_id} not found.") from exc

    def _initialize_interface(self, kwargs):
        """Set interface object if call_object_type is 'dcim.interface'."""
        if kwargs.get(CALL_OBJECT_TYPE) == "dcim.interface":
            if INTERFACE_ID not in kwargs:
                raise ValueError("Interface_id is required.")
            try:
                self.interface = Interface.objects.get(pk=kwargs.get(INTERFACE_ID))
            except Interface.DoesNotExist as error:
                raise ValueError(f"Interface with ID {kwargs.get(INTERFACE_ID)} not found.") from error

    def _initialize_commands(self, kwargs):
        """Parse and set commands to execute."""
        if COMMANDS_J2 not in kwargs:
            raise ValueError(f"{COMMANDS_J2} is required.")
        if self.call_object_type == "dcim.interface" and self.interface and hasattr(self.interface, "name"):
            self.intf_name = self.interface.name
            self.intf_name_only, self.intf_number = split_interface(self.intf_name)
            self.intf_abbrev = abbreviated_interface_name(self.interface.name)
        else:
            self.intf_name = self.intf_name_only = self.intf_number = self.intf_abbrev = None
        self.commands = self.parse_commands(kwargs.get(COMMANDS_J2))

    def run(self, *args, **kwargs):  # pylint: disable=too-many-locals
        """Main job logic: connect to device, execute commands, collect results."""
        callername = self.user.username  # type: ignore
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

        results = []
        with InitNornir(
            # runner={"plugin": "threadedrunner", "options": {"num_workers": 1}}
            runner={"plugin": "serial"},  # Serial runner has no options num_workers
            logging={"enabled": False},  # Disable logging because we are using our own logger
            inventory=inventory,
        ) as nornir_obj:
            nr_with_processors = nornir_obj.with_processors([ProcessLivedata(self.logger)])
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
                    # Support for !! filter syntax (e.g., "show run !! include Gi")
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
                        if filter_instruction:
                            task_result = apply_output_filter(task_result, filter_instruction)
                        results.append({"command": command, "task_result": task_result})
                    except NornirExecutionError as error:
                        raise ValueError(f"`E3001:` {error}") from error
            finally:
                if connection:
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
        return return_values


class LivedataCleanupJobResultsJob(Job):
    """Job to cleanup the Livedata Query Interface Job results."""

    class Meta:  # pylint: disable=too-few-public-methods
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

    def run(self, days_to_keep, dry_run, *args, **kwargs):  # pylint: disable=arguments-differ
        """Delete or count job results older than days_to_keep."""
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
