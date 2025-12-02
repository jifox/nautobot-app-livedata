"""Params for testing."""

# filepath: nautobot_app_livedata/tests/conftest.py

# https://docs.djangoproject.com/en/4.2/howto/initial-data/
# https://github.com/nautobot/nautobot/blob/develop/nautobot/ipam/tests/test_api.py#L1236

import os
from pathlib import Path
import sys
from uuid import uuid4

_AUTOGEN_IP_PREFIX = "198.51.100"
_AUTOGEN_IP_MASK = 32
_AUTOGEN_IP_DESCRIPTION = "Autogen Livedata IP"
_AUTOGEN_PREFIX_NETWORK = "198.51.100.0"
_AUTOGEN_PREFIX_LENGTH = 24
_AUTOGEN_PREFIX_CIDR = f"{_AUTOGEN_PREFIX_NETWORK}/{_AUTOGEN_PREFIX_LENGTH}"
_AUTOGEN_NAMESPACE_NAME = "Autogen Namespace"
_AUTOGEN_PLATFORM_COMMANDS = "command1\ncommand2"
_PLATFORM_ASSIGNMENT_TARGET = 6

# Ensure tests can import the app package and repository root when run in CI/container
# Prepend the app package directory (nautobot_app_livedata) so imports like
# `import nautobot_app_livedata` succeed when pytest runs from the tests dir.
_HERE = Path(__file__).resolve()
_APP_PKG_DIR = _HERE.parents[1]
if str(_APP_PKG_DIR) not in sys.path:
    sys.path.insert(0, str(_APP_PKG_DIR))

# Also add repository root (where `pyproject.toml` lives) to sys.path so test
# helpers can import project-level modules when executed inside containers.
_ROOT = _HERE
for _ in range(6):
    if (_ROOT / "pyproject.toml").exists():
        if str(_ROOT) not in sys.path:
            sys.path.insert(0, str(_ROOT))
        break
    _ROOT = _ROOT.parent

# Imports follow path manipulation; mark with E402 to satisfy ruff/flake8 checks
from django.contrib.auth import get_user_model  # noqa: E402
from nautobot.core.choices import ColorChoices  # noqa: E402
from nautobot.core.models import ContentType  # noqa: E402
from nautobot.core.settings_funcs import is_truthy  # noqa: E402
from nautobot.dcim.models import (  # noqa: E402
    Device,
    DeviceType,
    Interface,
    Location,
    LocationType,
    Manufacturer,
    Platform,
    VirtualChassis,
)
from nautobot.extras.models import Job, Role, Status  # noqa: E402
from nautobot.ipam.models import IPAddress, IPAddressToInterface, Namespace, Prefix  # noqa: E402
from nautobot.users.models import ObjectPermission  # noqa: E402

from nautobot_app_livedata.utilities.permission import create_permission  # noqa: E402

User = get_user_model()

# Set to True to enable remote debugging tests with VScode
remote_test_debug_enable = is_truthy(os.getenv("REMOTE_TEST_DEBUG_ENABLE", "False"))  # pylint: disable=invalid-name
remote_test_debug_port = int(os.getenv("REMOTE_TEST_DEBUG_PORT", "6897"))  # pylint: disable=invalid-name


