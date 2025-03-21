"""Utilities for working with permissions in Nautobot."""


def create_permission(db_objects: dict, name: str, actions_list: list, description: str, content_type):
    """Create a permission in the database.

    Args:
        db_objects (dict): The database objects. Must contain the ContentType and ObjectPermission models.
        name (str): The name of the permission.
        actions_list (list): The list of actions.
        description (str): The description of the permission.
        content_type (ContentType): The content type of the permission.

    Raises:
        ValueError: If database objects are not provided.
    """
    if not db_objects:
        raise ValueError("Database objects are required")
    ObjectPermission = db_objects["ObjectPermission"]  # pylint: disable=invalid-name
    try:
        permission = ObjectPermission.objects.get(name=name)
    except ObjectPermission.DoesNotExist:
        permission = ObjectPermission.objects.create(
            name=name,
            actions=actions_list,
            description=description,
        )
        permission.validated_save()
    if permission.object_types.count() == 0 or not permission.object_types.filter(id=content_type.id).exists():
        try:
            permission.object_types.add(content_type)  # type: ignore
            permission.validated_save()
        except Exception as e:  # pylint: disable=broad-except
            print(f"ERROR: Could not assign permission to content type: {e}")
