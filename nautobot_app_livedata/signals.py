"""Signal handlers for the livedata_app."""

from django.apps import apps as global_apps
from django.conf import settings
from django.db import DEFAULT_DB_ALIAS, router

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
    _set_permission(
        name="napalm_read",
        actions_list=["napalm_read"],
        description="Permission to make NAPALM requests via the Nautobot REST API.",
        model_name="dcim.device",
    )
    # To allow the user to interact with the devices, like query the interfaces,
    # a Nautobot user must have assigned a permission granting the 'can_interact'
    # action for the device object type.
    _set_permission(
        name="interact with devices",
        actions_list=["can_interact"],
        description="Interact with devices without permission to change device configurations.",
        model_name="dcim.device",
    )
    # Add the custom field to the Platform model, which is used to store the
    # Commands to display on the Interface page.
    from nautobot.extras.choices import CustomFieldTypeChoices  # pylint: disable=import-outside-toplevel

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
    _add_custom_field(
        apps, key_name=key_name, field_type=field_type, defaults=defaults, app_label="dcim", model_name="interface"
    )

    # Ensure that the jobs are enabled
    _enable_job(apps, job_name=PLUGIN_SETTINGS["query_interface_job_name"])
    _enable_job(apps, job_name="Livedata Cleanup job results")


def _get_content_type(apps):
    """Get the ContentType model.

    Args:
        apps (django.apps.apps.Apps): Use this to look up model classes as needed.

    Returns:
        ContentType: The ContentType model or None if it is not available.
    """
    print("Database-Ready - Checking if ContentType model is available...")
    # Determine whether or not the ContentType model is available.
    try:
        ContentType = apps.get_model("contenttypes", "ContentType")  # pylint: disable=invalid-name
    except LookupError:
        available = False
    else:
        available = router.allow_migrate_model(DEFAULT_DB_ALIAS, ContentType)
    # The ContentType model is not available yet.
    if not available:
        print("WARNING: Database-Ready - ContentType model is not available")
        return None
    print("Database-Ready - ContentType model is available")
    return ContentType


def _add_custom_field(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    apps, key_name, field_type, defaults, app_label, model_name
):
    """Add a custom field with the given key name and field type.

    Args:
        apps (django.apps.apps.Apps): Use this to look up model classes as needed.
        key_name (str): The key name of the custom field.
        field_type (str): The type of the custom field.
        defaults (dict): The default values for the custom field.
        app_label (str): The app label of the model.
        model_name (str): The model name of the model.
    """
    print(f"Database-Ready - Creating custom field {key_name}...")
    CustomField = apps.get_model("extras", "customfield")  # pylint: disable=invalid-name
    # Check if the custom field already exists
    try:
        field = CustomField.objects.get(
            type=field_type,
            key=key_name,
        )
        print(f"Database-Ready     - Custom field {key_name} already exists")
    except CustomField.DoesNotExist:
        field, created = CustomField.objects.update_or_create(
            key=key_name,
            defaults=defaults,
        )
        if created:
            field.save()
            print(f"Database-Ready     - Custom field '{key_name}' created")

    # if the ContentType of the field is empty, assign it
    if not field.content_types:
        print(f"Database-Ready     - Assigning content type '{app_label}.{model_name}' to custom field '{key_name}'...")
        ContentType = _get_content_type(apps)  # pylint: disable=invalid-name
        if not ContentType or not app_label or not model_name:
            print(
                "WARNING: Database-Ready     - Could not assign the content type",
                f"'{app_label}.{model_name}'",
                "to the custom field",
                f"'{key_name}'!",
            )
            print("WARNING: Database-Ready     - Assign the content type manually.")
            return
        ContentType = _get_content_type(apps)  # pylint: disable=invalid-name
        print(f"Database-Ready     - ContentType.objects.get(app_label={app_label}, model={model_name})")
        try:
            content_type_model = ContentType.objects.get(app_label=app_label, model=model_name)
        except ContentType.DoesNotExist:
            # Add the ContentType for model specified in the app_label and model_name
            print(f"WARNING: Database-Ready     - ContentType.DoesNotExist:")

        field.content_types.set([content_type_model])  # type: ignore
        field.save()
        print(f"Database-Ready     - ContenType '{app_label}.{model_name}' assigned to custom field '{key_name}'")
    else:
        print(
            f"Database-Ready     - ContenType '{app_label}.{model_name}' already assigned to custom field '{key_name}'"
        )


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
    print(f"Database-Ready - Creating permissions {name}...")
    # Get the model class name we need assing the content type to the permission
    model_info = model_name = model_name.split(".")
    if len(model_info) != 2:
        raise ValueError("Model name must be in the format 'app_label.model_name'")
    app_label = model_info[0].lower()
    model_name = model_info[1].lower()

    ObjectPermission = apps.get_model("users", "objectpermission")  # pylint: disable=invalid-name
    permission, created = ObjectPermission.objects.get_or_create(
        name=name,
        actions=actions_list,
        description=description,
    )
    if created:
        # Add the content type to the permission
        permission.save()
    if not permission.object_types:  # type: ignore
        print(f"Database-Ready     - Assigning content type {app_label}.{model_name} to permission {name}...")
        ContentType = apps.get_model("contenttypes", "contentType")  # pylint: disable=invalid-name
        permission_content_type_model = ContentType.objects.get(app_label=app_label, model=model_name)
        permission.object_types.set([permission_content_type_model])  # type: ignore
        permission.save()
        print(f"Database-Ready     - Permissions {name} created")
    else:
        print(f"Database-Ready     - Permissions {name} already exists")
