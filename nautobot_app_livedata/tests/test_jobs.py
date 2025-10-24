"""Comprehensive tests for jobs in nautobot_app_livedata."""

from datetime import datetime
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.utils.timezone import make_aware
from nautobot.apps.testing import TestCase as APITransactionTestCase

import nautobot_app_livedata.jobs as jobs_module  # Used in patch.object decorators
from nautobot_app_livedata.jobs import LivedataCleanupJobResultsJob, LivedataQueryJob

from .conftest import create_db_data

User = get_user_model()


class LivedataQueryJobTest(APITransactionTestCase):
    """Test LivedataQueryJob class."""

    @classmethod
    def setUpTestData(cls):
        """Set up data for the test class."""
        cls.device_list = create_db_data()

    def setUp(self):
        """Set up data for each test case."""
        super().setUp()
        self.user = User.objects.create_user(username="testuser", password="password")
        self.job = LivedataQueryJob()
        # Mock logger
        self.job.logger = Mock()

    def test_job_initialization(self):
        """Test that job initializes with correct default values."""
        job = LivedataQueryJob()
        self.assertIsNone(job.callername)
        self.assertEqual(job.commands, [])
        self.assertIsNone(job.device)
        self.assertIsNone(job.interface)
        self.assertIsNone(job.remote_addr)
        self.assertIsNone(job.primary_device)
        self.assertIsNone(job.virtual_chassis)
        self.assertIsNone(job.x_forwarded_for)
        self.assertEqual(job.results, [])
        self.assertIsNone(job.intf_name)
        self.assertIsNone(job.intf_name_only)
        self.assertIsNone(job.intf_number)
        self.assertIsNone(job.intf_abbrev)
        self.assertIsNone(job.device_name)
        self.assertIsNone(job.device_ip)
        self.assertIsNone(job.execution_timestamp)
        self.assertIsNone(job.now)
        self.assertIsNone(job.call_object_type)

    def test_parse_commands_simple(self):
        """Test parse_commands with simple static commands."""
        self.job.intf_name = "GigabitEthernet0/1"
        self.job.intf_name_only = "GigabitEthernet"
        self.job.intf_number = "0/1"
        self.job.intf_abbrev = "Gi0/1"
        self.job.device_name = "test-device"
        self.job.primary_device = Mock()
        self.job.primary_device.name = "test-device"
        self.job.device_ip = "192.168.1.1"
        self.job.interface = Mock()
        self.job.execution_timestamp = "2025-10-24 10:00:00"
        self.job.call_object_type = "dcim.interface"

        commands_j2 = ["show version", "show ip interface brief"]
        result = self.job.parse_commands(commands_j2)

        self.assertEqual(result, ["show version", "show ip interface brief"])

    def test_parse_commands_with_jinja2_variables(self):
        """Test parse_commands with Jinja2 variable substitution."""
        self.job.intf_name = "GigabitEthernet0/1"
        self.job.intf_name_only = "GigabitEthernet"
        self.job.intf_number = "0/1"
        self.job.intf_abbrev = "Gi0/1"
        self.job.device_name = "test-device"
        self.job.primary_device = Mock()
        self.job.primary_device.name = "test-device"
        self.job.device_ip = "192.168.1.1"
        self.job.interface = Mock()
        self.job.execution_timestamp = "2025-10-24 10:00:00"
        self.job.call_object_type = "dcim.interface"

        commands_j2 = [
            "show interface {{ intf_name }}",
            "show interface {{ intf_abbrev }}",
            "! Device: {{ device_name }}",
        ]
        result = self.job.parse_commands(commands_j2)

        self.assertEqual(
            result,
            [
                "show interface GigabitEthernet0/1",
                "show interface Gi0/1",
                "! Device: test-device",
            ],
        )

    def test_parse_commands_with_invalid_jinja2(self):
        """Test parse_commands raises ValueError for invalid Jinja2 template."""
        self.job.intf_name = "GigabitEthernet0/1"
        self.job.intf_name_only = "GigabitEthernet"
        self.job.intf_number = "0/1"
        self.job.intf_abbrev = "Gi0/1"
        self.job.device_name = "test-device"
        self.job.primary_device = Mock()
        self.job.primary_device.name = "test-device"
        self.job.device_ip = "192.168.1.1"
        self.job.interface = Mock()
        self.job.execution_timestamp = "2025-10-24 10:00:00"
        self.job.call_object_type = "dcim.interface"

        commands_j2 = ["show interface {{ undefined_variable }}"]

        with self.assertRaises(ValueError) as context:
            self.job.parse_commands(commands_j2)

        self.assertIn("Failed to render Jinja2 command template", str(context.exception))

    def test_initialize_variables(self):
        """Test _initialize_variables sets correct values."""
        # Mock the user property
        with patch.object(type(self.job), "user", Mock(username="testuser")):
            kwargs = {
                "remote_addr": "192.168.1.100",
                "x_forwarded_for": "10.0.0.1",
                "call_object_type": "dcim.interface",
            }

            self.job._initialize_variables(kwargs)  # pylint: disable=protected-access

            self.assertEqual(self.job.callername, "testuser")
            self.assertIsNotNone(self.job.now)
            self.assertEqual(self.job.remote_addr, "192.168.1.100")
            self.assertEqual(self.job.x_forwarded_for, "10.0.0.1")
            self.assertEqual(self.job.call_object_type, "dcim.interface")
            self.assertIsNotNone(self.job.execution_timestamp)

    def test_initialize_variables_missing_call_object_type(self):
        """Test _initialize_variables raises ValueError when call_object_type is missing."""
        with patch.object(type(self.job), "user", Mock(username="testuser")):
            kwargs = {}

            with self.assertRaises(ValueError) as context:
                self.job._initialize_variables(kwargs)  # pylint: disable=protected-access

            self.assertIn("call_object_type is required", str(context.exception))

    def test_initialize_interface(self):
        """Test _initialize_interface sets interface correctly."""
        device = self.device_list[0]
        interface = device.interfaces.first()

        kwargs = {
            "call_object_type": "dcim.interface",
            "interface_id": interface.id,
        }

        self.job._initialize_interface(kwargs)  # pylint: disable=protected-access

        self.assertIsNotNone(self.job.interface)
        self.assertEqual(str(self.job.interface.id), str(interface.id))

    def test_initialize_interface_missing_id(self):
        """Test _initialize_interface raises ValueError when interface_id is missing."""
        kwargs = {
            "call_object_type": "dcim.interface",
        }

        with self.assertRaises(ValueError) as context:
            self.job._initialize_interface(kwargs)  # pylint: disable=protected-access

        self.assertIn("Interface_id is required", str(context.exception))

    def test_initialize_interface_not_found(self):
        """Test _initialize_interface raises ValueError when interface doesn't exist."""
        kwargs = {
            "call_object_type": "dcim.interface",
            "interface_id": "00000000-0000-0000-0000-000000000000",
        }

        with self.assertRaises(ValueError) as context:
            self.job._initialize_interface(kwargs)  # pylint: disable=protected-access

        self.assertIn("Interface with ID", str(context.exception))
        self.assertIn("not found", str(context.exception))

    def test_initialize_device(self):
        """Test _initialize_device sets device correctly."""
        device = self.device_list[0]

        kwargs = {
            "device_id": device.id,
        }

        self.job._initialize_device(kwargs)

        self.assertIsNotNone(self.job.device)
        self.assertEqual(self.job.device.id, device.id)
        self.assertEqual(self.job.device_name, device.name)

    def test_initialize_device_from_interface(self):
        """Test _initialize_device gets device from interface when device_id not provided."""
        device = self.device_list[0]
        interface = device.interfaces.first()
        self.job.interface = interface

        kwargs = {}

        self.job._initialize_device(kwargs)

        self.assertIsNotNone(self.job.device)
        self.assertEqual(self.job.device.id, device.id)

    def test_initialize_primary_device(self):
        """Test _initialize_primary_device sets primary device correctly."""
        device = self.device_list[0]

        kwargs = {
            "primary_device_id": device.id,
        }

        self.job._initialize_primary_device(kwargs)

        self.assertIsNotNone(self.job.primary_device)
        self.assertEqual(self.job.primary_device.id, device.id)
        self.assertIsNotNone(self.job.device_ip)

    def test_initialize_primary_device_not_found(self):
        """Test _initialize_primary_device raises ValueError when device doesn't exist."""
        kwargs = {
            "primary_device_id": "00000000-0000-0000-0000-000000000000",
        }

        with self.assertRaises(ValueError) as context:
            self.job._initialize_primary_device(kwargs)

        self.assertIn("Primary Device with ID", str(context.exception))
        self.assertIn("not found", str(context.exception))

    def test_initialize_virtual_chassis(self):
        """Test _initialize_virtual_chassis sets virtual chassis when provided."""
        device = self.device_list[0]

        # Check if device has virtual chassis
        if hasattr(device, "virtual_chassis") and device.virtual_chassis:
            kwargs = {
                "virtual_chassis_id": device.virtual_chassis.id,
            }

            self.job._initialize_virtual_chassis(kwargs)

            if device.virtual_chassis:
                self.assertIsNotNone(self.job.virtual_chassis)
                self.assertEqual(self.job.virtual_chassis.id, device.virtual_chassis.id)
        else:
            # Test with no virtual chassis
            kwargs = {}
            self.job._initialize_virtual_chassis(kwargs)
            # Should not raise an error

    def test_initialize_commands(self):
        """Test _initialize_commands parses commands correctly."""
        device = self.device_list[0]
        interface = device.interfaces.first()
        self.job.interface = interface
        self.job.call_object_type = "dcim.interface"
        self.job.primary_device = device
        self.job.device_ip = "192.168.1.1"
        self.job.device_name = device.name
        self.job.execution_timestamp = "2025-10-24 10:00:00"

        kwargs = {
            "commands_j2": ["show version", "show interface {{ intf_name }}"],
        }

        self.job._initialize_commands(kwargs)

        self.assertIsNotNone(self.job.commands)
        self.assertEqual(len(self.job.commands), 2)
        self.assertEqual(self.job.commands[0], "show version")
        self.assertIsNotNone(self.job.intf_name)
        self.assertIsNotNone(self.job.intf_name_only)
        self.assertIsNotNone(self.job.intf_number)
        self.assertIsNotNone(self.job.intf_abbrev)

    def test_initialize_commands_missing(self):
        """Test _initialize_commands raises ValueError when commands_j2 is missing."""
        kwargs = {}

        with self.assertRaises(ValueError) as context:
            self.job._initialize_commands(kwargs)

        self.assertIn("commands_j2 is required", str(context.exception))

    def test_before_start_interface(self):
        """Test before_start initializes all context for interface query."""
        device = self.device_list[0]
        interface = device.interfaces.first()

        with patch.object(type(self.job), "user", Mock(username="testuser")):
            kwargs = {
                "call_object_type": "dcim.interface",
                "interface_id": interface.id,
                "device_id": device.id,
                "primary_device_id": device.id,
                "commands_j2": ["show version"],
                "remote_addr": "192.168.1.100",
                "x_forwarded_for": "10.0.0.1",
            }

            self.job.before_start("test-task-id", (), kwargs)

            self.assertEqual(self.job.call_object_type, "dcim.interface")
            self.assertIsNotNone(self.job.interface)
            self.assertIsNotNone(self.job.device)
            self.assertIsNotNone(self.job.primary_device)
            self.assertIsNotNone(self.job.commands)
            self.assertEqual(len(self.job.commands), 1)

    def test_before_start_device(self):
        """Test before_start initializes all context for device query."""
        device = self.device_list[0]

        with patch.object(type(self.job), "user", Mock(username="testuser")):
            kwargs = {
                "call_object_type": "dcim.device",
                "device_id": device.id,
                "primary_device_id": device.id,
                "commands_j2": ["show version"],
                "remote_addr": "192.168.1.100",
            }

            self.job.before_start("test-task-id", (), kwargs)

            self.assertEqual(self.job.call_object_type, "dcim.device")
            self.assertIsNotNone(self.job.device)
            self.assertIsNotNone(self.job.primary_device)
            self.assertIsNotNone(self.job.commands)

    @patch.object(jobs_module, "InitNornir")
    def test_run_success(self, mock_init_nornir):
        """Test run method executes commands successfully."""
        device = self.device_list[0]

        with patch.object(type(self.job), "user", Mock(username="testuser")):
            self.job.primary_device = device
            self.job.device_name = device.name
            self.job.interface = None
            self.job.call_object_type = "dcim.device"
            self.job.commands = ["show version"]

            # Mock Nornir and Netmiko connection
            mock_nornir = Mock()
            mock_init_nornir.return_value.__enter__.return_value = mock_nornir
            mock_nr_with_processors = Mock()
            mock_nornir.with_processors.return_value = mock_nr_with_processors

            mock_filter_result = Mock()
            mock_nr_with_processors.filter.return_value = mock_filter_result

            mock_host = Mock()
            mock_filter_result.inventory.hosts = {device.name: mock_host}

            mock_connection = Mock()
            mock_connection.send_command.return_value = "Command output"
            mock_connection.disconnect.return_value = None
            mock_host.get_connection.return_value = mock_connection

            result = self.job.run()

            self.assertIsInstance(result, list)
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]["command"], "show version")
            self.assertEqual(result[0]["stdout"], "Command output")
            self.assertEqual(result[0]["stderr"], "")
            mock_connection.disconnect.assert_called_once()

    @patch.object(jobs_module, "InitNornir")
    def test_run_with_filter_syntax(self, mock_init_nornir):
        """Test run method handles !! filter syntax correctly."""
        device = self.device_list[0]

        with patch.object(type(self.job), "user", Mock(username="testuser")):
            self.job.primary_device = device
            self.job.device_name = device.name
            self.job.interface = None
            self.job.call_object_type = "dcim.device"
            self.job.commands = ["show run !! include interface"]

            # Mock Nornir and Netmiko connection
            mock_nornir = Mock()
            mock_init_nornir.return_value.__enter__.return_value = mock_nornir
            mock_nr_with_processors = Mock()
            mock_nornir.with_processors.return_value = mock_nr_with_processors

            mock_filter_result = Mock()
            mock_nr_with_processors.filter.return_value = mock_filter_result

            mock_host = Mock()
            mock_filter_result.inventory.hosts = {device.name: mock_host}

            mock_connection = Mock()
            mock_connection.send_command.return_value = "interface GigabitEthernet0/1\ninterface GigabitEthernet0/2"
            mock_connection.disconnect.return_value = None
            mock_host.get_connection.return_value = mock_connection

            with patch.object(jobs_module, "apply_output_filter") as mock_filter:
                mock_filter.return_value = "Filtered output"
                result = self.job.run()

                # Verify filter was called
                mock_filter.assert_called_once()
                self.assertEqual(len(result), 1)
                self.assertEqual(result[0]["stdout"], "Filtered output")

    @patch.object(jobs_module, "InitNornir")
    def test_run_device_not_in_inventory(self, mock_init_nornir):
        """Test run raises ValueError when device not found in inventory."""
        device = self.device_list[0]

        with patch.object(type(self.job), "user", Mock(username="testuser")):
            self.job.primary_device = device
            self.job.device_name = device.name
            self.job.interface = None
            self.job.call_object_type = "dcim.device"
            self.job.commands = ["show version"]

            # Mock Nornir but raise KeyError for device lookup
            mock_nornir = Mock()
            mock_init_nornir.return_value.__enter__.return_value = mock_nornir
            mock_nr_with_processors = Mock()
            mock_nornir.with_processors.return_value = mock_nr_with_processors

            mock_filter_result = Mock()
            mock_nr_with_processors.filter.return_value = mock_filter_result
            mock_filter_result.inventory.hosts = {}

            with self.assertRaises(ValueError) as context:
                self.job.run()

            self.assertIn("not found in Nornir inventory", str(context.exception))


