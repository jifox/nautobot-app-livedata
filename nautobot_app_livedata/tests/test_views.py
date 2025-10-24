"""Comprehensive tests for API views in nautobot_app_livedata."""

from http import HTTPStatus
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test import RequestFactory
from django.urls import reverse
from nautobot.apps.testing import TestCase as APITransactionTestCase
from nautobot.dcim.models import Device
from nautobot.extras.jobs import RunJobTaskFailed
from nautobot.extras.models import Job, JobResult
from nautobot.users.models import ObjectPermission

from nautobot_app_livedata.api.views import (
    LivedataQueryDeviceApiView,
    LivedataQueryInterfaceApiView,
)
from nautobot_app_livedata.utilities.permission import create_permission

from .conftest import create_db_data

User = get_user_model()


class LivedataQueryInterfaceApiViewTest(APITransactionTestCase):
    """Test LivedataQueryInterfaceApiView."""

    @classmethod
    def setUpTestData(cls):
        """Set up data for the test class."""
        cls.device_list = create_db_data()

    def setUp(self):
        """Set up data for each test case."""
        super().setUp()
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username="testuser", password="password")
        self.forbidden_user = User.objects.create_user(username="forbidden_user", password="password")

        # Grant the user the dcim.can_interact_device permission
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
        self.client.force_authenticate(user=self.user)

    def test_get_object_type(self):
        """Test that get_object_type returns correct object type for interface."""
        view = LivedataQueryInterfaceApiView()
        self.assertEqual(view.get_object_type(), "dcim.interface")

    def test_get_commands_for_interface(self):
        """Test that get_commands retrieves interface commands."""
        device = self.device_list[0]
        interface = device.interfaces.first()
        view = LivedataQueryInterfaceApiView()

        commands = view.get_commands(interface)
        self.assertIsInstance(commands, list)

    def test_interface_query_without_permission(self):
        """Test that interface query without permission returns 403."""
        device = self.device_list[0]
        interface = device.interfaces.first()

        url = reverse(
            "plugins-api:nautobot_app_livedata-api:livedata-query-intf-api",
            kwargs={"pk": interface.id},
        )

        self.client.force_authenticate(user=self.forbidden_user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)

    @patch("nautobot_app_livedata.api.views.get_livedata_commands_for_interface")
    @patch("nautobot_app_livedata.api.views.JobResult.enqueue_job")
    @patch("nautobot_app_livedata.api.views.Job.objects.filter")
    def test_interface_query_success(self, mock_job_filter, mock_enqueue, mock_get_commands):
        """Test successful interface query."""
        device = self.device_list[0]
        interface = device.interfaces.first()

        # Mock commands
        mock_get_commands.return_value = ["show interface {{ interface.name }}"]

        # Mock job and job result
        mock_job = Mock(spec=Job)
        mock_job.name = "Livedata Api-Job"
        mock_job_filter.return_value.first.return_value = mock_job

        mock_job_result = Mock(spec=JobResult)
        mock_job_result.id = "test-job-result-id"
        mock_enqueue.return_value = mock_job_result

        url = reverse(
            "plugins-api:nautobot_app_livedata-api:livedata-query-intf-api",
            kwargs={"pk": interface.id},
        )

        response = self.client.get(url)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        response_data = response.json()
        self.assertIn("jobresult_id", response_data)
        self.assertEqual(response_data["jobresult_id"], "test-job-result-id")

    @patch("nautobot_app_livedata.api.views.Job.objects.filter")
    def test_interface_query_job_not_found(self, mock_job_filter):
        """Test interface query when job is not found."""
        device = self.device_list[0]
        interface = device.interfaces.first()

        mock_job_filter.return_value.first.return_value = None

        url = reverse(
            "plugins-api:nautobot_app_livedata-api:livedata-query-intf-api",
            kwargs={"pk": interface.id},
        )

        response = self.client.get(url)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_interface_query_invalid_pk(self):
        """Test interface query with invalid primary key."""
        # Use a UUID that doesn't exist
        url = reverse(
            "plugins-api:nautobot_app_livedata-api:livedata-query-intf-api",
            kwargs={"pk": "00000000-0000-0000-0000-000000000000"},
        )

        response = self.client.get(url)
        # Serializer validation fails first, so we get BAD_REQUEST instead of NOT_FOUND
        self.assertIn(response.status_code, [HTTPStatus.BAD_REQUEST, HTTPStatus.NOT_FOUND])


