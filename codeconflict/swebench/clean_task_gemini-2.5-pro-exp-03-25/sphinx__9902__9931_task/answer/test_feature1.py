# answer/test_feature1.py
import unittest
from answer.formatter import format_type

class TestFeature1(unittest.TestCase):
    """Tests the explicit shortening feature (tilde prefix)."""

    def test_explicit_shorten_qualified(self):
        """Test that '~' shortens a qualified name."""
        self.assertEqual(format_type("~collections.deque"), "deque")

    def test_explicit_shorten_unqualified(self):
        """Test that '~' on an unqualified name just removes the tilde."""
        self.assertEqual(format_type("~MyType"), "MyType")

    def test_no_shorten_without_tilde(self):
        """Test that qualified names are not shortened without '~' (when force_short_name=False)."""
        self.assertEqual(format_type("collections.deque"), "collections.deque")
        self.assertEqual(format_type("collections.deque", force_short_name=False), "collections.deque")

    def test_no_shorten_unqualified_without_tilde(self):
        """Test that unqualified names are unchanged without '~'."""
        self.assertEqual(format_type("MyType"), "MyType")
        self.assertEqual(format_type("MyType", force_short_name=False), "MyType")

if __name__ == '__main__':
    unittest.main()