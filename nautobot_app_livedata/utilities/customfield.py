"""Utilities for working with custom fields in Nautobot."""


def create_custom_field(db_objects, content_type_objects=None, **kwargs):
    """Create a custom field with the given key name and field type.

    Args:
        db_objects (dict): The database objects to use for the creation.
        content_types (list[str]): The model names to assign the custom field to. "app_label.model_name"

    Keyword Args:
        key (str): The key name of the custom field.
        type (str): The CustomFieldTypeChoices type of the custom field.
        label (str): The label of the custom field.
        description (str): The description of the custom field.
        default (str): The default value of the custom field.
        required (bool): The required status of the custom field.
        filter_logic (str): (loose|strict) The filter logic of the custom field.
        weight (int): The weight of the custom field.
        advanced_ui (bool): The advanced UI status of the custom field. Defaults to True.

    Raises:
        ValueError: If the model_name is not in the format 'app_label.model_name'.
        ValueError: If the field_type is not in CustomFieldTypeChoices.
    """
    if content_type_objects is None:
        content_type_objects = []
    CustomField = db_objects["CustomField"]  # pylint: disable=invalid-name
    custom_field_key = kwargs.pop("key")
    custom_field_modified = False
    try:
        custom_field = CustomField.objects.get(key=custom_field_key)
        for key, value in kwargs.items():
            if getattr(custom_field, key) != value:
                custom_field_modified = True
                setattr(custom_field, key, value)
    except CustomField.DoesNotExist:
        custom_field_modified = True
        custom_field = CustomField.objects.create(**kwargs)
    if custom_field_modified:
        custom_field.validated_save()
        custom_field.refresh_from_db()

    added_content_types = False
    if content_type_objects:
        # Assign the custom field to the given content types.
        ContentType = db_objects["ContentType"]  # pylint: disable=invalid-name
        for content_type in content_type_objects:
            # check if contenttyp is already assigned
            if custom_field.content_types.filter(id=content_type.id).exists():
                continue
            try:
                custom_field.content_types.add(content_type)
                added_content_types = True
            except ContentType.DoesNotExist:
                print(
                    "WARNING: Could not assign custom field to content type.",
                    f"\nYou must assign the custom field {custom_field} to a content type {content_type} manually!",
                )
    if added_content_types:
        custom_field.validated_save()