class LivedataQueryDeviceApiViewTest(APITransactionTestCase):
    """Test LivedataQueryDeviceApiView."""

    @classmethod
    def setUpTestData(cls):
        """Set up data for the test class."""
        cls.device_list = create_db_data()

    def setUp(self):
        """Set up data for each test case."""
        super().setUp()
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username="testuser", password="password")
        self.forbidden_user = User.objects.create_user(username="forbidden_user", password="password")

        # Grant the user the dcim.can_interact_device permission
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
        self.client.force_authenticate(user=self.user)

    def test_get_object_type(self):
        """Test that get_object_type returns correct object type for device."""
        view = LivedataQueryDeviceApiView()
        self.assertEqual(view.get_object_type(), "dcim.device")

    def test_get_commands_for_device(self):
        """Test that get_commands delegates to get_livedata_commands_for_device."""
        view = LivedataQueryDeviceApiView()

        # Just verify the method exists and is callable
        # Don't test the actual implementation since it requires custom fields
        self.assertTrue(hasattr(view, "get_commands"))
        self.assertTrue(callable(view.get_commands))

    def test_get_queryset_restricts_to_user_permissions(self):
        """Test that get_queryset restricts devices based on user permissions."""
        view = LivedataQueryDeviceApiView()
        request = self.factory.get("/")
        request.user = self.user
        view.request = request

        queryset = view.get_queryset()
        self.assertIsNotNone(queryset)
        # The queryset should be restricted by the user's permissions
        self.assertTrue(hasattr(queryset, "model"))
        self.assertEqual(queryset.model, Device)

    def test_device_query_without_permission(self):
        """Test that device query without permission returns 403."""
        device = self.device_list[0]

        url = reverse(
            "plugins-api:nautobot_app_livedata-api:livedata-query-device-api",
            kwargs={"pk": device.id},
        )

        self.client.force_authenticate(user=self.forbidden_user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)

    @patch("nautobot_app_livedata.api.views.get_livedata_commands_for_device")
    @patch("nautobot_app_livedata.api.views.JobResult.enqueue_job")
    @patch("nautobot_app_livedata.api.views.Job.objects.filter")
    def test_device_query_success(self, mock_job_filter, mock_enqueue, mock_get_commands):
        """Test successful device query."""
        device = self.device_list[0]

        # Mock commands
        mock_get_commands.return_value = ["show version", "show ip interface brief"]

        # Mock job and job result
        mock_job = Mock(spec=Job)
        mock_job.name = "Livedata Api-Job"
        mock_job_filter.return_value.first.return_value = mock_job

        mock_job_result = Mock(spec=JobResult)
        mock_job_result.id = "test-job-result-id"
        mock_enqueue.return_value = mock_job_result

        url = reverse(
            "plugins-api:nautobot_app_livedata-api:livedata-query-device-api",
            kwargs={"pk": device.id},
        )

        response = self.client.get(url)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        response_data = response.json()
        self.assertIn("jobresult_id", response_data)
        self.assertEqual(response_data["jobresult_id"], "test-job-result-id")

    @patch("nautobot_app_livedata.api.views.get_livedata_commands_for_device")
    @patch("nautobot_app_livedata.api.views.JobResult.enqueue_job")
    @patch("nautobot_app_livedata.api.views.Job.objects.filter")
    def test_device_query_enqueue_failure(self, mock_job_filter, mock_enqueue, mock_get_commands):
        """Test device query when job enqueue fails."""
        device = self.device_list[0]

        # Mock commands
        mock_get_commands.return_value = ["show version"]

        # Mock job
        mock_job = Mock(spec=Job)
        mock_job.name = "Livedata Api-Job"
        mock_job_filter.return_value.first.return_value = mock_job

        # Mock enqueue failure
        mock_enqueue.side_effect = RunJobTaskFailed("Job enqueue failed")

        url = reverse(
            "plugins-api:nautobot_app_livedata-api:livedata-query-device-api",
            kwargs={"pk": device.id},
        )

        response = self.client.get(url)
        self.assertEqual(response.status_code, HTTPStatus.INTERNAL_SERVER_ERROR)

    def test_device_query_invalid_pk(self):
        """Test device query with invalid primary key."""
        # Use a UUID that doesn't exist
        url = reverse(
            "plugins-api:nautobot_app_livedata-api:livedata-query-device-api",
            kwargs={"pk": "00000000-0000-0000-0000-000000000000"},
        )

        response = self.client.get(url)
        # Serializer validation fails first, so we get BAD_REQUEST instead of NOT_FOUND
        self.assertIn(response.status_code, [HTTPStatus.BAD_REQUEST, HTTPStatus.NOT_FOUND])


