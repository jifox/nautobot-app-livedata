"""Jobs for the Nautobot App Livedata API."""

from datetime import datetime

import jinja2
from django.utils import timezone
from django.utils.timezone import make_aware
from nautobot.apps.jobs import DryRunVar, IntegerVar, Job, register_jobs
from nautobot.dcim.models import Device, Interface, VirtualChassis
from nautobot.extras.models import JobResult
from nautobot_plugin_nornir.constants import NORNIR_SETTINGS
from nautobot_plugin_nornir.plugins.inventory.nautobot_orm import NautobotORMInventory
from netutils.interface import abbreviated_interface_name, split_interface
from nornir import InitNornir
from nornir.core.exceptions import NornirExecutionError
from nornir.core.plugins.inventory import InventoryPluginRegister

from .api.utils import GetManagedDevice
from .nornir_plays.processor import ProcessLivedata
from .urls import APP_NAME, PLUGIN_SETTINGS

# Groupname: Livedata
name = GROUP_NAME = APP_NAME  # pylint: disable=invalid-name

InventoryPluginRegister.register("nautobot-inventory", NautobotORMInventory)


class LivedataQueryInterfaceJob(Job):  # pylint: disable=too-many-instance-attributes
    """Job to query live data on an interface.

    For more information on implementing jobs, refer to the Nautobot job documentation:
    https://docs.nautobot.com/projects/core/en/stable/development/jobs/

    Args:
        commands_j2 (List[str]): The commands to execute in jinja2 syntax.
        device_id (int): The device ID.
        interface_id (int): The interface ID.
        managed_device_id (int): The managed device ID with management ip.
        remote_addr (str): The request.META.get("REMOTE_ADDR").
        virtual_chassis_id (int): The virtual chassis ID.
        x_forwarded_for (str): The request.META.get("HTTP_X_FORWARDED_FOR").
        *args: Additional arguments.
        **kwargs: Additional keyword arguments.
    """

    class Meta:  # pylint: disable=too-few-public-methods
        """Metadata for the Livedata Query Interface Job."""

        name = PLUGIN_SETTINGS.get("query_interface_job_name")
        description = PLUGIN_SETTINGS.get("query_interface_job_description")
        has_sensitive_variables = False
        hidden = PLUGIN_SETTINGS.get("query_interface_job_hidden")
        soft_time_limit = PLUGIN_SETTINGS.get("query_interface_job_soft_time_limit")
        enabled = True

    def __init__(self, *args, **kwargs):
        """Initialize the Livedata Query Interface Job variables."""
        super().__init__(*args, **kwargs)  # defines self.logger
        self.callername = None  # The user who initiated the job
        self.commands = []  # The commands to execute
        self.device = None
        self.interface = None  # The interface object
        self.remote_addr = None  # The remote address request.META.get("REMOTE_ADDR")
        self.managed_device = None  # The managed device object that will be used to execute the commands
        self.virtual_chassis = None  # The virtual chassis object if applicable
        self.x_forwarded_for = None  # The forwarded address request.META.get("HTTP_X_FORWARDED_FOR")
        self.results = []  # The results of the command execution
        self.intf_name = None  # The interface name (e.g. "GigabitEthernet1/0/10")
        self.intf_name_only = None  # The interface name without the number (e.g. "GigabitEthernet")
        self.intf_number = None  # The interface number (e.g. "1/0/10")
        self.intf_abbrev = None  # The abbreviated interface name (e.g. "Gi1/0/10")
        self.device_name = None  # The device name of the device where the interface is located
        self.device_ip = None  # The primary IP address of the managed device
        self.execution_timestamp = None  # The current timestamp in the format "YYYY-MM-DD HH:MM:SS"
        self.now = None  # The current timestamp

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
            "managed_device": self.managed_device.name,  # type: ignore
            "device_ip": self.device_ip,
            "obj": self.interface,
            "timestamp": self.execution_timestamp,
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
            ValueError: If the managed device with the provided managed_device_id is not found.
        """
        super().before_start(task_id, args, kwargs)
        self.callername = self.user.username  # type: ignore
        # ManagedDevice is the device that is manageabe

        self.now = make_aware(datetime.now())

        # Initialize the job-specific variables
        self._initialize_interface(kwargs)
        self._initialize_managed_device(kwargs)
        self.device_name = self.managed_device.name
        self.device_ip = self.managed_device.primary_ip.address  # type: ignore
        self._initialize_device(kwargs)
        self._initialize_virtual_chassis(kwargs)
        if "user" in kwargs:
            self.user = kwargs.get("user")  # type: ignore
        if "remote_addr" in kwargs:
            self.remote_addr = kwargs.get("remote_addr")
        if "x_forwarded_for" in kwargs:
            self.x_forwarded_for = kwargs.get("x_forwarded_for")
        # Initialize the show commands
        if "commands_j2" not in kwargs:
            raise ValueError("commands_j2 is required.")
        self.intf_name = self.interface.name
        self.intf_name_only, self.intf_number = split_interface(self.intf_name)
        self.intf_abbrev = abbreviated_interface_name(self.interface.name)
        self.commands = self.parse_commands(kwargs.get("commands_j2"))
        self.execution_timestamp = self.now.strftime("%Y-%m-%d %H:%M:%S")

    def _initialize_virtual_chassis(self, kwargs):
        """Initialize the virtual chassis object if applicable."""
        if "virtual_chassis_id" in kwargs:
            virtual_chassis_id = kwargs.get("virtual_chassis_id")
            if virtual_chassis_id:
                self.virtual_chassis = VirtualChassis.objects.get(pk=virtual_chassis_id)

    def _initialize_device(self, kwargs):
        """Initialize the device object."""
        if "device_id" in kwargs:
            device_id = kwargs.get("device_id")
        else:
            device_id = self.interface.device.id  # type: ignore
        if device_id:
            self.device = Device.objects.get(pk=device_id)
            self.device_name = self.device.name

    def _initialize_managed_device(self, kwargs):
        """Initialize the managed device object."""
        if "managed_device_id" not in kwargs:
            managed_device_id = GetManagedDevice("dcim.interface", self.interface.id).managed_device.id  # type: ignore
        else:
            managed_device_id = kwargs.get("managed_device_id")
        try:
            self.managed_device = Device.objects.get(pk=managed_device_id)
        except Device.DoesNotExist:
            raise ValueError(f"Managed Device with ID {managed_device_id} not found.")  # pylint: disable=raise-missing-from

    def _initialize_interface(self, kwargs):
        """Initialize the interface object."""
        if "interface_id" not in kwargs:
            raise ValueError("interface_id is required.")
        try:
            self.interface = Interface.objects.get(pk=kwargs.get("interface_id"))
        except Interface.DoesNotExist as error:
            raise ValueError(f"Interface with ID {kwargs.get('interface_id')} not found.") from error

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
            managed_device (int): The managed device ID.
            remote_addr (str): The remote address.
            virtual_chassis_id (int): The virtual chassis ID.
            x_forwarded_for (str): The forwarded address.
            *args: Additional arguments.
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
        # ManagedDevice is the device that is manageabe

        now = make_aware(datetime.now())
        qs = Device.objects.filter(id=self.managed_device.id).distinct()  # type: ignore

        data = {
            "now": now,
            "caller": callername,
            "interface": self.interface,
            "device_name": self.device_name,
            "device_ip": self.managed_device.primary_ip.address,  # type: ignore
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
            connection = (
                nr_with_processors.filter(name=self.device_name)
                .inventory.hosts[self.device_name]  # type: ignore
                .get_connection("netmiko", nr_with_processors.config)
            )
            try:
                for command in self.commands:
                    try:
                        self.logger.debug(f"Executing '{command}' on device {self.device_name}")
                        task_result = connection.send_command(command)
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
            job_model__name=PLUGIN_SETTINGS["query_interface_job_name"],
            status="SUCCESS",
        )
        cleanup_job_results = JobResult.objects.filter(
            date_done__lt=cutoff_date,
            job_model__name="livedata_cleanup_job_results",
            status="SUCCESS",
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


print("Registering Jobs: LivedataQueryInterfaceJob, LivedataCleanupJobResultsJob")
register_jobs(LivedataQueryInterfaceJob, LivedataCleanupJobResultsJob)
