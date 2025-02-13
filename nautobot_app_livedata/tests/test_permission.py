"""Test cases for the PermissionUtils classes."""

from nautobot.apps.testing import TestCase
from nautobot.core.models import ContentType
from nautobot.users.models import ObjectPermission

from nautobot_app_livedata.utilities.permission import create_permission

from .conftest import wait_for_debugger_connection


class TestPermission(TestCase):
    """Test the PermissionUtils class."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        super().setUpTestData()
        wait_for_debugger_connection()  # To enable set env REMOTE_TEST_DEBUG_ENABLE=True

    def setup(self):
        """Set up test data."""
        super().setUp()

    def test_permission_utils_initialization(self):
        """Test PermissionUtils initialization."""
        db_objects = {
            "ContentType": ContentType,
            "ObjectPermission": ObjectPermission,
        }
        create_permission(
            db_objects=db_objects,
            name="livedata.interact_with_devices",
            actions_list=["can_interact"],
            description="Interact with devices without permission to change device configurations.",
            full_model_name="dcim.device",
        )
        pu = ObjectPermission.objects.get(name="livedata.interact_with_devices")
        self.assertEqual(pu.name, "livedata.interact_with_devices")
        self.assertEqual(pu.actions, ["can_interact"])
        self.assertEqual(pu.description, "Interact with devices without permission to change device configurations.")
        self.assertEqual(str(pu.object_types.first()), "dcim | device")