def create_db_data():  # pylint: disable=too-many-locals
    """Creates data for testing.

    The returned device_list contains the following devices:

    | index | primary_ip4 | vc member | vc master | vc name             | Status | Platform | Driver    |
    |-------|-------------|-----------|-----------|---------------------|--------|----------|-----------|
    | 0     | yes         | no        | no        |                     | Active | yes      | cisco_ios |
    |-------|-------------|-----------|-----------|---------------------|--------|----------|-----------|
    | 1     | no          | no        | no        |                     | Active | yes      | cisco_ios |
    |-------|-------------|-----------|-----------|---------------------|--------|----------|-----------|
    | 2     | yes         | yes       | yes       | vc-ip-master        | Active | yes      | cisco_ios |
    | 3     | no          | yes       | no        | vc-ip-master        | Planned| yes      | cisco_ios |
    | 4     | no          | yes       | no        | vc-ip-master        | Active | yes      | cisco_ios |
    |-------|-------------|-----------|-----------|---------------------|--------|----------|-----------|
    | 5     | yes         | yes       | no        | vc-ip-no_master     | Active | yes      |           |
    | 6     | no          | yes       | no        | vc-ip-no_master     | Active | no       |           |
    |-------|-------------|-----------|-----------|---------------------|--------|----------|-----------|
    | 7     | no          | yes       | no        | vc-no_ip-no_master  | Active | no       |           |

    Returns:
        list[dcim.Device]: The list of devices prepared for testing.
    """
    wait_for_debugger_connection()

    device_listtmp = []
    device_list = []
    collect_valid_device_entries(device_listtmp)
    assign_device_ips_and_status(device_listtmp, device_list)
    assign_platform(device_list)
    db_objects = {
        "ContentType": ContentType,
        "ObjectPermission": ObjectPermission,
        "Device": Device,
        "Job": Job,
        "Platform": Platform,
    }
    content_typs = {
        "Device": ContentType.objects.get_for_model(Device),  # type: ignore
        "Job": ContentType.objects.get_for_model(Job),  # type: ignore
        "Platform": ContentType.objects.get_for_model(Platform),  # type: ignore
    }
    create_permission(
        db_objects=db_objects,
        name="livedata.interact_with_devices",
        actions_list=["can_interact"],
        description="Interact with devices without permission to change device configurations.",
        content_type=content_typs["Device"],
    )
    create_permission(
        db_objects=db_objects,
        name="extras.run_job",
        actions_list=["run"],
        description="Run jobs",
        content_type=content_typs["Job"],
    )

    # | index | primary_ip4 | vc member | vc master | vc name             | Status |
    # |-------|-------------|-----------|-----------|---------------------|--------|
    # | 2     | yes         | yes       | yes       | vc-ip-master        | Active |
    # | 3     | no          | yes       | no        | vc-ip-master        | Planned|
    # | 4     | no          | yes       | no        | vc-ip-master        | Active |
    try:
        vc = VirtualChassis.objects.get(name="vc-ip-master")
    except VirtualChassis.DoesNotExist:
        vc = VirtualChassis.objects.create(name="vc-ip-master")
        vc.save()
    vc.members.add(device_list[2])  # type: ignore
    vc.members.add(device_list[3])  # type: ignore
    vc.members.add(device_list[4])  # type: ignore
    vc.save()
    vc.master = device_list[2]
    vc.save()

    # | index | primary_ip4 | vc member | vc master | vc name             | Status |
    # |-------|-------------|-----------|-----------|---------------------|--------|
    # | 5     | yes         | yes       | no        | vc-ip-no_master     | Active |
    # | 6     | no          | yes       | no        | vc-ip-no_master     | Active |
    try:
        vc = VirtualChassis.objects.get(name="vc-ip-no_master")
    except VirtualChassis.DoesNotExist:
        vc = VirtualChassis.objects.create(name="vc-ip-no_master")
        vc.save()
    vc.members.add(device_list[5])  # type: ignore
    vc.members.add(device_list[6])  # type: ignore
    vc.save()

    # Add a virtualchassis and assigne the devices 6, and 7 to it
    # 6 = no primary_ip4, 7 = no primary_ip4
    # | index | primary_ip4 | vc member | vc master | vc name             | Status |
    # |-------|-------------|-----------|-----------|---------------------|--------|
    # | 7     | no          | yes       | no        | vc-no_ip-no_master  | Active |
    try:
        vc = VirtualChassis.objects.get(name="vc-no_ip-no_master")
    except VirtualChassis.DoesNotExist:
        vc = VirtualChassis.objects.create(name="vc-no_ip-no_master")
        vc.save()
    vc.members.add(device_list[7])  # type: ignore
    vc.save()

    # # Print out the devices in device_list
    # print(f"\nThere are {len(device_list)} devices in the Device list: ")
    # for dev in device_list:
    #     print(
    #         f"  {dev.name}:  IP = {dev.primary_ip4 if dev.primary_ip4 else '---'}",
    #         ", Virt-Cassis =",
    #         dev.virtual_chassis,
    #         ", Status =",
    #         dev.status,
    #     )
    #     for interface in dev.interfaces.all():
    #         print(f"    - Interface {interface.name}")
    #         for ip in interface.ip_addresses.all():
    #             print(f"              - IP: {ip.address}")
    #     print(" ")
    return device_list


def assign_device_ips_and_status(device_listtmp, device_list):
    """Assign IP addresses and device status values for testing.

    Args:
        device_listtmp (list[dcim.Device]): Devices collected from the database.
        device_list (list[dcim.Device]): Destination list populated for the tests.
    """
    status_active = _get_or_create_status("Active", ColorChoices.COLOR_GREEN)
    status_planned = _get_or_create_status("Planned", ColorChoices.COLOR_AMBER)
    _ensure_status_supports_model(status_active, Device)
    _ensure_status_supports_model(status_planned, Device)
    interface_status = status_active
    _ensure_status_supports_model(interface_status, Interface)
    cnt = -1
    for dev in device_listtmp[:8]:
        cnt += 1
        dev.name = f"device-{cnt}"
        interface = dev.interfaces.first()
        if interface is None:
            interface = Interface.objects.create(
                device=dev,
                name="GigabitEthernet0/0/0",
                status=interface_status,
            )
        elif interface.status_id is None:
            interface.status = interface_status
            interface.save()
        if cnt in [0, 2, 5]:
            ip_v4 = _get_or_create_available_ipv4(status_active)
            _assign_ip_to_interface(interface, ip_v4)
            dev.primary_ip4 = ip_v4
        if cnt == 3:
            dev.status = status_planned
        else:
            dev.status = status_active
        dev.save()
        device_list.append(dev)


