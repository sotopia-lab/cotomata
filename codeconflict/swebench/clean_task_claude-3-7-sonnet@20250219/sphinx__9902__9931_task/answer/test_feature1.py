import unittest
from codebase import TypeProcessor

class TestFeature1(unittest.TestCase):
    """
    Test the cross-reference specifier feature.
    """
    
    def setUp(self):
        self.processor = TypeProcessor()
    
    def test_normal_type_reference(self):
        """Test normal type reference without prefix."""
        result = self.processor.get_crossref("module.Type")
        self.assertEqual(result['reftarget'], "module.Type")
        self.assertEqual(result['reftext'], "module.Type")
        self.assertFalse(result.get('refspecific', False))
    
    def test_relative_type_reference(self):
        """Test relative type reference with dot prefix."""
        result = self.processor.get_crossref(".Type")
        self.assertEqual(result['reftarget'], "Type")
        self.assertEqual(result['reftext'], "Type")
        self.assertTrue(result['refspecific'])
    
    def test_shortened_type_reference(self):
        """Test shortened type reference with tilde prefix."""
        result = self.processor.get_crossref("~package.module.Type")
        self.assertEqual(result['reftarget'], "package.module.Type")
        self.assertEqual(result['reftext'], "Type")
        self.assertFalse(result.get('refspecific', False))
    
    def test_format_type_with_prefixes(self):
        """Test that format_type preserves prefixes for feature 1."""
        # The dot notation is preserved through format_type
        self.assertEqual(self.processor.format_type(".Type"), ".Type")
        # The tilde notation is preserved through format_type
        self.assertEqual(self.processor.format_type("~package.Type"), "~package.Type")


if __name__ == "__main__":
    unittest.main()