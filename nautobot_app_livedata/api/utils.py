"""Utility functions for the Livedata API."""

# filepath: livedata/api/utils.py

import logging
from typing import List

from nautobot.dcim.models import Device, Interface, VirtualChassis

logger = logging.getLogger(__name__)

# Check that napalm is installed
try:
    import napalm  # pylint: disable=unused-import # noqa: F401
except ImportError:
    raise ImportError(  # pylint: disable=raise-missing-from
        "ERROR NAPALM is not installed. Please see the documentation for instructions."
    )

# Check that celery worker is installed
try:
    from nautobot.core.celery import nautobot_task  # pylint: disable=unused-import,ungrouped-imports # noqa: F401

    CELERY_WORKER = True
except ImportError as err:
    print("ERROR in livedata_device_worker: Celery is not Installed.")
    logger.error(  # pylint: disable=raise-missing-from  # type: ignore
        "ERROR in livedata_device_worker: Celery is not Installed."
    )
    raise ImportError from err


class GetManagedDevice:
    """Get the managed device for the given object type and ID.

    For more information on implementing jobs, refer to the Nautobot job documentation:
    https://docs.nautobot.com/projects/core/en/stable/development/jobs/
    """

    def __init__(self, object_type: str, pk: str):
        """Initialize the GetManagedDevice class.

        Args:
            object_type (str): The object type to get the managed device for.
            pk (str): The primary key of the object.

        Properties:
            device (Device): The device that was given as input.
            interface (Interface): The interface that was given as input.
            virtual_chassis (VirtualChassis): The virtual chassis that was
                given as input.
            managed_device (Device): The managed device.

        Raises:
            ValueError: If the object type is not valid.
            ValueError: If the device is not found.
            ValueError: If the device does not have a primary IP address.
            ValueError: If the device state is not active
        """
        self._object_type = object_type
        self._pk = pk
        self._device = None
        self._interface = None
        self._virtual_chassis = None
        self._managed_device = None
        self.get_managed_device()

    def get_managed_device(self):
        """Get the managed device for the given object type and ID."""
        self._get_associated_device()

        # Check if device is None
        if self._device is None:
            raise ValueError("Device not found")

        # Set the managed device to the device
        self._managed_device = self._device

        # Check if the desvice has a primary IP address and status is active
        if not self._managed_device.primary_ip:
            # Try to loop over all devices in the virtual chassis and check if any of them has a primary IP address
            if self._managed_device.virtual_chassis:
                for member in self._managed_device.virtual_chassis.members.all():
                    if member.primary_ip:
                        self._managed_device = member
                        break
            else:
                raise ValueError("Device does not have a primary IP address")
        # Check if the device state is active
        if str(self._managed_device.status) != "Active":
            raise ValueError("Device is not active")

    def _get_associated_device(self):
        if self._object_type == "dcim.interface":
            try:
                self._interface = Interface.objects.get(pk=self._pk)
                self._device = self._interface.device
            except Interface.DoesNotExist as err:
                raise ValueError("Interface does not exist") from err
        elif self._object_type == "dcim.device":
            try:
                self._device = Device.objects.get(pk=self._pk)
            except Device.DoesNotExist as err:
                raise ValueError("Device does not exist") from err
        elif self._object_type == "dcim.virtualchassis":
            try:
                self._virtual_chassis = VirtualChassis.objects.get(pk=self._pk)
                if self._virtual_chassis.master:
                    self._device = self._virtual_chassis.master
                else:
                    self._device = self._virtual_chassis.members.first()  # type: ignore
            except VirtualChassis.DoesNotExist as err:
                raise ValueError("VirtualChassis does not exist") from err
        else:
            raise ValueError("Invalid object type")

    def to_dict(self):
        """Cast the GetManagedDevice object to a dictionary."""
        return {
            "object_type": self._object_type,
            "pk": self._pk,
            "device": self._device.pk if self._device else None,
            "interface": self._interface.pk if self._interface else None,
            "virtual_chassis": self._virtual_chassis.pk if self._virtual_chassis else None,
            "managed_device": self._managed_device.pk if self._managed_device else None,
        }

    @property
    def device(self):
        """Return the device that was given as input."""
        return self._device

    @property
    def interface(self):
        """Return the interface that was given as input."""
        return self._interface

    @property
    def virtual_chassis(self):
        """Return the virtual chassis that was given as input."""
        return self._virtual_chassis

    @property
    def managed_device(self):
        """Return the managed device.

        Device that has a primary IP address and is in active state.

        Returns:
            Device (dcim.Device): The managed device.
        """
        return self._managed_device


def get_livedata_commands_for_interface(interface: Interface) -> List[str]:
    """Get the commands to be executed for Livedata on the given interface.

    Args:
        interface (Interface): The interface to get the commands for.

    Returns:
        out (List[str]): The commands to be executed for Livedata on the given interface.

    Raises:
        ValueError: If the device.platform does not have a platform set.
        ValueError: If the device.platform does not have a network driver set.
        ValueError: If the device.platform does not have the custom field 'livedata_interface_commands' set.
    """
    # Check if the device has a platform that supports the commands
    if interface.device.platform is None:  # type: ignore
        raise ValueError(
            f"`E3002:` Device {interface.device.name} does not support "  # type: ignore
            "the commands required for Livedata because the platform is not set"
        )
    if not interface.device.platform.network_driver:  # type: ignore
        raise ValueError(
            f"`E3002:` Device {interface.device.name} does not support "  # type: ignore
            "the commands required for Livedata because the network driver is not set"
        )
    if "livedata_interface_commands" not in interface.device.platform.custom_field_data.keys():  # type: ignore
        raise ValueError(
            f"`E3002:` Device {interface.device.name} does not support the commands "  # type: ignore
            "required for Livedata because the custom field 'livedata_interface_commands' is not set"
        )
    interface_commands = interface.device.platform.custom_field_data[  # type: ignore
        "livedata_interface_commands"
    ].splitlines()
    # Return the commands to be executed
    return interface_commands
