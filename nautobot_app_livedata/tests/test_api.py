"""Unit tests for nautobot_app_livedata."""

from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test import RequestFactory
from django.urls import reverse
from nautobot.apps.testing import TestCase as APITransactionTestCase
from nautobot.dcim.models import Device
from nautobot.users.models import ObjectPermission

from nautobot_app_livedata.api.views import LivedataPrimaryDeviceApiView
from nautobot_app_livedata.utilities.permission import create_permission

from .conftest import create_db_data, wait_for_debugger_connection

User = get_user_model()

# Add the following to your VScode launch.json to enable remote test debugging
# {
#   "name": "Python: Nautobot Test (Remote)",
#   "type": "python",
#   "request": "attach",
#   "connect": {
#     "host": "127.0.0.1",
#     "port": 6897
#   },
#   "pathMappings": [{
#     "localRoot": "${workspaceFolder}",
#     "remoteRoot": "/source"
#   }],
#   "django": true,
#   "justMyCode": true
# },


class LiveDataAPITest(APITransactionTestCase):
    """Test the Livedata API."""

    @classmethod
    def setUpTestData(cls):
        """Set up data for the test class."""
        print("\nRUN setUpTestData")
        wait_for_debugger_connection()  # To enable set env REMOTE_TEST_DEBUG_ENABLE=True
        cls.device_list = create_db_data()

    def setUp(self):
        """Set up data for each test case.

        self.user: User with permission to interact with devices.
        self.forbidden_user: User without permission to interact with devices.
        self.factory: RequestFactory for creating requests.
        """
        super().setUp()
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username="testuser", password="password")
        self.forbidden_user = User.objects.create_user(username="forbidden_user", password="password")

        # Grant the user the dcim.can_interact_device permission using ObjectPermission
        device_ct = ContentType.objects.get_for_model(Device)
        db_objects = {
            "ContentType": ContentType,
            "ObjectPermission": ObjectPermission,
        }
        create_permission(
            db_objects=db_objects,
            name="dcim.can_interact_device",
            actions_list=["can_interact"],
            description="Test permission to interact with devices",
            content_type=device_ct,
        )
        obj_perm = ObjectPermission.objects.get(name="dcim.can_interact_device")
        obj_perm.enabled = True
        obj_perm.users.add(self.user)
        obj_perm.validated_save()
        # Clear cached permissions
        if hasattr(self.user, "_perm_cache"):
            delattr(self.user, "_perm_cache")
        if hasattr(self.user, "_user_perm_cache"):
            delattr(self.user, "_user_perm_cache")
        self.client.force_authenticate(user=self.user)  # type: ignore

    def test_self_user_has_permission_can_interact(self):
        """Test that the user has the permission to interact with devices."""
        self.user.is_superuser = False
        self.user.save()
        self.assertTrue(
            self.user.has_perm("dcim.can_interact_device", self.device_list[0]),  # type: ignore
            "User should have permission to interact with devices.",
        )

    def test_permission_denied(self):
        """Test that a user without permission is denied access."""
        device = self.device_list[0]
        interface = device.interfaces.first()
        url = reverse(
            "plugins-api:nautobot_app_livedata-api:livedata-managed-device-api",
            kwargs={
                "pk": interface.id,  # type: ignore
                "object_type": "dcim.interface",
            },
        )  # type: ignore
        request = self.factory.get(url)
        request.user = self.forbidden_user
        self.client.logout()
        response = LivedataPrimaryDeviceApiView.as_view()(request)
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN, "Should return 403 Forbidden.")

    def test_device_with_primary_ip(self):
        """Test that the device with the primary_ip is returned."""
        device = self.device_list[0]
        interface = device.interfaces.first()
        url = reverse(
            "plugins-api:nautobot_app_livedata-api:livedata-managed-device-api",
            kwargs={
                "pk": interface.id,  # type: ignore
                "object_type": "dcim.interface",
            },
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, HTTPStatus.OK, "Should return 200 OK.")
        response_data = response.json()
        self.assertIn("primary_device", response_data, "Response should contain primary_device")

    def test_primary_device_from_interface_on_device_with_primary_ip(self):
        """Test that the primary device from interface on device with primary_ip is returned."""
        print("\nRUN test_primary_device_from_interface_on_device_with_primary_ip")
        device = self.device_list[0]
        interface = device.interfaces.first()
        url = reverse(
            "plugins-api:nautobot_app_livedata-api:livedata-managed-device-api",
            kwargs={
                "pk": interface.id,  # type: ignore
                "object_type": "dcim.interface",
            },
        )
        response = self.client.get(url + "?depth=1&exclude_m2m=false")
        self.assertEqual(response.status_code, HTTPStatus.OK, "Should return 200 OK.")
        self.assertIn("primary_device", response.json(), "Response should contain primary_device")

    def test_primary_device_from_interface_on_device_without_primary_ip(self):
        """Test that the primary device from interface on device without primary_ip is handled."""
        device = self.device_list[1]
        interface = device.interfaces.first()
        url = reverse(
            "plugins-api:nautobot_app_livedata-api:livedata-managed-device-api",
            kwargs={
                "pk": interface.id,  # type: ignore
                "object_type": "dcim.interface",
            },
        )
        response = self.client.get(url)
        # Should either return 200 with error message or 400 if device has no primary IP
        self.assertIn(
            response.status_code, [HTTPStatus.OK, HTTPStatus.BAD_REQUEST], "Should return 200 OK or 400 Bad Request."
        )
