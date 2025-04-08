"""
Tests for Feature 2: Consistent viewcode behavior across multiple builds
"""

import unittest
import os
import sys
import shutil
from pathlib import Path

# Add parent directory to path so we can import codebase
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from codebase import HTMLBuilder, SingleHTMLBuilder, viewcode_anchor, Node


class Feature2Test(unittest.TestCase):
    """Test cases for Feature 2: Consistent viewcode behavior."""
    
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
    
    def test_viewcode_anchors_preserved_in_document_tree(self):
        """Test that viewcode anchors are inserted in the document tree regardless of builder."""
        # Create a SingleHTML builder (not supported by viewcode)
        builder = SingleHTMLBuilder()
        
        # Collect modules - this will create document nodes
        builder.env._viewcode_modules = {}  # Ensure we start fresh
        builder.process_doctree()
        
        # Check that viewcode_anchor nodes were created during document reading
        has_viewcode_anchors = False
        for node in builder.env.document_nodes:
            if isinstance(node, Node):
                for child in list(node.children):
                    if isinstance(child, viewcode_anchor):
                        has_viewcode_anchors = True
                        break
                if has_viewcode_anchors:
                    break
        
        self.assertTrue(has_viewcode_anchors, "viewcode_anchor nodes should be created during document reading")
    
    def test_anchors_converted_for_html_builder(self):
        """Test that viewcode_anchor nodes are converted to source links for HTML builder."""
        # Create an HTML builder (supported by viewcode)
        builder = HTMLBuilder()
        
        # Process the document tree
        builder.prepare()
        
        # Check that document nodes have [source] text for HTML builder
        source_links = []
        for node in builder.env.document_nodes:
            if isinstance(node, object) and hasattr(node, 'children'):
                for child in node.children:
                    if hasattr(child, 'content') and child.content == "[source]":
                        source_links.append(child)
        
        self.assertGreater(len(source_links), 0, "[source] links should be present for HTML builder")
    
    def test_anchors_removed_for_singlehtml_builder(self):
        """Test that viewcode_anchor nodes are removed for SingleHTML builder."""
        # Create a SingleHTML builder (not supported by viewcode)
        builder = SingleHTMLBuilder()
        
        # Process the document tree
        builder.prepare()
        
        # Check that no document nodes have viewcode_anchor or [source] links
        has_anchors = False
        for node in builder.env.document_nodes:
            if isinstance(node, Node):
                for child in list(node.children):
                    if isinstance(child, viewcode_anchor) or (hasattr(child, 'content') and child.content == "[source]"):
                        has_anchors = True
                        break
                if has_anchors:
                    break
        
        self.assertFalse(has_anchors, "No viewcode_anchor nodes or [source] links should be present for SingleHTML builder")
    
    def test_sequential_builds_with_different_builders(self):
        """Test that sequential builds with different builders work correctly."""
        # First build with SingleHTML (not supported)
        single_builder = SingleHTMLBuilder()
        single_builder.build()
        
        # Save the document tree (simulating environment preservation between builds)
        document_tree = single_builder.env.document_nodes
        
        # Now build with HTML (supported)
        html_builder = HTMLBuilder()
        html_builder.env.document_nodes = document_tree
        html_builder.build()
        
        # Check that HTML builder generated source pages
        pages = []
        for modname in html_builder.env._viewcode_modules:
            pagename = os.path.join('_modules', modname.replace('.', '/'))
            pages.append(pagename)
        
        self.assertGreater(len(pages), 0, "Source pages should be generated for HTML builder after SingleHTML build")
        
        # Check that document nodes have [source] text for HTML builder
        source_links = []
        for node in html_builder.env.document_nodes:
            if isinstance(node, object) and hasattr(node, 'children'):
                for child in node.children:
                    if hasattr(child, 'content') and child.content == "[source]":
                        source_links.append(child)
        
        self.assertGreater(len(source_links), 0, "[source] links should be present for HTML builder after SingleHTML build")


if __name__ == "__main__":
    unittest.main()