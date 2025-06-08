"""Signal handlers for the livedata_app."""

# filepath: nautobot_app_livedata/signals.py

from django.apps import apps as global_apps
from django.conf import settings
from django.db.models.signals import post_migrate
from django.dispatch import receiver
from nautobot.apps.choices import CustomFieldTypeChoices

from .utilities.customfield import create_custom_field
from .utilities.permission import create_permission


def get_plugin_settings():
    """Get the plugin settings."""
    if "nautobot_app_livedata" not in settings.PLUGINS_CONFIG:
        raise RuntimeError("Plugin 'nautobot_app_livedata' is not configured in settings.")
    return settings.PLUGINS_CONFIG["nautobot_app_livedata"]


class AppDbReadyState:  # pylint: disable=too-few-public-methods
    """App database ready state."""

    def __init__(self):
        self.is_dcim_ready = False
        self.is_nautobot_app_livedata_ready = False
        self.is_extras_ready = False
        self._db_objects = None
        self._content_typs = None
        self.already_initialized = False

    @property
    def is_ready(self):
        """Check if the app is ready."""
        return (
            not self.already_initialized
            and self.is_dcim_ready
            and self.is_nautobot_app_livedata_ready
            and self.is_extras_ready
            and self.try_init_objects()
        )

    def try_init_objects(self):
        """Try to initialize the database objects."""
        if not global_apps:
            return False
        if self._db_objects:
            return True
        try:
            db_objects = {
                "ContentType": global_apps.get_model("contenttypes", "ContentType"),
                "CustomField": global_apps.get_model("extras", "CustomField"),
                "Device": global_apps.get_model("dcim", "Device"),
                "Job": global_apps.get_model("extras", "Job"),
                "ObjectPermission": global_apps.get_model("users", "ObjectPermission"),
                "Permission": global_apps.get_model("auth", "Permission"),
                "Platform": global_apps.get_model("dcim", "Platform"),
            }
            content_typs = {
                "Device": db_objects["ContentType"].objects.get_for_model(db_objects["Device"]),  # type: ignore
                "Job": db_objects["ContentType"].objects.get_for_model(db_objects["Job"]),  # type: ignore
                "Platform": db_objects["ContentType"].objects.get_for_model(db_objects["Platform"]),  # type: ignore
            }
            for _, db_object in db_objects.items():
                if db_object.objects is None:
                    return False
            for _, content_typ in content_typs.items():
                if content_typ is None:
                    return False
            self._db_objects = db_objects
            self._content_typs = content_typs
        except Exception:  # pylint: disable=broad-except
            return False
        return True

    @property
    def db_objects(self):
        """Get the database objects."""
        return self._db_objects

    @property
    def content_typs(self):
        """Get the content types."""
        return self._content_typs


app_db_ready_state = AppDbReadyState()


