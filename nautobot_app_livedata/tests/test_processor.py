"""Tests for nornir_plays/processor.py."""

# Filepath: nautobot_app_livedata/tests/test_processor.py

from unittest.mock import Mock

from django.test import TestCase
from nornir.core.task import MultiResult, Result
from nornir_nautobot.exceptions import NornirNautobotException

from nautobot_app_livedata.nornir_plays.processor import ProcessLivedata


class ProcessLivedataTest(TestCase):
    """Tests for ProcessLivedata processor class."""

    def setUp(self):
        """Set up test fixtures."""
        self.logger = Mock()
        self.processor = ProcessLivedata(self.logger)

    def test_initialization(self):
        """Test ProcessLivedata initializes with logger."""
        self.assertEqual(self.processor.logger, self.logger)

    def test_find_result_exceptions_no_failure(self):
        """Test _find_result_exceptions returns empty list for successful result."""
        result = Result(host=Mock(), result="Success")
        result.failed = False

        # pylint: disable=protected-access
        exceptions = self.processor._find_result_exceptions(result)

        self.assertEqual(exceptions, [])

    def test_find_result_exceptions_with_exception(self):
        """Test _find_result_exceptions finds valid exceptions."""
        exception = ValueError("Test error")
        host_mock = Mock()
        result = Result(host=host_mock, result="Error traceback", exception=exception, failed=True)

        # pylint: disable=protected-access
        exceptions = self.processor._find_result_exceptions(result)

        self.assertEqual(len(exceptions), 1)
        self.assertEqual(exceptions[0][0], exception)
        self.assertEqual(exceptions[0][1], "Error traceback")

    def test_find_result_exceptions_filters_nautobot_exceptions(self):
        """Test _find_result_exceptions filters out NornirNautobotException."""
        nautobot_exception = NornirNautobotException("Expected error")
        host_mock = Mock()
        result = Result(host=host_mock, result="Error traceback", exception=nautobot_exception, failed=True)

        # pylint: disable=protected-access
        exceptions = self.processor._find_result_exceptions(result)

        self.assertEqual(exceptions, [])

    def test_find_result_exceptions_multiresult_with_exception(self):
        """Test _find_result_exceptions handles MultiResult with exception."""
        exception = RuntimeError("Multi error")
        multi_result = Mock(spec=MultiResult)
        multi_result.failed = True
        multi_result.exception = exception
        multi_result.result = "Multi error traceback"

        # pylint: disable=protected-access
        exceptions = self.processor._find_result_exceptions(multi_result)

        self.assertEqual(len(exceptions), 1)
        self.assertEqual(exceptions[0][0], exception)
        self.assertEqual(exceptions[0][1], "Multi error traceback")

    def test_find_result_exceptions_multiresult_filters_nautobot_exceptions(self):
        """Test _find_result_exceptions filters NornirNautobotException from MultiResult."""
        nautobot_exception = NornirNautobotException("Expected multi error")
        multi_result = Mock(spec=MultiResult)
        multi_result.failed = True
        multi_result.exception = nautobot_exception
        multi_result.result = "Multi error traceback"

        # pylint: disable=protected-access
        exceptions = self.processor._find_result_exceptions(multi_result)

        self.assertEqual(exceptions, [])

    def test_find_result_exceptions_recursive_search(self):
        """Test _find_result_exceptions recursively searches nested results."""
        inner_exception = ValueError("Inner error")
        host_mock = Mock()
        inner_result = Result(host=host_mock, result="Inner traceback", exception=inner_exception, failed=True)

        # Create outer result with nested exception result
        outer_exception = Mock()
        outer_exception.result = [inner_result]
        outer_result = Mock()
        outer_result.failed = True
        outer_result.exception = outer_exception

        # pylint: disable=protected-access
        exceptions = self.processor._find_result_exceptions(outer_result)

        self.assertEqual(len(exceptions), 1)
        self.assertEqual(exceptions[0][0], inner_exception)
        self.assertEqual(exceptions[0][1], "Inner traceback")

    def test_task_instance_completed_success(self):
        """Test task_instance_completed handles successful result."""
        mock_task = Mock()
        mock_task.name = "test_task"
        mock_host = Mock()
        mock_host.data = {"obj": Mock()}

        multi_result = Mock(spec=MultiResult)
        multi_result.failed = False

        self.processor.task_instance_completed(mock_task, mock_host, multi_result)

        # Verify host connections closed
        mock_host.close_connections.assert_called_once()
        # Verify no error logged
        self.logger.error.assert_not_called()

    def test_task_instance_completed_with_failure_no_exceptions(self):
        """Test task_instance_completed handles failed result without valid exceptions."""
        mock_task = Mock()
        mock_task.name = "test_task"
        mock_host = Mock()
        mock_host.data = {"obj": Mock()}

        # Failed result but with NornirNautobotException (filtered out)
        nautobot_exception = NornirNautobotException("Expected error")
        multi_result = Mock(spec=MultiResult)
        multi_result.failed = True
        multi_result.exception = nautobot_exception
        multi_result.result = "Traceback"

        self.processor.task_instance_completed(mock_task, mock_host, multi_result)

        # Verify host connections closed
        mock_host.close_connections.assert_called_once()
        # Verify no error logged (exception was filtered)
        self.logger.error.assert_not_called()

    def test_task_instance_completed_with_failure_and_exceptions(self):
        """Test task_instance_completed logs error for failed result with exceptions."""
        device_obj = Mock()
        device_obj.name = "test-device"

        mock_task = Mock()
        mock_task.name = "test_task"
        mock_task.host = Mock()
        mock_task.host.data = {"obj": device_obj}

        mock_host = Mock()
        mock_host.data = {"obj": device_obj}

        # Failed result with valid exception
        exception = ValueError("Test error")
        multi_result = Mock(spec=MultiResult)
        multi_result.failed = True
        multi_result.exception = exception
        multi_result.result = "Error traceback"

        self.processor.task_instance_completed(mock_task, mock_host, multi_result)

        # Verify host connections closed
        mock_host.close_connections.assert_called_once()
        # Verify error logged
        self.logger.error.assert_called_once()
        call_args = self.logger.error.call_args
        self.assertIn("test_task failed", call_args[0][0])
        self.assertIn("Test error", call_args[0][0])
        self.assertEqual(call_args[1]["extra"]["object"], device_obj)

    def test_task_instance_completed_with_multiple_exceptions(self):
        """Test task_instance_completed logs all exceptions."""
        device_obj = Mock()
        mock_task = Mock()
        mock_task.name = "multi_error_task"
        mock_task.host = Mock()
        mock_task.host.data = {"obj": device_obj}

        mock_host = Mock()
        mock_host.data = {"obj": device_obj}

        # Create result with nested exceptions
        inner_exception1 = ValueError("Error 1")
        inner_result1 = Result(host=Mock(), result="Traceback 1", exception=inner_exception1, failed=True)

        inner_exception2 = RuntimeError("Error 2")
        inner_result2 = Result(host=Mock(), result="Traceback 2", exception=inner_exception2, failed=True)

        # Create outer result - not a MultiResult or Result, so will hit else branch
        outer_exception = Mock()
        outer_exception.result = [inner_result1, inner_result2]
        outer_result = Mock()  # Plain Mock, not spec=MultiResult
        outer_result.failed = True
        outer_result.exception = outer_exception

        self.processor.task_instance_completed(mock_task, mock_host, outer_result)

        # Verify host connections closed
        mock_host.close_connections.assert_called_once()
        # Verify error logged with both exceptions
        self.logger.error.assert_called_once()
        call_args = self.logger.error.call_args
        log_message = call_args[0][0]
        self.assertIn("multi_error_task failed", log_message)
        self.assertIn("Error 1", log_message)
        self.assertIn("Error 2", log_message)
