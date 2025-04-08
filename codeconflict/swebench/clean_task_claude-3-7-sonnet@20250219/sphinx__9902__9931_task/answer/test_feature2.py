"""
Unit tests for Feature 2: Unqualified type hints configuration.
"""

import unittest
from codebase import type_to_xref, stringify_annotation, BuildEnvironment


class TestUnqualifiedTypeHints(unittest.TestCase):
    """Test the unqualified type hints functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.env = BuildEnvironment()
        self.env.config['autodoc_unqualified_typehints'] = True
    
    def test_suppress_prefix(self):
        """Test that module prefixes are suppressed when flag is set."""
        xref = type_to_xref("module.submodule.Type", suppress_prefix=True)
        self.assertEqual(xref.target, "module.submodule.Type")
        self.assertEqual(xref.text, "Type")
        self.assertFalse(xref.refspecific)
    
    def test_nested_module_prefix_suppression(self):
        """Test that deeply nested module prefixes are suppressed."""
        xref = type_to_xref("package.module.submodule.Class", suppress_prefix=True)
        self.assertEqual(xref.target, "package.module.submodule.Class")
        self.assertEqual(xref.text, "Class")
    
    def test_builtins_not_affected(self):
        """Test that builtin types are not affected."""
        xref = type_to_xref("int", suppress_prefix=True)
        self.assertEqual(xref.target, "int")
        self.assertEqual(xref.text, "int")
    
    def test_priority_with_special_prefixes(self):
        """Test that special prefixes take priority over suppress_prefix."""
        # Explicit ~ prefix should override suppress_prefix behavior
        xref = type_to_xref("~module.Type", suppress_prefix=True)
        self.assertEqual(xref.target, "module.Type")
        self.assertEqual(xref.text, "Type")
        
        # Local reference should override suppress_prefix behavior
        xref = type_to_xref(".OtherType", suppress_prefix=True)
        self.assertEqual(xref.target, "OtherType")
        self.assertEqual(xref.text, "OtherType")
        self.assertTrue(xref.refspecific)
    
    def test_stringify_annotation_unqualified(self):
        """Test the stringify_annotation function with unqualified=True."""
        class CustomType:
            __module__ = 'module'
            __name__ = 'CustomType'
        
        # With unqualified=False (default)
        result = stringify_annotation(CustomType)
        self.assertEqual(result, "module.CustomType")
        
        # With unqualified=True
        result = stringify_annotation(CustomType, unqualified=True)
        self.assertEqual(result, "CustomType")


if __name__ == '__main__':
    unittest.main()