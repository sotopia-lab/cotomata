# answer/test_feature1.py
import unittest
import sys
import os

# Ensure 'answer' directory is in path to import codebase
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Adjust import based on whether the test is run from the root or 'answer' dir
try:
    from codebase import OutputGenerator
except ImportError:
    # If running from parent directory (e.g., using python -m unittest discover .)
    from answer.codebase import OutputGenerator


class TestFeature1EpubControl(unittest.TestCase):
    """Tests the logic related to Feature 1 (EPUB generation control)."""

    def test_epub_disabled_by_default(self):
        """Verify epub output is skipped when enable_epub is default (False)."""
        generator = OutputGenerator(builder_name="epub")
        self.assertEqual(generator.generate(), "Output skipped for epub",
                         "Should skip epub by default")

    def test_epub_disabled_explicitly(self):
        """Verify epub output is skipped when enable_epub is explicitly False."""
        config = {'enable_epub': False}
        generator = OutputGenerator(builder_name="epub", config=config)
        self.assertEqual(generator.generate(), "Output skipped for epub",
                         "Should skip epub when explicitly disabled")

    def test_epub_enabled(self):
        """Verify epub output is generated when enable_epub is True."""
        config = {'enable_epub': True}
        generator = OutputGenerator(builder_name="epub", config=config)
        self.assertEqual(generator.generate(), "Output generated for epub",
                         "Should generate epub when explicitly enabled")

    def test_html_unaffected_by_epub_config_false(self):
        """Verify html output is generated regardless of enable_epub being False."""
        config = {'enable_epub': False}
        generator = OutputGenerator(builder_name="html", config=config)
        self.assertEqual(generator.generate(), "Output generated for html",
                         "HTML generation should be unaffected by epub config (False)")

    def test_html_unaffected_by_epub_config_true(self):
        """Verify html output is generated regardless of enable_epub being True."""
        config = {'enable_epub': True}
        generator = OutputGenerator(builder_name="html", config=config)
        self.assertEqual(generator.generate(), "Output generated for html",
                         "HTML generation should be unaffected by epub config (True)")

if __name__ == '__main__':
    # Allow running the test file directly
    unittest.main(module=__name__, exit=False)