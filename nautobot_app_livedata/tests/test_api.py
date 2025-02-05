"""Unit tests for nautobot_app_livedata."""

from django.contrib.auth import get_user_model
from django.test import RequestFactory
from django.urls import reverse
from nautobot.apps.testing import TestCase as APITransactionTestCase
from nautobot.users.models import ObjectPermission
from rest_framework import status

from nautobot_app_livedata.api.views import LivedataPrimaryDeviceApiView

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
        self.forbidden_user = User.objects.create(username="forbidden_user", password="password")
        permission = ObjectPermission.objects.get(name="livedata.interact_with_devices")
        self.user.object_permissions.add(permission)  # type: ignore
        self.client.force_authenticate(user=self.user)

    # def test_self_user_has_permission_can_interact(self):
    #     """Test that the user has the permission to interact with devices."""
    #     self.user.is_superuser = False
    #     self.user.save()
    #     self.assertTrue(
    #         self.user.has_perm("dcim.can_interact_device", self.device_list[0]),  # type: ignore
    #         "User should have permission to interact with devices.",
    #     )

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
        response = LivedataPrimaryDeviceApiView.as_view()(request)

        self.user.is_superuser = False
        self.user.save()
        self.client.logout()
        self.client.credentials(HTTP_AUTHORIZATION="Token " + "invalid_token")
        response = self.client.get(url, format="json")
        self.assertTrue(b"PermissionDenied" in response.content, "Should return PermissionDenied (logged out).")
        self.client.force_authenticate(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION="Token " + "invalid_token")
        self.assertTrue(b"PermissionDenied" in response.content, "Should return PermissionDenied (missing permission).")

    def test_primary_device_from_interface_on_device_with_primary_ip(self):
        """Test that the device with the primary_ip is returned."""
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
        self.assertEqual(response.status_code, status.HTTP_200_OK, "Should return 200 OK.")

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
