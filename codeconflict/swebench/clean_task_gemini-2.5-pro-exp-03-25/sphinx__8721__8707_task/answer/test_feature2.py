# answer/test_feature2.py
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


class TestFeature2SingleHTML(unittest.TestCase):
    """Tests the logic related to Feature 2 (skipping singlehtml)."""

    def test_singlehtml_skipped(self):
        """Verify singlehtml output is always skipped."""
        generator = OutputGenerator(builder_name="singlehtml")
        self.assertEqual(generator.generate(), "Output skipped for singlehtml",
                         "Should always skip singlehtml")

    def test_singlehtml_skipped_even_if_epub_enabled(self):
        """Verify singlehtml is skipped even if epub config is True (irrelevant)."""
        config = {'enable_epub': True}
        generator = OutputGenerator(builder_name="singlehtml", config=config)
        self.assertEqual(generator.generate(), "Output skipped for singlehtml",
                         "Should skip singlehtml regardless of other config")

    def test_html_still_generates(self):
        """Verify html output is still generated (unaffected by singlehtml skip)."""
        generator = OutputGenerator(builder_name="html")
        self.assertEqual(generator.generate(), "Output generated for html",
                         "HTML generation should be unaffected by singlehtml rule")

    def test_epub_enabled_still_generates(self):
        """Verify epub (when enabled) is unaffected by the singlehtml skip rule."""
        config = {'enable_epub': True}
        generator = OutputGenerator(builder_name="epub", config=config)
        self.assertEqual(generator.generate(), "Output generated for epub",
                         "Enabled EPUB generation should be unaffected by singlehtml rule")

    def test_epub_disabled_still_skipped(self):
        """Verify epub (when disabled) is still skipped (unaffected by singlehtml rule)."""
        config = {'enable_epub': False}
        generator = OutputGenerator(builder_name="epub", config=config)
        self.assertEqual(generator.generate(), "Output skipped for epub",
                         "Disabled EPUB skipping should be unaffected by singlehtml rule")


if __name__ == '__main__':
    # Allow running the test file directly
    unittest.main(module=__name__, exit=False)