import unittest
from codebase import (
    Application, Config, Node, viewcode_anchor, 
    doctree_read, ViewcodeAnchorTransform
)

class Feature2Tests(unittest.TestCase):
    """Tests for Feature 2: Improved anchor generation for viewcode links."""
    
    def test_viewcode_anchor_creation(self):
        """Test that viewcode_anchor nodes are created during doctree_read."""
        # Setup
        config = Config()
        app = Application(builder_name="html", config=config)
        
        # Create a simple document tree with a function node
        doctree = Node()
        func_node = Node(tagname='function', module='test_module', name='test_func')
        doctree.add_child(func_node)
        
        # Process the doctree
        doctree_read(app, doctree)
        
        # Check that a viewcode_anchor was added
        anchors = list(doctree.traverse(viewcode_anchor))
        self.assertEqual(len(anchors), 1, "One viewcode_anchor should be created")
        
        # Check anchor properties
        anchor = anchors[0]
        self.assertEqual(anchor['reftarget'], '_modules/test_module')
        self.assertEqual(anchor['refid'], 'test_func')
    
    def test_viewcode_anchor_conversion_for_supported_builder(self):
        """Test that viewcode_anchors are converted to links for supported builders."""
        # Setup
        config = Config()
        app = Application(builder_name="html", config=config)
        
        # Create a document with a viewcode_anchor
        doctree = Node()
        anchor = viewcode_anchor(
            reftarget='_modules/test_module',
            refid='test_func',
            refdoc='index'
        )
        doctree.add_child(anchor)
        
        # Apply the transform
        transform = ViewcodeAnchorTransform(app, doctree)
        transform.apply()
        
        # Check that the anchor was converted
        self.assertEqual(len(doctree.children), 1)
        refnode = doctree.children[0]
        
        # Check that it's no longer a viewcode_anchor
        self.assertNotIsInstance(refnode, viewcode_anchor)
        
        # Check reference properties
        self.assertEqual(refnode['reftype'], 'viewcode')
        self.assertEqual(refnode['reftarget'], '_modules/test_module')
        self.assertEqual(refnode['refid'], 'test_func')
        
        # Check that it has the [source] text
        self.assertEqual(len(refnode.children), 1)
        self.assertEqual(refnode.children[0].text, '[source]')
    
    def test_viewcode_anchor_removal_for_unsupported_builder(self):
        """Test that viewcode_anchors are removed for unsupported builders."""
        # Setup
        config = Config()
        app = Application(builder_name="singlehtml", config=config)
        
        # Create a document with a viewcode_anchor
        doctree = Node()
        anchor = viewcode_anchor(
            reftarget='_modules/test_module',
            refid='test_func',
            refdoc='index'
        )
        doctree.add_child(anchor)
        
        # Apply the transform
        transform = ViewcodeAnchorTransform(app, doctree)
        transform.apply()
        
        # Check that the anchor was removed
        self.assertEqual(len(doctree.children), 0, "Anchor should be removed for unsupported builder")
    
    def test_viewcode_anchor_removal_for_epub_when_disabled(self):
        """Test that viewcode_anchors are removed for EPUB when viewcode_enable_epub is False."""
        # Setup
        config = Config()
        config.viewcode_enable_epub = False
        app = Application(builder_name="epub", config=config)
        
        # Create a document with a viewcode_anchor
        doctree = Node()
        anchor = viewcode_anchor(
            reftarget='_modules/test_module',
            refid='test_func',
            refdoc='index'
        )
        doctree.add_child(anchor)
        
        # Apply the transform
        transform = ViewcodeAnchorTransform(app, doctree)
        transform.apply()
        
        # Check that the anchor was removed
        self.assertEqual(len(doctree.children), 0, "Anchor should be removed for EPUB when disabled")
    
    def test_viewcode_anchor_conversion_for_epub_when_enabled(self):
        """Test that viewcode_anchors are converted for EPUB when viewcode_enable_epub is True."""
        # Setup
        config = Config()
        config.viewcode_enable_epub = True
        app = Application(builder_name="epub", config=config)
        
        # Create a document with a viewcode_anchor
        doctree = Node()
        anchor = viewcode_anchor(
            reftarget='_modules/test_module',
            refid='test_func',
            refdoc='index'
        )
        doctree.add_child(anchor)
        
        # Apply the transform
        transform = ViewcodeAnchorTransform(app, doctree)
        transform.apply()
        
        # Check that the anchor was converted (not removed)
        self.assertEqual(len(doctree.children), 1, "Anchor should be converted for EPUB when enabled")


if __name__ == "__main__":
    unittest.main()