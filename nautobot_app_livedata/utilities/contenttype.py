"""Utilities for working with the ContentType model."""

from django.apps import apps as global_apps
from django.db import DEFAULT_DB_ALIAS, router


class ContentTypeUtils:  # pylint: disable=too-many-instance-attributes
    """Utility functions for working with the ContentType model."""

    def __init__(self, full_model_name=None, is_in_database_ready=False):
        self.apps = global_apps
        self._app_name = None
        self._content_type_model = None
        self._full_model_name = None
        self._app_label = None
        self._model_name = None
        self.is_in_database_ready = is_in_database_ready
        self.permission_content_type_model = None
        if full_model_name is not None:
            self._full_model_name = full_model_name
        self._app_name, self._model_name = self._split_app_model(full_model_name)
        try:
            self._content_type = self.get_content_type()
        except AttributeError:
            self._content_type = None

    @property
    def ContentType(self):  # pylint: disable=invalid-name
        """Retrieve the ContentType model.

        Returns:
            ContentType: The ContentType model or None if it is not available.
        """
        if self._content_type is None:
            self._content_type = self.get_content_type()
        return self._content_type

    @property
    def full_model_name(self):
        """Retrieve the full model name.

        Returns:
            str: The full model name.
        """
        return self._full_model_name

    @full_model_name.setter
    def full_model_name(self, value):
        """Set the full model name.

        Args:
            value (str): The full model name to set. Must be in the format 'app_label.model_name'.

        Raises:
            ValueError: If the value is not in the format 'app_label.model_name'.
        """
        self._app_name, self._model_name = self._split_app_model(value)

    @property
    def app_name(self):
        """Retrieve the app name.

        Returns:
            str: The app name.
        """
        return self._app_name

    @app_name.setter
    def app_name(self, value):
        """Set the app name.

        Args:
            value (str): The app name to set.
        """
        if self._app_name is None:
            self._app_name = value
        if self._app_name is not None and self._model_name is not None:
            self.full_model_name = f"{value}.{self._model_name}"
        else:
            self._full_model_name = None

    @property
    def model_name(self):
        """Retrieve the model name.

        Returns:
            str: The model name.
        """
        return self._model_name

    @model_name.setter
    def model_name(self, value):
        """Set the model name.

        Args:
            value (str): The model name to set.
        """
        if self._model_name is None:
            self._model_name = value
        if self._app_name is not None and self._model_name is not None:
            self.full_model_name = f"{self._app_name}.{value}"
        else:
            self._full_model_name = None

    @property
    def content_type_for_model(self):
        """Retrieve the ContentType for the model.

        Returns:
            ContentType: The ContentType model for the model.

        Raises:
            ValueError: If the model_name is not in the format 'app_label.model_name'.
            ValueError: If the ContentType for the model is not found.
        """
        if self._full_model_name is None:
            raise ValueError("full_model_name is required")
        return self._fetch_content_type_for_model()

    def get_content_type(self):
        """Retrieve the ContentType model.

        This function retrieves the ContentType model and can be used during
        the database_ready signal.

        Args:
            apps (django.apps.apps.Apps): Used to look up model classes as needed.
            is_in_database_ready (bool): If the function is being called from
                the database_ready signal. Default is False.

        Returns:
            ContentType: The ContentType model, or None if it is not available.

        Raises:
            ValueError: If the ContentType model is not available and is_in_database_ready is False.
        """
        try:
            self._content_type = self.apps.get_model("contenttypes", "ContentType")
        except LookupError:
            available = False
        else:
            available = router.allow_migrate_model(DEFAULT_DB_ALIAS, self._content_type)
        # The ContentType model is not available yet.
        if not available:
            if self.is_in_database_ready:
                print("get_content_type - ContentType model is not available")
                return None
            raise ValueError("ContentType model is not available")
        return self._content_type

    def _fetch_content_type_for_model(self):
        """Fetch the ContentType for the model.

        Args:
            full_model_name (str): The full model name to fetch the ContentType for.
                Must be in the format 'app_label.model_name'.
        Returns:
            ContentType: The ContentType model for the model.

        Raises:
            ValueError: If the full_model_name is not set.
            ValueError: If the ContentType for the model is not found.
        """
        if self._full_model_name is None:
            raise ValueError("full_model_name is required")
        self.get_content_type()
        try:
            self._content_type_model = self.ContentType.objects.get(  # type: ignore
                app_label=self.app_name, model=self.model_name
            )
        except Exception as error:  # pylint: disable=broad-except
            self._content_type_model = None
            if self.is_in_database_ready:
                print(f"fetch_content_type_for_model - ContentType {self.full_model_name} not found - {error}")
            else:
                raise ValueError(  # pylint: disable=raise-missing-from
                    f"ContentType {self.full_model_name} not found - {error}"
                )
        return self._content_type_model

    def _split_app_model(self, full_model_name):
        """Split the model name into app_label and model_name.

        Args:
            full_model_name (str): The full model name to split.

        Returns:
            tuple: The app_label and model_name.

        Raises:
            ValueError: If the full_model_name is not in the format 'app_label.model_name'
        """
        try:
            full_model_name = full_model_name.lower()
        except AttributeError:
            raise ValueError("Model name must be a string")  # pylint: disable=raise-missing-from
        model_info = full_model_name.split(".")
        if len(model_info) != 2:
            raise ValueError("Model name must be in the format 'app_label.model_name'")
        self._app_label = model_info[0].lower()
        self._model_name = model_info[1].lower()
        self._full_model_name = ".".join([self._app_label, self._model_name])
        return self._app_label, self._model_name

    @property
    def model(self):
        """Retrieve the model.

        Returns:
            Model: The model.
        """
        return self.apps.get_model(self._app_label, self._model_name)  # type: ignore
