"""
Tests for Feature 1: EPUB support with configuration option
"""

import unittest
import os
import sys
import shutil
from pathlib import Path

# Add parent directory to path so we can import codebase
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from codebase import EPUBBuilder, collect_pages, setup


class Feature1Test(unittest.TestCase):
    """Test cases for Feature 1: EPUB support configuration."""
    
    def setUp(self):
        """Set up the test environment."""
        # Create temporary output directory
        output_dir = Path("test_output")
        if output_dir.exists():
            shutil.rmtree(output_dir)
        output_dir.mkdir()
        
    def tearDown(self):
        """Clean up after tests."""
        # Remove temporary output directory
        output_dir = Path("test_output")
        if output_dir.exists():
            shutil.rmtree(output_dir)
    
    def test_epub_disabled_by_default(self):
        """Test that EPUB source pages are disabled by default."""
        # Create an EPUB builder with default config
        builder = EPUBBuilder()
        
        # Prepare the builder
        builder.prepare()
        
        # Get pages that would be generated
        pages = collect_pages(builder)
        
        # Verify no pages are generated for EPUB by default
        self.assertEqual(len(pages), 0, "No source pages should be generated for EPUB by default")
    
    def test_epub_enabled_via_config(self):
        """Test that EPUB source pages can be enabled via configuration."""
        # Create an EPUB builder with viewcode_enable_epub set to True
        builder = EPUBBuilder(config={'viewcode_enable_epub': True})
        
        # Prepare the builder
        builder.prepare()
        
        # Get pages that would be generated
        pages = collect_pages(builder)
        
        # Verify pages are generated for EPUB when enabled
        self.assertGreater(len(pages), 0, "Source pages should be generated for EPUB when enabled")
        
        # Check that the module page is included
        page_paths = [page[0] for page in pages]
        self.assertIn('_modules/spam/mod1', page_paths, "Module page should be generated")
    
    def test_source_links_removed_for_epub_disabled(self):
        """Test that [source] links are removed when EPUB is disabled."""
        # Create an EPUB builder with default config (disabled)
        builder = EPUBBuilder()
        
        # Prepare the builder - this will process anchors
        builder.prepare()
        
        # Check that no document nodes have [source] text
        source_links = []
        for node in builder.env.document_nodes:
            if isinstance(node, object) and hasattr(node, 'children'):
                for child in node.children:
                    if hasattr(child, 'content') and child.content == "[source]":
                        source_links.append(child)
        
        self.assertEqual(len(source_links), 0, "No [source] links should be present when EPUB is disabled")
    
    def test_source_links_present_for_epub_enabled(self):
        """Test that [source] links are present when EPUB is enabled."""
        # Create an EPUB builder with viewcode_enable_epub set to True
        builder = EPUBBuilder(config={'viewcode_enable_epub': True})
        
        # Prepare the builder - this will process anchors
        builder.prepare()
        
        # Check that document nodes have [source] text
        source_links = []
        for node in builder.env.document_nodes:
            if isinstance(node, object) and hasattr(node, 'children'):
                for child in node.children:
                    if hasattr(child, 'content') and child.content == "[source]":
                        source_links.append(child)
        
        self.assertGreater(len(source_links), 0, "[source] links should be present when EPUB is enabled")


if __name__ == "__main__":
    unittest.main()