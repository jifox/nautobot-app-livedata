"""Unit tests for customfield.py."""


# class CustomFieldUtilsTest(TestCase):
#     """Test the CustomFieldUtils class."""

#     @classmethod
#     def setUpTestData(cls):
#         """Set up test data."""
#         wait_for_debugger_connection()  # To enable set env REMOTE_TEST_DEBUG_ENABLE=True
#         cls.device_list = create_db_data()

#     def setUp(self):
#         """Set up test data."""
#         self.key_name = "test_field"
#         self.field_type = CustomFieldTypeChoices.TYPE_TEXT
#         self.defaults = {
#             "label": "Test Field",
#             "description": "A test custom field",
#             "default": "default value",
#             "required": False,
#             "filter_logic": "loose",
#             "weight": 100,
#             "advanced_ui": False,
#         }
#         self.model_names = ["dcim.device"]

#     def test_add_custom_field(self):
#         """Test adding a custom field."""
#         custom_field_utils = CustomFieldUtils(
#             key_name=self.key_name,
#             field_type=self.field_type,
#             defaults=self.defaults,
#             model_names=self.model_names,
#         )
#         custom_field = custom_field_utils.add_custom_field()
#         self.assertEqual(custom_field.key, self.key_name)
#         self.assertEqual(custom_field.type, self.field_type)
#         self.assertEqual(custom_field.label, self.defaults["label"])
#         self.assertEqual(custom_field.description, self.defaults["description"])
#         self.assertEqual(custom_field.default, self.defaults["default"])
#         self.assertEqual(custom_field.required, self.defaults["required"])
#         self.assertEqual(custom_field.filter_logic, self.defaults["filter_logic"])
#         self.assertEqual(custom_field.weight, self.defaults["weight"])
#         self.assertEqual(custom_field.advanced_ui, self.defaults["advanced_ui"])

#     def test_invalid_field_type(self):
#         """Test invalid field type."""
#         with self.assertRaises(ValueError):
#             CustomFieldUtils(
#                 key_name=self.key_name,
#                 field_type="invalid_type",
#                 defaults=self.defaults,
#                 model_names=self.model_names,
#             )

#     def test_invalid_key_name(self):
#         """Test invalid key name."""
#         with self.assertRaises(ValueError):
#             CustomFieldUtils(
#                 key_name="invalid key name",
#                 field_type=self.field_type,
#                 defaults=self.defaults,
#                 model_names=self.model_names,
#             )

#     def test_invalid_model_name(self):
#         """Test invalid model name."""
#         with self.assertRaises(ValueError):
#             CustomFieldUtils(
#                 key_name=self.key_name,
#                 field_type=self.field_type,
#                 defaults=self.defaults,
#                 model_names=["invalid.model"],
#             )

#     # get_livedata_commands_for_interface specific tests

#     def test_get_livedata_commands(self):
#         """Test getting livedata commands for an interface."""
#         intf = self.device_list[0].interfaces.first()
#         commands = get_livedata_commands_for_interface(intf)
#         self.assertEqual(commands, ["command1", "command2"])

#     def test_no_platform(self):
#         """Test device with no platform."""
#         intf = self.device_list[6].interfaces.first()
#         with self.assertRaises(ValueError):
#             get_livedata_commands_for_interface(intf)

#     def test_no_network_driver(self):
#         """Test device with no network driver."""
#         intf = self.device_list[5].interfaces.first()
#         with self.assertRaises(ValueError):
#             get_livedata_commands_for_interface(intf)

#     def test_no_platform_no_driver(self):
#         """Test device with no platform and no network driver."""
#         intf = self.device_list[7].interfaces.first()
#         with self.assertRaises(ValueError):
#             get_livedata_commands_for_interface(intf)