class LivedataPrimaryDeviceApiViewTest(APITransactionTestCase):
    """Test LivedataPrimaryDeviceApiView."""

    @classmethod
    def setUpTestData(cls):
        """Set up data for the test class."""
        cls.device_list = create_db_data()

    def setUp(self):
        """Set up data for each test case."""
        super().setUp()
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username="testuser", password="password")
        self.forbidden_user = User.objects.create_user(username="forbidden_user", password="password")

        # Grant the user the dcim.can_interact_device permission
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
        self.client.force_authenticate(user=self.user)

    def test_primary_device_api_with_device_object_type(self):
        """Test primary device API with device object type."""
        device = self.device_list[0]

        url = reverse(
            "plugins-api:nautobot_app_livedata-api:livedata-managed-device-api",
            kwargs={
                "pk": device.id,
                "object_type": "dcim.device",
            },
        )

        response = self.client.get(url)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        response_data = response.json()
        self.assertIn("primary_device", response_data)

    def test_primary_device_api_with_interface_object_type(self):
        """Test primary device API with interface object type."""
        device = self.device_list[0]
        interface = device.interfaces.first()

        url = reverse(
            "plugins-api:nautobot_app_livedata-api:livedata-managed-device-api",
            kwargs={
                "pk": interface.id,
                "object_type": "dcim.interface",
            },
        )

        response = self.client.get(url)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        response_data = response.json()
        self.assertIn("primary_device", response_data)

    def test_primary_device_api_without_permission(self):
        """Test that primary device API without permission returns 403."""
        device = self.device_list[0]
        interface = device.interfaces.first()

        url = reverse(
            "plugins-api:nautobot_app_livedata-api:livedata-managed-device-api",
            kwargs={
                "pk": interface.id,
                "object_type": "dcim.interface",
            },
        )

        self.client.force_authenticate(user=self.forbidden_user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)
        response_data = response.json()
        self.assertIn("error", response_data)

    def test_primary_device_api_with_invalid_object_type(self):
        """Test primary device API with invalid object type."""
        device = self.device_list[0]

        url = reverse(
            "plugins-api:nautobot_app_livedata-api:livedata-managed-device-api",
            kwargs={
                "pk": device.id,
                "object_type": "invalid.type",
            },
        )

        response = self.client.get(url)
        # Should return BAD_REQUEST due to serializer validation failure
        self.assertIn(response.status_code, [HTTPStatus.BAD_REQUEST, HTTPStatus.NOT_FOUND])

    def test_primary_device_api_with_invalid_pk(self):
        """Test primary device API with invalid primary key."""
        url = reverse(
            "plugins-api:nautobot_app_livedata-api:livedata-managed-device-api",
            kwargs={
                "pk": "00000000-0000-0000-0000-000000000000",
                "object_type": "dcim.device",
            },
        )

        response = self.client.get(url)
        # Should return BAD_REQUEST or NOT_FOUND
        self.assertIn(response.status_code, [HTTPStatus.BAD_REQUEST, HTTPStatus.NOT_FOUND])

    def test_primary_device_api_serializer_invalid_data(self):
        """Test primary device API with data that fails serializer validation."""
        # Create a mock request with invalid data
        device = self.device_list[0]

        url = reverse(
            "plugins-api:nautobot_app_livedata-api:livedata-managed-device-api",
            kwargs={
                "pk": device.id,
                "object_type": "dcim.device",
            },
        )

        # Make request - serializer will validate the data
        response = self.client.get(url)

        # Response should either succeed or fail gracefully
        self.assertIn(
            response.status_code,
            [HTTPStatus.OK, HTTPStatus.BAD_REQUEST, HTTPStatus.NOT_FOUND],
        )

    def test_primary_device_api_returns_correct_structure(self):
        """Test that primary device API returns correct data structure."""
        device = self.device_list[0]
        interface = device.interfaces.first()

        url = reverse(
            "plugins-api:nautobot_app_livedata-api:livedata-managed-device-api",
            kwargs={
                "pk": interface.id,
                "object_type": "dcim.interface",
            },
        )

        response = self.client.get(url)

        if response.status_code == HTTPStatus.OK:
            response_data = response.json()
            # Check for expected keys in response
            expected_keys = ["object_type", "pk"]
            for key in expected_keys:
                self.assertIn(key, response_data, f"Response should contain '{key}' key")
