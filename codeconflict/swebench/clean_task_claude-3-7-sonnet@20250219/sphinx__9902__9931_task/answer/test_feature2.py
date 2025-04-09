import unittest
from codebase import TypeProcessor

class TestFeature2(unittest.TestCase):
    """
    Test the unqualified type names feature.
    """
    
    def setUp(self):
        # Create processor with unqualified_typehints enabled
        self.processor = TypeProcessor(unqualified_typehints=True)
        # Create processor with unqualified_typehints disabled for comparison
        self.qualified_processor = TypeProcessor(unqualified_typehints=False)
    
    def test_unqualified_type_name(self):
        """Test that type names get simplified when unqualified_typehints is enabled."""
        # With unqualified_typehints=True, module prefixes should be removed
        self.assertEqual(self.processor.format_type("package.module.Type"), "Type")
        self.assertEqual(self.processor.format_type("typing.List"), "List")
        
        # With unqualified_typehints=False, full names should be preserved
        self.assertEqual(self.qualified_processor.format_type("package.module.Type"), "package.module.Type")
        self.assertEqual(self.qualified_processor.format_type("typing.List"), "typing.List")
    
    def test_crossref_with_unqualified_types(self):
        """Test that crossrefs display unqualified names but target full names."""
        result = self.processor.get_crossref("package.module.Type")
        
        # The reference target should still be the full name
        self.assertEqual(result['reftarget'], "package.module.Type")
        # But the display text should be the simplified name
        self.assertEqual(result['reftext'], "Type")
    
    def test_unqualified_doesnt_affect_simple_types(self):
        """Test that simple type names without dots aren't affected."""
        self.assertEqual(self.processor.format_type("Type"), "Type")
        self.assertEqual(self.processor.format_type("str"), "str")
        self.assertEqual(self.processor.format_type("int"), "int")
    
    def test_unqualified_preserves_prefix_notation(self):
        """Test that .Type and ~Type notation takes precedence over unqualified setting."""
        # Feature 1 notation takes precedence
        self.assertEqual(self.processor.format_type(".Type"), ".Type")
        self.assertEqual(self.processor.format_type("~package.Type"), "~package.Type")
        
        # Verify that crossref still handles these correctly
        dot_result = self.processor.get_crossref(".Type") 
        self.assertEqual(dot_result['reftarget'], "Type")
        self.assertEqual(dot_result['reftext'], "Type")
        self.assertTrue(dot_result['refspecific'])
        
        tilde_result = self.processor.get_crossref("~package.Type")
        self.assertEqual(tilde_result['reftarget'], "package.Type")
        self.assertEqual(tilde_result['reftext'], "Type")


if __name__ == "__main__":
    unittest.main()