class LivedataCleanupJobResultsJobTest(APITransactionTestCase):
    """Test LivedataCleanupJobResultsJob class."""

    @classmethod
    def setUpTestData(cls):
        """Set up data for the test class."""
        cls.device_list = create_db_data()

    def setUp(self):
        """Set up data for each test case."""
        super().setUp()
        self.user = User.objects.create_user(username="testuser", password="password")
        self.job = LivedataCleanupJobResultsJob()
        # Mock logger
        self.job.logger = Mock()

    def test_job_meta_attributes(self):
        """Test that job has correct meta attributes."""
        self.assertEqual(self.job.Meta.name, "Livedata Cleanup job results")
        self.assertEqual(self.job.Meta.description, "Cleanup the Livedata Query Interface Job results.")
        self.assertFalse(self.job.Meta.dry_run_default)
        self.assertFalse(self.job.Meta.has_sensitive_variables)
        self.assertFalse(self.job.Meta.hidden)
        self.assertEqual(self.job.Meta.soft_time_limit, 60)
        self.assertTrue(self.job.Meta.enabled)

    @patch.object(jobs_module.JobResult.objects, "filter")
    def test_run_dry_run(self, mock_filter):
        """Test run with dry_run=True returns count without deleting."""
        # Mock QuerySets
        mock_query_results = Mock()
        mock_query_results.count.return_value = 5
        mock_cleanup_results = Mock()
        mock_cleanup_results.count.return_value = 2

        mock_filter.side_effect = [mock_query_results, mock_cleanup_results]

        result = self.job.run(days_to_keep=30, dry_run=True)

        self.assertIn("5 job results", result)
        self.assertIn("would be deleted", result)
        self.assertIn("2 cleanup job results", result)
        # Verify delete was not called
        mock_query_results.delete.assert_not_called()
        mock_cleanup_results.delete.assert_not_called()

    @patch.object(jobs_module.JobResult.objects, "filter")
    def test_run_delete(self, mock_filter):
        """Test run with dry_run=False actually deletes records."""
        # Mock QuerySets
        mock_query_results = Mock()
        mock_query_results.delete.return_value = (5, {})
        mock_cleanup_results = Mock()
        mock_cleanup_results.delete.return_value = (2, {})

        mock_filter.side_effect = [mock_query_results, mock_cleanup_results]

        result = self.job.run(days_to_keep=30, dry_run=False)

        self.assertIn("Deleted 5 job results", result)
        self.assertIn("Deleted 2 cleanup job results", result)
        # Verify delete was called
        mock_query_results.delete.assert_called_once()
        mock_cleanup_results.delete.assert_called_once()

    @patch.object(jobs_module.JobResult.objects, "filter")
    def test_run_default_days_to_keep(self, mock_filter):
        """Test run uses default 30 days when days_to_keep is None."""
        mock_query_results = Mock()
        mock_query_results.count.return_value = 0
        mock_cleanup_results = Mock()
        mock_cleanup_results.count.return_value = 0

        mock_filter.side_effect = [mock_query_results, mock_cleanup_results]

        result = self.job.run(days_to_keep=None, dry_run=True)

        # Should use default 30 days
        self.assertIn("30 days", result)

    @patch.object(jobs_module.timezone, "now")
    @patch.object(jobs_module.JobResult.objects, "filter")
    def test_run_filters_by_cutoff_date(self, mock_filter, mock_now):
        """Test run filters JobResults by correct cutoff date."""
        # Set fixed "now" time
        fixed_now = make_aware(datetime(2025, 10, 24, 12, 0, 0))
        mock_now.return_value = fixed_now

        mock_query_results = Mock()
        mock_query_results.count.return_value = 0
        mock_cleanup_results = Mock()
        mock_cleanup_results.count.return_value = 0

        mock_filter.side_effect = [mock_query_results, mock_cleanup_results]

        self.job.run(days_to_keep=7, dry_run=True)

        # Verify filter was called with correct parameters
        calls = mock_filter.call_args_list

        # First call should filter query job results
        self.assertIn("date_done__lt", str(calls[0]))
        # Second call should filter cleanup job results
        self.assertIn("date_done__lt", str(calls[1]))