@receiver(post_migrate)
def nautobot_database_ready_callback(sender, **kwargs):  # pylint: disable=unused-argument
    """
    Callback function triggered by the nautobot_database_ready signal and the post_migrate signal.

    There is a problem, that not all the models are ready when the nautobot_database_ready signal is triggered.
    So, we need to wait for the post_migrate signal to be triggered for the 'dcim' app.

    An App could use this callback to add any records to the database that it requires for proper operation,
    such as:

    - Relationship definitions
    - CustomField definitions
    - Webhook definitions
    - etc.

    Args:
        sender (NautobotAppConfig): The ExampleAppConfig instance that was registered for this callback
    """
    if not global_apps:
        return
    if "dcim" in repr(sender):
        app_db_ready_state.is_dcim_ready = True
    if "extras" in repr(sender):
        app_db_ready_state.is_extras_ready = True
    if "nautobot_app_livedata" in repr(sender):
        app_db_ready_state.is_nautobot_app_livedata_ready = True
    if not app_db_ready_state.is_ready:
        return
    app_db_ready_state.already_initialized = True
    # To make NAPALM requests via the Nautobot REST API, a Nautobot user
    # must have assigned a permission granting the 'napalm_read' action for
    # the device object type.
    create_permission(
        db_objects=app_db_ready_state.db_objects,  # type: ignore
        name="napalm_read",
        actions_list=["napalm_read"],
        description="Permission to make NAPALM requests via the Nautobot REST API.",
        content_type=app_db_ready_state.content_typs["Device"],  # type: ignore
    )

    # To allow the user to interact with the devices, like query the interfaces,
    # a Nautobot user must have assigned a permission granting the 'can_interact'
    # action for the device object type.
    create_permission(
        db_objects=app_db_ready_state.db_objects,  # type: ignore
        name="livedata.interact_with_devices",
        actions_list=["can_interact"],
        description="Interact with devices without permission to change device configurations.",
        content_type=app_db_ready_state.content_typs["Device"],  # type: ignore
    )

    # Create permission to run jobs
    create_permission(
        db_objects=app_db_ready_state.db_objects,  # type: ignore
        name="extras.run_job",
        actions_list=["run"],
        description="Run jobs",
        content_type=app_db_ready_state.content_typs["Job"],  # type: ignore
    )

    # Add the custom field to the Platform model, which is used to store the
    # Commands to display on the Interface page.
    field_data = {
        "key": "livedata_interface_commands",
        "type": CustomFieldTypeChoices.TYPE_MARKDOWN,
        "label": "Livedata Interface Commands",
        "description": (
            "Available variables for show commands. One a line:\n\n"
            "- {{ **obj** }}: the **Interface** object\n"
            "- {{ **device_**xxx }}: **ip, name**\n"
            "- {{ **intf_**xxx }}: **abbrev, name, name_only, number**"
        ),
        "default": "",
        "required": False,
        "filter_logic": "loose",
        "weight": 100,
        "advanced_ui": False,
    }
    cto = [app_db_ready_state.content_typs["Platform"]]  # type: ignore
    try:
        create_custom_field(db_objects=app_db_ready_state.db_objects, content_type_objects=cto, **field_data)
    except Exception as e:  # pylint: disable=broad-except
        print(f"ERROR: Database-Ready awaiting - {e}")
        return

    # Add the custom field to the Platform model, which is used to store the
    # Commands to display on the Interface page.
    field_data = {
        "key": "livedata_device_commands",
        "type": CustomFieldTypeChoices.TYPE_MARKDOWN,
        "label": "Livedata Device Commands",
        "description": (
            "Available variables for show commands. One a line:\n\n"
            "- {{ **obj** }}: the **Device** object\n"
            "- {{ **device_**xxx }}: **ip, name**\n"
        ),
        "default": "",
        "required": False,
        "filter_logic": "loose",
        "weight": 110,
        "advanced_ui": False,
    }
    cto = [app_db_ready_state.content_typs["Platform"]]  # type: ignore
    try:
        create_custom_field(db_objects=app_db_ready_state.db_objects, content_type_objects=cto, **field_data)
    except Exception as e:  # pylint: disable=broad-except
        print(f"ERROR: Database-Ready awaiting - {e}")
        return

    # Ensure that the jobs are enabled
    _enable_job(job_name=get_plugin_settings()["query_job_name"])
    _enable_job(job_name="Livedata Cleanup job results")


def _enable_job(job_name):
    """Enable the job with the given name.

    Args:
        apps (django.apps.apps.Apps): Use this to look up model classes as needed.
        job_name (str): The name of the job to enable.
    """
    Job = global_apps.get_model("extras", "Job")  # pylint: disable=invalid-name
    try:
        job = Job.objects.get(
            name=job_name,
        )
        if not job.enabled:  # type: ignore
            job.enabled = True  # type: ignore
            job.save()
            print(f"Database-Ready     - Job '{job_name}' enabled")
    except Job.DoesNotExist:
        print(f"WARNING: Database-Ready     - Job '{job_name}' not found")
