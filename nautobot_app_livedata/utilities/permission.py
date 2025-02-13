"""Utilities for working with permissions in Nautobot."""


def create_permission(db_objects: dict, name: str, actions_list: list, description: str, full_model_name: str):
    """Create a permission in the database.

    Args:
        db_objects (dict): The database objects. Must contain the ContentType and ObjectPermission models.
        name (str): The name of the permission.
        actions_list (list): The list of actions.
        description (str): The description of the permission.
        full_model_name (str): The full model name.

    Raises:
        ValueError: If database objects are not provided.
    """
    if not db_objects:
        raise ValueError("Database objects are required")
    ContentType = db_objects["ContentType"]  # pylint: disable=invalid-name
    full_model_name = full_model_name.lower()
    app_label, model = full_model_name.split(".")
    try:
        content_type = ContentType.objects.get(app_label=app_label, model=model)
    except ContentType.DoesNotExist:
        print(
            f"Missing app_label={app_label}', model={model}'.",
            "\nYou must assign the permission to a content type manually.",
        )
    ObjectPermission = db_objects["ObjectPermission"]  # pylint: disable=invalid-name
    permission = ObjectPermission.objects.filter(name=name).first()
    if not permission:
        permission = ObjectPermission.objects.create(
            name=name,
            actions=actions_list,
            description=description,
        )
        permission.validated_save()
    if permission.object_types.count() == 0:  # type: ignore
        permission.object_types.set([content_type])  # type: ignore
        permission.validated_save()