def collect_valid_device_entries(device_listtmp, minimum_required=8):
    """Collect or create devices with interfaces and without a primary IP address.

    Args:
        device_listtmp (list[dcim.Device]): The list of devices to extend.
        minimum_required (int): Minimum number of devices needed for the tests.
    """
    for dev in Device.objects.all():
        if not dev.interfaces.exists() or dev.primary_ip4:  # type: ignore
            continue
        device_listtmp.append(dev)
    if len(device_listtmp) < minimum_required:
        _create_minimum_viable_devices(minimum_required - len(device_listtmp), device_listtmp)


def _create_minimum_viable_devices(count, device_listtmp):
    """Create deterministic devices so the fixture has enough data to operate.

    Args:
        count (int): Number of devices to create.
        device_listtmp (list[dcim.Device]): Destination list to extend.
    """
    status_active = _get_or_create_status("Active", ColorChoices.COLOR_GREEN)
    _ensure_status_supports_model(status_active, Device)
    device_role = _get_or_create_device_role()
    device_location = _get_or_create_device_location(status_active)
    manufacturer, _ = Manufacturer.objects.get_or_create(name="Autogen Manufacturer")
    device_type, _ = DeviceType.objects.get_or_create(
        manufacturer=manufacturer,
        model="Autogen Model",
    )
    _ensure_status_supports_model(status_active, Interface)
    for _ in range(count):
        suffix = uuid4().hex[:8]
        device = Device.objects.create(
            name=f"autogen-device-{suffix}",
            location=device_location,
            role=device_role,
            device_type=device_type,
            status=status_active,
        )
        Interface.objects.create(
            device=device,
            name=f"GigabitEthernet0/{suffix[:2]}/{suffix[2:4]}",
            status=status_active,
        )
        device_listtmp.append(device)


def _get_or_create_available_ipv4(status_active):
    """Return an IPv4 address that is not assigned to any interface.

    Args:
        status_active (Status): Active status used for new IP addresses.

    Returns:
        IPAddress: An available IPv4 address.
    """
    _ensure_status_supports_model(status_active, IPAddress)
    ip_addresses = IPAddress.objects.filter(ip_version=4)
    for ip_v4 in ip_addresses:
        if not IPAddressToInterface.objects.filter(ip_address=ip_v4).exists():
            return ip_v4
    return _create_ipv4_address(status_active)


def _create_ipv4_address(status_active):
    """Create a unique IPv4 address reserved for these tests.

    Args:
        status_active (Status): Active status applied to the created IP.

    Returns:
        IPAddress: Newly created IPv4 address.
    """
    _ensure_autogen_prefix(status_active)
    counter = 1
    while True:
        if counter >= 255:
            counter = 1
        candidate_host = f"{_AUTOGEN_IP_PREFIX}.{counter}"
        if not IPAddress.objects.filter(
            host=candidate_host,
            mask_length=_AUTOGEN_IP_MASK,
        ).exists():
            return IPAddress.objects.create(
                address=f"{candidate_host}/{_AUTOGEN_IP_MASK}",
                status=status_active,
                description=_AUTOGEN_IP_DESCRIPTION,
            )
        counter += 1


def _ensure_autogen_prefix(status_active):
    """Guarantee the synthetic prefix exists so IPs can find a parent."""
    _ensure_status_supports_model(status_active, Prefix)
    namespace = Namespace.objects.filter(name="Global").first()
    if namespace is None:
        namespace, _ = Namespace.objects.get_or_create(name=_AUTOGEN_NAMESPACE_NAME)
    prefix = Prefix.objects.filter(
        namespace=namespace,
        network=_AUTOGEN_PREFIX_NETWORK,
        prefix_length=_AUTOGEN_PREFIX_LENGTH,
    ).first()
    if prefix is None:
        prefix = Prefix.objects.create(
            prefix=_AUTOGEN_PREFIX_CIDR,
            namespace=namespace,
            status=status_active,
        )
    return prefix


