"""Params for testing."""

# filepath: nautobot_app_livedata/tests/conftest.py

# https://docs.djangoproject.com/en/4.2/howto/initial-data/
# https://github.com/nautobot/nautobot/blob/develop/nautobot/ipam/tests/test_api.py#L1236

import os

from django.contrib.auth import get_user_model
from nautobot.core.settings_funcs import is_truthy
from nautobot.dcim.models import Device, VirtualChassis
from nautobot.extras.models import Status
from nautobot.ipam.models import IPAddress, IPAddressToInterface
from nautobot.users.models import ObjectPermission

User = get_user_model()

# Set to True to enable remote debugging tests with VScode
remote_test_debug_enable = is_truthy(os.getenv("REMOTE_TEST_DEBUG_ENABLE", "False"))  # pylint: disable=invalid-name
remote_test_debug_port = int(os.getenv("REMOTE_TEST_DEBUG_PORT", "6897"))  # pylint: disable=invalid-name


def create_db_data():  # pylint: disable=too-many-locals
    """Creates data for testing.

    The returned device_list contains the following devices:

    | index | primary_ip4 | vc member | vc master | vc name             | Status |
    |-------|-------------|-----------|-----------|---------------------|--------|
    | 0     | yes         | no        | no        |                     | Active |
    |-------|-------------|-----------|-----------|---------------------|--------|
    | 1     | no          | no        | no        |                     | Active |
    |-------|-------------|-----------|-----------|---------------------|--------|
    | 2     | yes         | yes       | yes       | vc-ip-master        | Active |
    | 3     | no          | yes       | no        | vc-ip-master        | Planned|
    | 4     | no          | yes       | no        | vc-ip-master        | Active |
    |-------|-------------|-----------|-----------|---------------------|--------|
    | 5     | yes         | yes       | no        | vc-ip-no_master     | Active |
    | 6     | no          | yes       | no        | vc-ip-no_master     | Active |
    |-------|-------------|-----------|-----------|---------------------|--------|
    | 7     | no          | yes       | no        | vc-no_ip-no_master  | Active |

    Returns:
        list[dcim.Device]: The list of devices prepared for testing.
    """
    status_active = Status.objects.get(name="Active")
    status_planned = Status.objects.get(name="Planned")

    device_listtmp = []
    device_list = []
    for dev in Device.objects.all():
        if not dev.interfaces.exists() or dev.primary_ip4:  # type: ignore
            # skip devices without interfaces or with a primary IP address
            continue
        device_listtmp.append(dev)
    ip_addresses = IPAddress.objects.filter(ip_version=4)
    cnt = -1
    for dev in device_listtmp[:8]:
        cnt += 1
        dev.name = f"device-{cnt}"
        interface = dev.interfaces.first()
        if cnt in [0, 2, 5]:
            for ip_v4 in ip_addresses:
                ip_interfaces = IPAddressToInterface.objects.filter(ip_address=ip_v4)
                if ip_interfaces.exists():
                    # Skip if the IP address is already assigned to an interface
                    continue
                ip_address_to_interface = IPAddressToInterface.objects.create(
                    interface=interface,
                    ip_address=ip_v4,
                    is_primary=True,
                )
                ip_address_to_interface.save()
                interface.ip_address_assignments.add(ip_address_to_interface)
                interface.save()
                dev.primary_ip4 = ip_v4
                break
        if cnt == 3:
            dev.status = status_planned
        else:
            dev.status = status_active
        dev.save()
        device_list.append(dev)

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

    # Print out the devices in device_list
    print(f"\nThere are {len(device_list)} devices in the Device list: ")
    for dev in device_list:
        print(
            f"  {dev.name}:  IP = {dev.primary_ip4 if dev.primary_ip4 else '---'}",
            ", Virt-Cassis =",
            dev.virtual_chassis,
            ", Status =",
            dev.status,
        )
        for interface in dev.interfaces.all():
            print(f"    - Interface {interface.name}")
            for ip in interface.ip_addresses.all():
                print(f"              - IP: {ip.address}")
        print(" ")
    return device_list


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
    permission, created = ObjectPermission.objects.get_or_create(
        name=name,
        actions=actions_list,
        description=description,
    )
    if created:
        # Add the content type to the permission
        permission.save()
    if permission.object_types.count() == 0:  # type: ignore
        permission.object_types.set([model])  # type: ignore
        permission.save()
    return permission


def wait_for_debugger_connection():
    """Wait for the debugger to connect.

    This function is used to wait for the debugger to connect to the test.
    It listens on port 6897 and waits for the debugger to connect.
    If called multiple times it will only listen once.

    Pass the environment variable TEST_REMOTE_DEBUG_ENABLE=True to enable
    remote debugging.

    E.g.: TEST_REMOTE_DEBUG_ENABLE=True nautobot-server test --keepdb nautobot_app_livedata
    """
    global remote_test_debug_port  # pylint: disable=global-statement
    if not remote_test_debug_enable:
        return
    import debugpy  # pylint: disable=import-outside-toplevel

    if not hasattr(wait_for_debugger_connection, "_connected"):
        print(f"\nWaiting for debugger to connect on port {remote_test_debug_port}...")
        debugpy.listen(("0.0.0.0", remote_test_debug_port))
        debugpy.wait_for_client()
        wait_for_debugger_connection._connected = True
