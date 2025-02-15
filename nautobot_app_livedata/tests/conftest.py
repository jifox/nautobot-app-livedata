"""Params for testing."""

# filepath: nautobot_app_livedata/tests/conftest.py

# https://docs.djangoproject.com/en/4.2/howto/initial-data/
# https://github.com/nautobot/nautobot/blob/develop/nautobot/ipam/tests/test_api.py#L1236

import os

from django.contrib.auth import get_user_model
from nautobot.core.models import ContentType
from nautobot.core.settings_funcs import is_truthy
from nautobot.dcim.models import Device, Platform, VirtualChassis
from nautobot.extras.models import Job, Status
from nautobot.ipam.models import IPAddress, IPAddressToInterface
from nautobot.users.models import ObjectPermission

from nautobot_app_livedata.utilities.permission import create_permission

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
    """Assign IP addresses to devices and set the status.

    Args:
        status_active (Status): The active status.
        status_planned (Status): The planned status.
        device_listtmp (list[dcim.Device]): The list of devices to assign IP addresses and status.
        device_list (list[dcim.Device]): The list of devices to add the devices to.
    """
    status_active = Status.objects.get(name="Active")
    status_planned = Status.objects.get(name="Planned")
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


def collect_valid_device_entries(device_listtmp):
    """Collect devices with interfaces and without a primary IP address.

    Args:
        device_listtmp (list[dcim.Device]): The list of devices to add the devices to.
    """
    for dev in Device.objects.all():
        if not dev.interfaces.exists() or dev.primary_ip4:  # type: ignore
            # skip devices without interfaces or with a primary IP address
            continue
        device_listtmp.append(dev)


def assign_platform(device_list):
    """Assign a platform to the devices.

    Args:
        device_list (list[dcim.Device]): The list of devices to assign the platform to.
    """
    cnt = -1
    for platform in Platform.objects.all():
        cnt += 1
        if cnt < 5:
            platform.custom_field_data["livedata_interface_commands"] = "command1\ncommand2"
            platform.network_driver = "cisco_ios"
            platform.save()
            device_list[cnt].platform = platform
            device_list[cnt].save()
        elif cnt == 5:
            platform.custom_field_data["livedata_interface_commands"] = "command1\ncommand2"
            platform.network_driver = ""
            platform.save()
            device_list[cnt].platform = platform
            device_list[cnt].save()
        elif cnt == 6:
            break
        elif cnt == 7:
            break


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
        wait_for_debugger_connection._connected = True  # pylint: disable=protected-access