def _assign_ip_to_interface(interface, ip_address):
    """Attach an IP address to the provided interface as its primary address.

    Args:
        interface (dcim.Interface): Interface receiving the IP assignment.
        ip_address (IPAddress): IP address to associate with the interface.
    """
    ip_address_to_interface = IPAddressToInterface.objects.create(
        interface=interface,
        ip_address=ip_address,
        is_primary=True,
    )
    ip_address_to_interface.save()
    interface.ip_address_assignments.add(ip_address_to_interface)
    interface.save()


def _get_or_create_device_role():
    """Return a Role instance compatible with Device assignments."""
    device_content_type = ContentType.objects.get_for_model(Device)
    existing_role = Role.objects.filter(content_types=device_content_type).first()
    if existing_role:
        return existing_role
    suffix = uuid4().hex[:8]
    role = Role.objects.create(name=f"Autogen Device Role {suffix}")
    role.content_types.add(device_content_type)
    return role


def _get_or_create_device_location(status_active):
    """Return a Location that can host Device objects."""
    device_content_type = ContentType.objects.get_for_model(Device)
    location_type = LocationType.objects.filter(content_types=device_content_type).first()
    if location_type is None:
        location_type = LocationType.objects.create(name="Autogen Device Location Type")
        location_type.content_types.add(device_content_type)
    location = Location.objects.filter(location_type=location_type).first()
    if location:
        return location
    _ensure_status_supports_model(status_active, Location)
    return Location.objects.create(
        name="Autogen Location",
        location_type=location_type,
        status=status_active,
    )


def assign_platform(device_list):
    """Assign required platform metadata to the first set of devices."""
    if not device_list:
        return
    platforms = _ensure_platform_pool(_PLATFORM_ASSIGNMENT_TARGET)
    for idx in range(min(len(device_list), _PLATFORM_ASSIGNMENT_TARGET)):
        platform = platforms[idx]
        _configure_platform(platform, include_driver=idx < 5)
        device = device_list[idx]
        device.platform = platform
        device.save()


def _ensure_platform_pool(required_count):
    """Return at least ``required_count`` Platform objects, creating them if needed."""
    platforms = list(Platform.objects.order_by("pk"))
    while len(platforms) < required_count:
        suffix = uuid4().hex[:8]
        platforms.append(
            Platform.objects.create(
                name=f"Autogen Platform {suffix}",
            )
        )
    return platforms


def _configure_platform(platform, *, include_driver):
    """Ensure a platform carries the test driver's metadata."""
    platform.cf["livedata_interface_commands"] = _AUTOGEN_PLATFORM_COMMANDS
    platform.network_driver = "cisco_ios" if include_driver else ""
    platform.save()


def add_permission(name, actions_list, description, model):
    """Create a permission with the given name, actions and description and assign it to the model_name.

    Args:
        name (str): The name of the permission.
        actions_list (list): The list of actions the permission can do.
        description (str): The description of the permission.
        model

    Raises:
        ValueError: If the model_name is not in the format 'app_label.model_name'.
    """
    db_objects = {
        "ContentType": ContentType,
        "ObjectPermission": ObjectPermission,
    }
    create_permission(
        db_objects=db_objects,
        name=name,
        actions_list=actions_list,
        description=description,
        full_model_name=model,
    )
    return ObjectPermission.objects.get(name=name)


def wait_for_debugger_connection():
    """Wait for the debugger to connect.

    This function is used to wait for the debugger to connect to the test.
    It listens on port 6897 and waits for the debugger to connect.
    If called multiple times it will only listen once.

    Pass the environment variable TEST_REMOTE_DEBUG_ENABLE=True to enable
    remote debugging.

    E.g.: TEST_REMOTE_DEBUG_ENABLE=True nautobot-server test --keepdb nautobot_app_livedata
    """
    if not remote_test_debug_enable:
        return
    import debugpy  # pylint: disable=import-outside-toplevel

    if not hasattr(wait_for_debugger_connection, "_connected"):
        print(f"\nWaiting for debugger to connect on port {remote_test_debug_port}...")
        debugpy.listen(("0.0.0.0", remote_test_debug_port))
        debugpy.wait_for_client()


def _get_or_create_status(name, color):
    """Return a status object, creating it if needed."""
    status, _ = Status.objects.get_or_create(
        name=name,
        defaults={"color": color},
    )
    return status


def _ensure_status_supports_model(status, model):
    """Attach the provided status to the model's content type when required."""
    content_type = ContentType.objects.get_for_model(model)
    if not status.content_types.filter(pk=content_type.pk).exists():
        status.content_types.add(content_type)
        wait_for_debugger_connection._connected = True  # pylint: disable=protected-access
