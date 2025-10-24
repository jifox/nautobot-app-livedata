"""Utilities for getting the primary device for a given object."""

from typing import Any, List, Optional

from .contenttype import ContentTypeUtils


class PrimaryDeviceUtils:
    """Get the primary device for the given object type and ID.

    For more information on implementing jobs, refer to the Nautobot job documentation:
    https://docs.nautobot.com/projects/core/en/stable/development/jobs/
    """

    def __init__(self, object_type: str, pk: str):
        """Initialize the PrimaryDeviceUtils class.

        Args:
            object_type (str): The object type to get the primary device for.
            pk (str): The primary key of the object.

        Properties:
            device (Device): The device that was given as input.
            interface (Interface): The interface that was given as input.
            virtual_chassis (VirtualChassis): The virtual chassis that was
                given as input.
            primary_device (Device): The primary device.

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
        self._primary_device = None
        self._get_primary_device()

    def to_dict(self) -> dict[str, Any]:
        """Cast the PrimaryDeviceUtils object to a dictionary.

        Returns:
            dict: Dictionary representation of the PrimaryDeviceUtils object containing
                object_type, pk, device, interface, virtual_chassis, and primary_device IDs.
        """
        return {
            "object_type": self._object_type,
            "pk": self._pk,
            "device": self._device.id if self._device else None,
            "interface": self._interface.id if self._interface else None,
            "virtual_chassis": self._virtual_chassis.id if self._virtual_chassis else None,
            "primary_device": self._primary_device.id if self._primary_device else None,
        }

    def _get_associated_device(self) -> None:
        """Get the associated device for the given object type and ID.

        This method retrieves the device based on the object type (interface, device, or virtual chassis).
        For interfaces, it gets the parent device. For devices, it validates the status is Active.
        For virtual chassis, it gets the master or first member device.

        Raises:
            ValueError: If the object type is invalid.
            ValueError: If the interface/device/virtual chassis does not exist.
            ValueError: If the device status is not Active.
        """
        Interface = ContentTypeUtils("dcim.interface").model  # pylint: disable=invalid-name
        Device = ContentTypeUtils("dcim.device").model  # pylint: disable=invalid-name
        if self._object_type == "dcim.interface":
            try:
                self._interface = Interface.objects.get(pk=self._pk)
                self._device = self._interface.device  # type: ignore
            except Interface.DoesNotExist as err:
                raise ValueError("Interface does not exist") from err
        elif self._object_type == "dcim.device":
            try:
                self._device = Device.objects.get(pk=self._pk)
                if str(self._device.status) != "Active":  # type: ignore
                    raise ValueError(
                        (
                            f"Device '{self._device.name}' "  # type: ignore
                            f"status is '{self._device.status}' and not 'Active'"  # type: ignore
                        )
                    )
            except Device.DoesNotExist as err:
                raise ValueError("Device does not exist") from err
        elif self._object_type == "dcim.virtualchassis":
            from nautobot.dcim.models import VirtualChassis  # pylint: disable=import-outside-toplevel

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

    def _get_primary_device(self) -> None:
        """Get the primary device for the given object type and ID.

        This method determines the primary device by first getting the associated device,
        then checking for a primary IP address. If the device doesn't have a primary IP,
        it searches through virtual chassis members for one that does.

        Raises:
            ValueError: If the device is not found.
            ValueError: If no device with a primary IP address is found.
            ValueError: If the device status is not Active.
        """
        self._get_associated_device()

        # Check if device is None
        if self._device is None:
            raise ValueError("Device not found")

        # Set the primary device to the device
        self._primary_device = self._device

        # Check if the device has a primary IP address and status is active
        if not self._primary_device.primary_ip:  # type: ignore
            # Try to loop over all devices in the virtual chassis and check if any of them has a primary IP address
            if self._primary_device.virtual_chassis:  # type: ignore
                self._virtual_chassis = self._primary_device.virtual_chassis  # type: ignore
                for member in self._primary_device.virtual_chassis.members.all():  # type: ignore
                    if member.primary_ip:
                        self._primary_device = member
                        break
                    raise ValueError("Device does not have a primary IP address")
            else:
                raise ValueError("Device does not have a primary IP address")
        # Check if the device state is active
        if str(self._primary_device.status) != "Active":  # type: ignore
            raise ValueError("Device status is not 'Active'")

    @property
    def device(self) -> Optional[Any]:
        """Return the device that was given as input.

        Returns:
            Device: The device object from the initial input, or None if input was not a device.
        """
        return self._device

    @property
    def interface(self) -> Optional[Any]:
        """Return the interface that was given as input.

        Returns:
            Interface: The interface object from the initial input, or None if input was not an interface.
        """
        return self._interface

    @property
    def primary_device(self) -> Optional[Any]:
        """Return the primary device.

        Device that has a primary IP address and is in active state.

        Returns:
            Device (dcim.Device): The primary device.
        """
        if self._primary_device is None:
            self._get_primary_device()
        return self._primary_device

    @property
    def virtual_chassis(self) -> Optional[Any]:
        """Return the virtual chassis that was given as input.

        Returns:
            VirtualChassis: The virtual chassis object from the initial input, or None if input
                was not a virtual chassis or the device is not part of one.
        """
        return self._virtual_chassis


def get_livedata_commands(device: Any, custom_field_key: str) -> List[str]:
    """Get the commands to be executed for Livedata on the given device.

    Args:
        device (dcim.Device): The device to get the commands for.
        custom_field_key (str): The custom field key to get the commands from.

    Returns:
        out (List[str]): The commands to be executed for Livedata on the given device.

    Raises:
        ValueError: If the device.platform does not have a platform set.
        ValueError: If the device.platform does not have a network driver set.
        ValueError: If the device.platform does not have the custom field set.
    """
    # Check if the device has a platform that supports the commands
    if device.platform is None:
        raise ValueError(
            f"`E3002:` Device {device.name} does not support "
            "the commands required for Livedata because the platform is not set"
        )
    if not device.platform.network_driver:
        raise ValueError(
            f"`E3002:` Device {device.name} does not support "
            "the commands required for Livedata because the network driver is not set"
        )
    if custom_field_key not in device.platform.custom_field_data.keys():
        raise ValueError(
            f"`E3002:` Device {device.name} does not support the commands "
            f"required for Livedata because the custom field  {custom_field_key} doesn't exist."
        )
    commands = device.platform.custom_field_data[custom_field_key].splitlines()
    # trim trailing whitespace
    commands = [command.rstrip() for command in commands]
    # Return the commands to be executed
    return commands


def get_livedata_commands_for_device(device: Any) -> List[str]:
    """Get the commands to be executed for Livedata on the given device.

    Args:
        device (dcim.Device): The device to get the commands for.

    Returns:
        out (List[str]): The commands to be executed for Livedata on the given device.
    """
    return get_livedata_commands(device, "livedata_device_commands")


def get_livedata_commands_for_interface(interface: Any) -> List[str]:
    """Get the commands to be executed for Livedata on the given interface.

    Args:
        interface (dcim.Interface): The interface to get the commands for.

    Returns:
        out (List[str]): The commands to be executed for Livedata on the given interface.
    """
    return get_livedata_commands(interface.device, "livedata_interface_commands")
