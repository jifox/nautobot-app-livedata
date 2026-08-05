"""
Unit tests for output filtering utilities in Nautobot App Livedata.
"""

from nautobot.apps.testing import TestCase

from nautobot_app_livedata.utilities.output_filter import apply_output_filter


class TestOutputFilter(TestCase):
    """Unit tests for output filtering utilities."""

    def test_exact_filter(self):
        output = "foo\nbar\nbaz\nfoo"
        filtered = apply_output_filter(output, "EXACT:foo")
        self.assertEqual(filtered, "foo\nfoo")

    def test_last_filter(self):
        output = "line1\nline2\nline3\nline4\nline5"
        filtered = apply_output_filter(output, "LAST:2")
        self.assertEqual(filtered, "line4\nline5")

    def test_no_filter(self):
        output = "a\nb\nc"
        filtered = apply_output_filter(output, None)
        self.assertEqual(filtered, output)

    def test_unknown_filter(self):
        output = "a\nb\nc"
        filtered = apply_output_filter(output, "FOO:bar")
        self.assertEqual(filtered, output)

    def test_last_filter_invalid(self):
        output = "a\nb\nc"
        filtered = apply_output_filter(output, "LAST:xyz")
        self.assertEqual(filtered, output)

    def test_exact_filter_whole_word(self):
        output = " Gi1/0/1\n1/0/1  \n^1/0/1 \n1/0/1$\n11/0/1\n1/0/11\n1/0/111\nfoo1/0/1bar\n1/0/1foo\nfoo1/0/1"
        filtered = apply_output_filter(output, "EXACT:1/0/1")
        self.assertEqual(filtered, " Gi1/0/1\n1/0/1  \n^1/0/1 \n1/0/1$")

    def test_multiple_filters(self):
        output = "foo\nbar\nfoo\nbaz\nfoo"
        # Apply EXACT:foo, then LAST:2
        filtered = apply_output_filter(output, "EXACT:foo!!LAST:2!!")
        self.assertEqual(filtered, "foo\nfoo")
        # Apply LAST:3, then EXACT:foo
        filtered2 = apply_output_filter(output, "LAST:3!!EXACT:foo!!")
        self.assertEqual(filtered2, "foo\nfoo")
        # Apply EXACT:foo, then LAST:1
        filtered3 = apply_output_filter(output, "EXACT:foo!!LAST:1!!")
        self.assertEqual(filtered3, "foo")

    def test_first_filter(self):
        output = "line1\nline2\nline3\nline4\nline5"
        filtered = apply_output_filter(output, "FIRST:3")
        self.assertEqual(filtered, "line1\nline2\nline3")

    def test_exact_filter_full_interface_name_in_log_line(self):
        output = "\n".join(
            [
                "Aug  3 09:49:20.277 MES: %LINK-5-UPDOWN: Interface GigabitEthernet4/0/36, changed state to up",
                "Aug  3 09:49:21.277 MES: %LINEPROTO-5-UPDOWN: Line protocol on Interface "
                "GigabitEthernet4/0/36, changed state to up",
                "Aug  3 09:49:20.277 MES: %LINK-5-UPDOWN: Interface GigabitEthernet14/0/36, changed state to up",
                "Aug  3 09:49:20.277 MES: %LINK-5-UPDOWN: Interface GigabitEthernet4/0/360, changed state to up",
                "Aug  3 09:49:20.277 MES: %LINK-5-UPDOWN: Interface GigabitEthernet4/0/3, changed state to up",
            ]
        )
        filtered = apply_output_filter(output, "EXACT:4/0/36")
        self.assertEqual(
            filtered,
            "Aug  3 09:49:20.277 MES: %LINK-5-UPDOWN: Interface GigabitEthernet4/0/36, "
            "changed state to up\n"
            "Aug  3 09:49:21.277 MES: %LINEPROTO-5-UPDOWN: Line protocol on Interface "
            "GigabitEthernet4/0/36, changed state to up",
        )

    def test_exact_filter_interface_mention_with_trailing_text(self):
        output = "Gi1/0/1 is up\nfoo1/0/1 is up\nGi1/0/1\nTe1/0/11 is up"
        filtered = apply_output_filter(output, "EXACT:1/0/1")
        self.assertEqual(filtered, "Gi1/0/1 is up\nGi1/0/1")
