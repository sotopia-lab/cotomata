import unittest
from codebase import Builder, ViewcodeAnchor, Node, doctree_read, process_viewcode_anchors, collect_pages

class TestViewcodeExtension(unittest.TestCase):
    """Test the viewcode extension functionality."""
    
    def setUp(self):
        """Set up common test fixtures."""
        self.doctree = Node()
    
    def test_feature1_epub_disabled_by_default(self):
        """Test that source pages are not generated for epub by default."""
        # Create an epub builder with default settings (viewcode_enable_epub = False)
        builder = Builder("epub")
        
        # Process the doctree
        doctree_read(builder, self.doctree)
        process_viewcode_anchors(builder, self.doctree)
        
        # Collect pages - there should be none for epub with default settings
        pages = list(collect_pages(builder))
        self.assertEqual(len(pages), 0, "No pages should be generated for epub by default")
        
        # Check that the source link was removed from the doctree
        self.assertEqual(len(self.doctree.children), 0, "Source link should be removed for unsupported builders")
    
    def test_feature1_epub_with_viewcode_enabled(self):
        """Test that source pages are generated for epub when viewcode is enabled."""
        # Create an epub builder with viewcode_enable_epub = True
        builder = Builder("epub")
        builder.env.config["viewcode_enable_epub"] = True
        
        # Process the doctree
        doctree_read(builder, self.doctree)
        process_viewcode_anchors(builder, self.doctree)
        
        # Collect pages - there should be one for the example module
        pages = list(collect_pages(builder))
        self.assertEqual(len(pages), 1, "Pages should be generated for epub when viewcode is enabled")
        
        # Check that the source link was retained in the doctree
        self.assertEqual(len(self.doctree.children), 1, "Source link should be retained for supported builders")
    
    def test_feature2_sequential_builds(self):
        """Test that viewcode links work correctly with sequential builds."""
        # First build with singlehtml (unsupported)
        singlehtml_builder = Builder("singlehtml")
        
        # Process the doctree
        doctree_read(singlehtml_builder, self.doctree)
        
        # Verify that a ViewcodeAnchor was added during doctree_read
        self.assertEqual(len(self.doctree.children), 1, "ViewcodeAnchor should be added regardless of builder")
        self.assertIsInstance(self.doctree.children[0], ViewcodeAnchor, "Child should be a ViewcodeAnchor")
        
        # Process anchors - they should be removed for singlehtml
        process_viewcode_anchors(singlehtml_builder, self.doctree)
        self.assertEqual(len(self.doctree.children), 0, "Anchors should be removed for unsupported builders")
        
        # No pages should be collected for singlehtml
        pages = list(collect_pages(singlehtml_builder))
        self.assertEqual(len(pages), 0, "No pages should be generated for singlehtml")
        
        # Now simulate another build with html (supported)
        html_builder = Builder("html")
        html_doctree = Node()
        
        # Process the doctree
        doctree_read(html_builder, html_doctree)
        
        # Verify that a ViewcodeAnchor was added during doctree_read
        self.assertEqual(len(html_doctree.children), 1, "ViewcodeAnchor should be added for html builder")
        self.assertIsInstance(html_doctree.children[0], ViewcodeAnchor, "Child should be a ViewcodeAnchor")
        
        # Process anchors - they should be converted to links for html
        process_viewcode_anchors(html_builder, html_doctree)
        self.assertEqual(len(html_doctree.children), 1, "Anchors should be converted to links for supported builders")
        self.assertIsInstance(html_doctree.children[0], Node, "Anchor should be converted to a regular Node")
        self.assertEqual(html_doctree.children[0].content, "[source]", "Converted node should contain [source]")
        
        # Pages should be collected for html
        pages = list(collect_pages(html_builder))
        self.assertEqual(len(pages), 1, "Pages should be generated for html")

if __name__ == "__main__":
    unittest.main()