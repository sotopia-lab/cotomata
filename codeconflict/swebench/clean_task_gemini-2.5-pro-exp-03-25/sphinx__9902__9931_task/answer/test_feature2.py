# answer/test_feature2.py
import unittest
from answer.formatter import format_type

class TestFeature2(unittest.TestCase):
    """Tests the global shortening feature (force_short_name flag)."""

    def test_force_shorten_qualified(self):
        """Test that force_short_name=True shortens a qualified name."""
        self.assertEqual(format_type("collections.deque", force_short_name=True), "deque")

    def test_force_shorten_unqualified(self):
        """Test that force_short_name=True doesn't change an unqualified name."""
        self.assertEqual(format_type("MyType", force_short_name=True), "MyType")

    def test_no_force_shorten(self):
        """Test that force_short_name=False doesn't shorten qualified names."""
        self.assertEqual(format_type("collections.deque", force_short_name=False), "collections.deque")
        # Check default behavior is False
        self.assertEqual(format_type("collections.deque"), "collections.deque")

    def test_interaction_tilde_and_force_shorten(self):
        """Test that force_short_name=True works even if tilde is present."""
        self.assertEqual(format_type("~collections.deque", force_short_name=True), "deque")

    def test_interaction_tilde_and_no_force_shorten(self):
        """Test that tilde still works correctly when force_short_name=False."""
        self.assertEqual(format_type("~collections.deque", force_short_name=False), "deque")


if __name__ == '__main__':
    unittest.main()