"""Utilities for working with custom fields in Nautobot."""

from nautobot.apps.choices import CustomFieldTypeChoices

from nautobot_app_livedata.utilities.contenttype import ContentTypeUtils


# https://docs.nautobot.com/projects/core/en/stable/user-guide/platform-functionality/customfield/
#
class CustomFieldUtils:
    """Utility functions for working with custom fields."""

    def __init__(self, key_name=None, field_type=None, defaults=None, model_names=None, is_in_database_ready=False):
        """Initialize the CustomFieldUtils."""
        self.is_in_database_ready = is_in_database_ready
        self._field_type = None
        self.field_type = field_type
        self._key_name = None
        self.key_name = key_name
        self._defaults = None
        self._model_names = None
        self.model_names = model_names
        self._assign_to_models = set()
        if defaults is None:
            self._defaults = {
                "label": key_name,
                "description": None,
                "default": None,
                "required": False,
                "filter_logic": "loose",  # (loose versus exact) determines whether partial or full matching is used.
                "weight": 100,
                "advanced_ui": False,
            }
        else:
            self._defaults = defaults

    @property
    def field_type(self):
        """Retrieve the field type."""
        return self._field_type

    @field_type.setter
    def field_type(self, value):
        """Set the field type to a value in CustomFieldTypeChoices."""
        if value not in CustomFieldTypeChoices.values():
            raise ValueError(f"Invalid field_type '{value}'. Must be one of {CustomFieldTypeChoices.values()}")
        self._field_type = value

    @property
    def key_name(self):
        """Retrieve the key name."""
        return self._key_name

    @key_name.setter
    def key_name(self, value):
        """Set the key name."""
        if not isinstance(value, str):
            raise ValueError("key_name must be a string")
        if not value.isidentifier():
            raise ValueError(f"Invalid key_name '{value}'. Must be a valid GraphQL identifier.")
        self._key_name = value

    @property
    def model_names(self):
        """Retrieve the model names."""
        return self._model_names

    @model_names.setter
    def model_names(self, value):
        """Set the model names."""
        if not isinstance(value, list):
            raise ValueError("model_names must be a list")
        self._assign_to_models = set()
        for model_name in value:
            if not isinstance(model_name, str):
                raise ValueError("model_name must be a string")
            if not model_name.count(".") == 1:
                raise ValueError(f"Invalid model_name '{model_name}'. Must be in the format 'app_label.model_name'.")
            self._assign_to_models.add(
                ContentTypeUtils(
                    full_model_name=model_name, is_in_database_ready=self.is_in_database_ready
                ).content_type_for_model
            )
        self._model_names = value

    def __repr__(self):
        return (
            f"CustomFieldUtils(key_name={self.key_name}, "
            f"field_type={self.field_type}, "
            f"defaults={self.defaults}, "
            f"model_name={self.model_names}"
        )

    def __str__(self):
        return f"CustomFieldUtils: {self.key_name}"

    def add_custom_field(self):
        """Add a custom field with the given key name and field type.

        Raises:
            ValueError: If the model_name is not in the format 'app_label.model_name'.
            ValueError: If the field_type is not in CustomFieldTypeChoices.
        """
        if self.field_type not in CustomFieldTypeChoices.values():
            raise ValueError(
                f"Invalid field_type '{self.field_type}'. Must be one of {CustomFieldTypeChoices.values()}"
            )
        CustomField = ContentTypeUtils(full_model_name="extras.customfield").model
        field, created = CustomField.objects.get_or_create(
            type=self.field_type, key=self.key_name, defaults=self._defaults
        )
        if created:
            field.save()

        if field.content_types.count() == 0:
            field.content_types.set(self._assign_to_models)
            field.save()
        return field
