"""Signal handlers for the livedata_app."""

from django.apps import apps as global_apps
from django.conf import settings

PLUGIN_SETTINGS = settings.PLUGINS_CONFIG["nautobot_app_livedata"]


def nautobot_database_ready_callback(sender, *, apps=global_apps, **kwargs):
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

    # ADD PERMISSIONS
    # Get the model classes we need

    # To make NAPALM requests via the Nautobot REST API, a Nautobot user
    # must have assigned a permission granting the napalm_read action for
    # the device object type.
    _set_permission(
        name="napalm_read",
        actions_list=["napalm_read"],
        description="Permission to make NAPALM requests via the Nautobot REST API.",
        model_name="dcim.device",
    )
    _set_permission(
        name="interact with devices",
        actions_list=["can_interact"],
        description="Interact with devices without permission to change device configurations.",
        model_name="dcim.device",
    )

    # ADD CUSTOM FIELDS
    ContentType = apps.get_model("contenttypes", "ContentType")
    content_type_platform = apps.get_model("dcim", "Platform")

    from nautobot.extras.choices import CustomFieldTypeChoices

    key_name = "livedata_interface_commands"
    field_type = CustomFieldTypeChoices.TYPE_MARKDOWN

    CustomField = apps.get_model("extras", "CustomField")
    # Check if the custom field already exists
    try:
        CustomField.objects.get(
            type=field_type,
            key=key_name,
        )
    except CustomField.DoesNotExist:
        field, created = CustomField.objects.update_or_create(
            key=key_name,
            defaults={
                "type": field_type,
                "label": "Livedata Interface Commands",
                "description": (
                    "Available variables for show commands. One a line:\n\n"
                    "- {{ **obj** }}: Interface object\n"
                    "- {{ **device_**xxx }}: **ip, name**\n"
                    "- {{ **intf_**xxx }}: **abbrev, name, name_only, number**"
                ),
                "default": "",
                "required": False,
                "filter_logic": "loose",
                "weight": 100,
                "advanced_ui": True,
            },
        )
        field.save()
        field.content_types.set([ContentType.objects.get_for_model(content_type_platform)])
        field.save()

    # Ensure that the job is enabled
    Job = apps.get_model("extras", "Job")
    try:
        job = Job.objects.get(
            name=PLUGIN_SETTINGS["query_interface_job_name"],
        )
        if not job.enabled:
            job.enabled = True
            job.save()
    except Job.DoesNotExist:
        print(f"WARNING: Job {PLUGIN_SETTINGS['query_interface_job_name']} not found")


def _set_permission(name, actions_list, description, model_name, apps=global_apps):
    """Create a permission with the given name, actions and description and assign it to the model_name.

    Args:
        name (str): The name of the permission.
        actions_list (list): The list of actions the permission can do.
        description (str): The description of the permission.
        model_name (str): The model name to assign the permission to.
            Must be in the format 'app_label.model_name' e.g. 'dcim.device'.
        apps (django.apps.apps.Apps): Use this to look up model classes as needed.

    Raises:
        ValueError: If the model_name is not in the format 'app_label.model_name'.
    """
    # Get the model class name we need assing the content type to the permission
    model_info = model_name = model_name.split(".")
    if len(model_info) != 2:
        raise ValueError("Model name must be in the format 'app_label.model_name'")
    app_label = model_info[0].lower()
    model_name = model_info[1].lower()

    ObjectPermission = apps.get_model("users", "ObjectPermission")
    permission, created = ObjectPermission.objects.get_or_create(
        name=name,
        actions=actions_list,
        description=description,
    )
    if created:
        # Add the content type to the permission
        permission.save()
        ContentType = apps.get_model("contenttypes", "ContentType")  # pylint: disable=invalid-name
        permission_content_type_model = ContentType.objects.get(app_label=app_label, model=model_name)
        permission.content_types.set([ContentType.objects.get_for_model(permission_content_type_model)])  # type: ignore
        permission.save()
        print(f"Permissions {name} created")
