"""Unit tests for nautobot_app_livedata."""

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.test import RequestFactory
from django.urls import reverse
from nautobot.apps.testing import TestCase as APITransactionTestCase

from nautobot_app_livedata.api.views import LivedataPrimaryDeviceApiView
from nautobot_app_livedata.utilities.contenttype import ContentTypeUtils

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
        print("\nRUN setUp")
        super().setUp()
        self.factory = RequestFactory()
        self.user = User.objects.create(username="test_user", password="password")
        self.forbidden_user = User.objects.create(username="forbidden_user", password="password")

        ObjectPermission = ContentTypeUtils("users.objectpermission").model  # pylint: disable=invalid-name

        permission = ObjectPermission.objects.get(name="livedata.interact_with_devices")
        self.user.object_permissions.add(permission)  # type: ignore
        self.user.save()
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
        with self.assertRaises(PermissionDenied):
            _ = LivedataPrimaryDeviceApiView.as_view()(request)

    # TODO: Fix the following tests

    # def test_device_with_primary_ip(self):
    #     """Test that the device with the primary_ip is returned."""
    #     device = self.device_list[0]
    #     interface = device.interfaces.first()
    #     url = reverse(
    #         "plugins-api:nautobot_app_livedata-api:livedata-managed-device-api",
    #         kwargs={
    #             "pk": interface.id,  # type: ignore
    #             "object_type": "dcim.interface",
    #         },
    #     )
    #     request = self.factory.get(url)
    #     request.user = self.user
    #     response = LivedataPrimaryDeviceApiView.as_view()(request)
    #     self.assertEqual(response.status_code, status.HTTP_200_OK, "Should return 200 OK.")

    # def test_primary_device_from_interface_on_device_with_primary_ip(self):
    #     """Test that the device with the primary_ip is returned."""
    #     print("\nRUN test_primary_device_from_interface_on_device_with_primary_ip")
    #     device = self.device_list[0]
    #     interface = device.interfaces.first()
    #     url = reverse(
    #         "plugins-api:nautobot_app_livedata-api:livedata-managed-device-api",
    #         kwargs={
    #             "pk": interface.id,  # type: ignore
    #             "object_type": "dcim.interface",
    #         },
    #     )
    #     response = self.client.get(url + "?depth=1&exclude_m2m=false")
    #     self.assertEqual(response.status_code, status.HTTP_200_OK, "Should return 200 OK.")

    # def test_primary_device_from_interface_on_device_without_primary_ip(self):
    #     """Test that the device with the primary_ip is returned."""
    #     device = self.device_list[1]
    #     interface = device.interfaces.first()
    #     url = reverse(
    #         "plugins-api:nautobot_app_livedata-api:livedata-managed-device-api",
    #         kwargs={
    #             "pk": interface.id,  # type: ignore
    #             "object_type": "dcim.interface",
    #         },
    #     )
    #     response = self.client.get(url)
    #     # print repsonse as formatted json string
    #     formattedstring = response.json()
    #     print(formattedstring)

    #     self.assertEqual(response.status_code, status.HTTP_200_OK, "Should return 200 OK.")
    #     # print the response data for debugging as json string
    #     print(response.data)
