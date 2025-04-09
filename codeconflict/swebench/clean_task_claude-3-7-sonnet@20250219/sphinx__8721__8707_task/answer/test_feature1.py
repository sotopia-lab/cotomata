import unittest
from codebase import Application, Config, collect_pages

class Feature1Tests(unittest.TestCase):
    """Tests for Feature 1: EPUB module page generation only when enabled."""
    
    def test_epub_disabled_by_default(self):
        """Test that module pages are not generated for EPUB by default."""
        # Setup
        config = Config()
        self.assertFalse(config.viewcode_enable_epub)  # Verify default setting
        
        app = Application(builder_name="epub", config=config)
        app.builder.env._viewcode_modules = {"test_module": {"code": "def test(): pass"}}
        
        # Test
        pages = list(collect_pages(app))
        
        # Assert
        self.assertEqual(len(pages), 0, "No pages should be generated for EPUB when disabled")
    
    def test_epub_enabled_generates_pages(self):
        """Test that module pages are generated for EPUB when explicitly enabled."""
        # Setup
        config = Config()
        config.viewcode_enable_epub = True
        
        app = Application(builder_name="epub", config=config)
        app.builder.env._viewcode_modules = {"test_module": {"code": "def test(): pass"}}
        
        # Test
        pages = list(collect_pages(app))
        
        # Assert
        self.assertEqual(len(pages), 1, "Pages should be generated for EPUB when enabled")
        self.assertEqual(pages[0][0], "_modules/test_module", "Page name should match module name")
    
    def test_html_always_generates_pages(self):
        """Test that module pages are always generated for HTML regardless of EPUB setting."""
        # Setup with EPUB disabled
        config = Config()
        self.assertFalse(config.viewcode_enable_epub)
        
        app = Application(builder_name="html", config=config)
        app.builder.env._viewcode_modules = {"test_module": {"code": "def test(): pass"}}
        
        # Test
        pages = list(collect_pages(app))
        
        # Assert
        self.assertEqual(len(pages), 1, "Pages should be generated for HTML")
        
        # Setup with EPUB enabled
        config.viewcode_enable_epub = True
        app = Application(builder_name="html", config=config)
        app.builder.env._viewcode_modules = {"test_module": {"code": "def test(): pass"}}
        
        # Test
        pages = list(collect_pages(app))
        
        # Assert
        self.assertEqual(len(pages), 1, "Pages should still be generated for HTML")


if __name__ == "__main__":
    unittest.main()