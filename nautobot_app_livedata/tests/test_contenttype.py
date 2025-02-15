"""Unit tests for contenttype.py."""

from django.test import TestCase

from nautobot_app_livedata.utilities.contenttype import ContentTypeUtils

from .conftest import create_db_data, wait_for_debugger_connection


class ContentTypeUtilsTest(TestCase):
    """Test the ContentTypeUtils class."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        wait_for_debugger_connection()  # To enable set env REMOTE_TEST_DEBUG_ENABLE=True
        cls.device_list = create_db_data()

    def setUp(self):
        """Set up test data."""
        self.content_type_utils = ContentTypeUtils(full_model_name="dcim.device")

    def test_get_content_type_for_model(self):
        """Test getting content type for a model."""
        content_type = self.content_type_utils.content_type_for_model
        self.assertEqual(content_type.model, "device")
        self.assertEqual(content_type.app_label, "dcim")

    def test_invalid_model_name(self):
        """Test invalid model name."""
        with self.assertRaises(ValueError):
            contenttype = ContentTypeUtils(full_model_name="invalid.model")
            _ = contenttype.content_type_for_model

    def test_get_full_model_name(self):
        """Test getting full model name."""
        full_model_name = self.content_type_utils.full_model_name
        self.assertEqual(full_model_name, "dcim.device")

    def test_set_full_model_name(self):
        """Test setting full model name."""
        self.content_type_utils.full_model_name = "dcim.device"
        self.assertEqual(self.content_type_utils.full_model_name, "dcim.device")
