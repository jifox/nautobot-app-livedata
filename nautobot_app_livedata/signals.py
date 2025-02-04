"""Signal handlers for the livedata_app."""

# filepath: nautobot_app_livedata/signals.py

from django.apps import apps as global_apps
from django.conf import settings
from nautobot.apps.choices import CustomFieldTypeChoices

from .utilities import CustomFieldUtils
from .utilities.permission import PermissionDataObject, PermissionUtils

PLUGIN_SETTINGS = settings.PLUGINS_CONFIG["nautobot_app_livedata"]


def nautobot_database_ready_callback(sender, *, apps=global_apps, **kwargs):  # pylint: disable=unused-argument
    """
    Callback function triggered by the nautobot_database_ready signal when the Nautobot database is fully ready.

    This function is connected to that signal in ExampleAppConfig.ready().

    An App could use this callback to add any records to the database that it requires for proper operation,
    such as:

    - Relationship definitions
    - CustomField definitions
    - Webhook definitions
    - etc.

    Args:
        sender (NautobotAppConfig): The ExampleAppConfig instance that was registered for this callback
        apps (django.apps.apps.Apps): Use this to look up model classes as needed
        **kwargs: See https://docs.djangoproject.com/en/3.1/ref/signals/#post-migrate for additional args
    """
    # pylint: disable=invalid-name
    if not apps:
        return

    # To make NAPALM requests via the Nautobot REST API, a Nautobot user
    # must have assigned a permission granting the 'napalm_read' action for
    # the device object type.
    permission_data = PermissionDataObject(
        name="napalm_read",
        actions_list=["napalm_read"],
        description="Permission to make NAPALM requests via the Nautobot REST API.",
        full_model_name="dcim.device",
        is_in_database_ready=True,
    )
    permission_utils = PermissionUtils(permission_data)
    permission_utils.create_permission()
    # To allow the user to interact with the devices, like query the interfaces,
    # a Nautobot user must have assigned a permission granting the 'can_interact'
    # action for the device object type.
    permission_data = PermissionDataObject(
        name="livedata.interact_with_devices",
        actions_list=["can_interact"],
        description="Interact with devices without permission to change device configurations.",
        full_model_name="dcim.device",
    )
    permission_utils = PermissionUtils(permission_data)
    permission_utils.create_permission()
    # Add the custom field to the Platform model, which is used to store the
    # Commands to display on the Interface page.

    key_name = "livedata_interface_commands"
    field_type = CustomFieldTypeChoices.TYPE_MARKDOWN
    defaults = {
        "type": field_type,
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
        "advanced_ui": True,
    }
    CustomFieldUtils(
        key_name=key_name,
        field_type=field_type,
        defaults=defaults,
        model_names=["dcim.interface"],
        is_in_database_ready=True,
    ).add_custom_field()

    # Ensure that the jobs are enabled
    _enable_job(apps, job_name=PLUGIN_SETTINGS["query_interface_job_name"])
    _enable_job(apps, job_name="Livedata Cleanup job results")


def _enable_job(apps, job_name):
    """Enable the job with the given name.

    Args:
        apps (django.apps.apps.Apps): Use this to look up model classes as needed.
        job_name (str): The name of the job to enable.
    """
    print(f"Database-Ready - Enabling job '{job_name}'...")
    Job = apps.get_model("extras", "Job")  # pylint: disable=invalid-name
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
    print(f"Database-Ready     - Job '{job_name}' already enabled")
