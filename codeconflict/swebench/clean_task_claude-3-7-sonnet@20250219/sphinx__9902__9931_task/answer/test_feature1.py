"""
Unit tests for Feature 1: Support for cross-reference specifiers in type options.
"""

import unittest
from codebase import type_to_xref, BuildEnvironment


class TestCrossReferenceSpecifiers(unittest.TestCase):
    """Test the cross-reference specifiers functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.env = BuildEnvironment()
    
    def test_regular_type_reference(self):
        """Test normal type reference without specifiers."""
        xref = type_to_xref("module.Type", self.env)
        self.assertEqual(xref.target, "module.Type")
        self.assertEqual(xref.text, "module.Type")
        self.assertFalse(xref.refspecific)
    
    def test_local_specifier(self):
        """Test local reference specifier (.)."""
        xref = type_to_xref(".Type", self.env)
        self.assertEqual(xref.target, "Type")
        self.assertEqual(xref.text, "Type")
        self.assertTrue(xref.refspecific, "Local reference should have refspecific=True")
    
    def test_compact_specifier(self):
        """Test compact reference specifier (~)."""
        xref = type_to_xref("~module.submodule.Type", self.env)
        self.assertEqual(xref.target, "module.submodule.Type")
        self.assertEqual(xref.text, "Type")
        self.assertFalse(xref.refspecific)
    
    def test_nested_type_with_compact_specifier(self):
        """Test compact reference with nested type."""
        xref = type_to_xref("~package.module.Class", self.env)
        self.assertEqual(xref.target, "package.module.Class")
        self.assertEqual(xref.text, "Class")
        self.assertFalse(xref.refspecific)
    
    def test_none_type(self):
        """Test None type handling."""
        xref = type_to_xref("None", self.env)
        self.assertEqual(xref.target, "None")
        self.assertEqual(xref.text, "None")
        self.assertEqual(xref.reftype, "obj", "None should use 'obj' reftype")


if __name__ == '__main__':
    unittest.main()