"""Utilities for working with permissions in Nautobot."""

from nautobot_app_livedata.utilities import contenttype

from .contenttype import ContentTypeUtils


class PermissionDataObject:
    """Data object for creating permissions."""

    def __init__(  # pylint: disable=too-many-arguments too-many-positional-arguments
        self,
        name=None,
        actions_list=None,
        description=None,
        full_model_name=None,
        is_in_database_ready=None,
        **kwargs,
    ):
        """Initialize the PermissionDataObject.

        Args:
            name (str): The name of the permission.
            actions_list (list[str]): The list of actions for the permission.
            description (str): The description of the permission.
            full_model_name (str): The full model name of the permission.
            **kwargs: Allow initialization of the object with a dictionary.

        Example:
            # Create a PermissionDataObject
            permission_data_object = PermissionDataObject(
                name="livedata.interact_with_devices",
                actions_list=["can_interact"],
                description="Interact with devices without permission to change device configurations.",
                full_model_name="dcim.device",
            )

            # Create a PermissionDataObject with a dictionary
            data = {
                "name": "livedata.interact_with_devices",
                "actions_list": ["can_interact"],
                "description": "Interact with devices without permission to change device configurations.",
                "full_model_name": "dcim.device",
            }

            permission_data_object = PermissionDataObject(**data)
        """
        if kwargs:
            self.name = kwargs.get("name")
            self.actions_list = kwargs.get("actions_list")
            self.description = kwargs.get("description")
            self.full_model_name = kwargs.get("full_model_name")
        else:
            self.name = name
            self.actions_list = actions_list
            self.description = description
            self.full_model_name = full_model_name
        if is_in_database_ready is None:
            self.is_in_database_ready = False
        else:
            self.is_in_database_ready = is_in_database_ready

    def __repr__(self):
        return (
            f"<PermissionDataObject name={self.name} actions_list={self.actions_list} "
            f"description={self.description} full_model_name={self.full_model_name}>"
        )

    def __str__(self):
        return f"{self.name} {self.actions_list} {self.description} {self.full_model_name}"

    def __eq__(self, other):
        if not isinstance(other, PermissionDataObject):
            return False
        return (
            self.name == other.name
            and self.actions_list == other.actions_list
            and self.description == other.description
            and self.full_model_name == other.full_model_name
        )

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash((self.name, self.actions_list, self.description, self.full_model_name))

    def __lt__(self, other):
        if not isinstance(other, PermissionDataObject):
            return NotImplemented
        return self.name < other.name

    def __le__(self, other):
        if not isinstance(other, PermissionDataObject):
            return NotImplemented
        return self.name <= other.name

    def __gt__(self, other):
        if not isinstance(other, PermissionDataObject):
            return NotImplemented
        return self.name > other.name

    def __ge__(self, other):
        if not isinstance(other, PermissionDataObject):
            return NotImplemented
        return self.name >= other.name

    def __len__(self):
        return len(self.name)

    def __getitem__(self, key):
        return self.__dict__[key]

    def __setitem__(self, key, value):
        self.__dict__[key] = value

    def __delitem__(self, key):
        del self.__dict__[key]

    def __contains__(self, key):
        return key in self.__dict__

    def __iter__(self):
        return iter(self.__dict__)

    def __reversed__(self):
        return reversed(self.__dict__)

    def __copy__(self):
        data = {
            "name": self.name,
            "actions_list": self.actions_list,
            "description": self.description,
            "full_model_name": self.full_model_name,
        }
        return PermissionDataObject(**data)


class PermissionUtils:  # pylint: disable=too-many-instance-attributes
    """Utility functions for creating permissions."""

    def __init__(self, permission_data_object: PermissionDataObject, is_in_database_ready=False):
        self.content_type_utils = ContentTypeUtils(is_in_database_ready=is_in_database_ready)
        self._name = permission_data_object.name
        self._action_list = permission_data_object.actions_list
        self._description = permission_data_object.description
        self.full_model_name = permission_data_object.full_model_name

    @property
    def actions_list(self):
        """Retrieve the action list.

        Returns:
            list: The action list.
        """
        return self._action_list

    @actions_list.setter
    def actions_list(self, value):
        """Set the action list.

        Args:
            value (list[str]): The action list to set.
        """
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            raise ValueError("action_list must be a list of strings")
        self._action_list = value

    @property
    def description(self):
        """Retrieve the description.

        Returns:
            str: The description.
        """
        return self._description

    @description.setter
    def description(self, value):
        """Set the description.

        Args:
            value (str): The description to set.
        """
        if not isinstance(value, str):
            raise ValueError("description must be a string")
        self._description = value

    @property
    def full_model_name(self):
        """Retrieve the full model name the permission is for."""
        return self.content_type_utils.full_model_name

    @full_model_name.setter
    def full_model_name(self, value):
        """Set the full model name.

        Args:
            value (str): The full model name to set. Must be in the format 'app_label.model_name'.

        Raises:
            ValueError: If the value is not in the format 'app_label.model_name'.
        """
        self.content_type_utils.full_model_name = value

    @property
    def name(self):
        """Retrieve the name.

        Returns:
            str: The name.
        """
        return self._name

    @name.setter
    def name(self, value):
        """Set the name.

        Args:
            value (str): The name to set.
        """
        if not isinstance(value, str):
            raise ValueError("name must be a string")
        self._name = value

    def create_permission(self, permission_data_object: PermissionDataObject = None):
        """Create a permission with the given name, actions and description and assign it to the model_name.

        Args:
            permission_data_object (PermissionDataObject): The permission data object to create the permission with.

        Raises:
            ValueError: If the model_name is not in the format 'app_label.model_name'.
        """
        if permission_data_object is not None:
            self.name = permission_data_object.name
            self.actions_list = permission_data_object.actions_list
            self.description = permission_data_object.description
            self.full_model_name = permission_data_object.full_model_name
            self._create_permission()

    def _create_permission(self):
        # Get the model class name we need assing the content type to the permission
        ct = ContentTypeUtils(full_model_name=self.full_model_name)
        permission_content_type_model = ct.content_type_for_model

        # Get the ObjectPermission model
        cto = contenttype.ContentTypeUtils(full_model_name="users.objectpermission")
        ObjectPermission = cto.content_type_for_model  # pylint: disable=invalid-name
        permission, created = ObjectPermission.objects.get_or_create(  # type: ignore
            name=self.name,
            actions=self.actions_list,
            description=self.description,
        )
        if created:
            # Add the content type to the permission
            permission.save()
        if permission.object_types.count() == 0:  # type: ignore
            permission.object_types.set([permission_content_type_model])  # type: ignore
            permission.save()
