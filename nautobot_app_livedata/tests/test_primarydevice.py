"""Unit tests for Get Primary Device."""

from django.contrib.auth import get_user_model
from nautobot.apps.testing import TestCase

from nautobot_app_livedata.utilities.primarydevice import PrimaryDeviceUtils

from .conftest import create_db_data, wait_for_debugger_connection

User = get_user_model()


class PrimaryDeviceTest(TestCase):
    """Test the PrimaryDevice class."""

    @classmethod
    def setUpTestData(cls):
        """Set up data for the test class.

        After initializing `self.device_list[]` contains the following devices:

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
        """
        wait_for_debugger_connection()  # To enable set env REMOTE_TEST_DEBUG_ENABLE=True
        cls.device_list = create_db_data()

    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.primary_device = PrimaryDeviceUtils("dcim.device", self.device_list[0].id)

    def test_to_dict(self):
        """Test to_dict method."""
        primary_device_dict = self.primary_device.to_dict()
        comp = self.device_list[0]
        self.assertEqual(primary_device_dict["object_type"], "dcim.device")
        self.assertEqual(primary_device_dict["pk"], comp.pk)
        self.assertEqual(primary_device_dict["device"], comp.id)
        self.assertEqual(primary_device_dict["interface"], None)
        self.assertEqual(primary_device_dict["virtual_chassis"], None)
        self.assertEqual(primary_device_dict["primary_device"], comp.id)

    def test_interface(self):
        """Test interface property."""
        comp = self.device_list[0]
        interface = comp.interfaces.first()
        primary_device = PrimaryDeviceUtils("dcim.interface", interface.pk)
        self.assertEqual(primary_device.interface, interface)
        self.assertEqual(primary_device.device, comp)
        self.assertEqual(primary_device.primary_device, comp)

    def test_virtual_chassis_with_master(self):
        """Test virtual_chassis property with master device."""
        comp = self.device_list[2]
        primary_device = PrimaryDeviceUtils("dcim.device", comp.pk)
        self.assertEqual(primary_device.device, comp)
        self.assertEqual(primary_device.primary_device, comp)
        self.assertEqual(primary_device.virtual_chassis, None)

    def test_virtual_chassis_with_member(self):
        """Test virtual_chassis property with member device."""
        comp_prim = self.device_list[2]
        comp = self.device_list[4]
        primary_device = PrimaryDeviceUtils("dcim.device", comp.pk)
        self.assertEqual(primary_device.device, comp)
        self.assertEqual(primary_device.primary_device, comp_prim)
        self.assertEqual(primary_device.virtual_chassis, comp.virtual_chassis)

    def test_virtual_chassis_fail_no_ip_member_no_master(self):
        """Test virtual_chassis property with member device and no master."""
        comp = self.device_list[7]
        with self.assertRaises(ValueError):
            _ = PrimaryDeviceUtils("dcim.device", comp.pk).primary_device

    def test_virtual_chassis_fail_member_not_active(self):
        """Test virtual_chassis property with member device and not active."""
        comp = self.device_list[3]
        with self.assertRaises(ValueError):
            _ = PrimaryDeviceUtils("dcim.device", comp.pk).primary_device
