"""
Unit tests for Feature 1: Properly Format Parametrized Types from the Typing Module.
"""

import unittest
from typing import Dict, List, Literal, Optional, Tuple, Union, Any

import codebase


class TestParametrizedTypesFormatting(unittest.TestCase):
    """Test cases for the proper formatting of parametrized types from typing module."""
    
    def test_simple_typing_types(self):
        """Test that simple typing types are properly formatted."""
        self.assertEqual(codebase.stringify_annotation(List), "List")
        self.assertEqual(codebase.stringify_annotation(Dict), "Dict")
        self.assertEqual(codebase.stringify_annotation(Optional), "Optional")
        
    def test_parametrized_types(self):
        """Test that parametrized types are properly formatted."""
        self.assertEqual(codebase.stringify_annotation(List[int]), "List[int]")
        self.assertEqual(codebase.stringify_annotation(Dict[str, int]), "Dict[str, int]")
        self.assertEqual(codebase.stringify_annotation(Optional[str]), "Optional[str]")
        
    def test_nested_parametrized_types(self):
        """Test that nested parametrized types are properly formatted."""
        self.assertEqual(
            codebase.stringify_annotation(List[Dict[str, int]]), 
            "List[Dict[str, int]]"
        )
        self.assertEqual(
            codebase.stringify_annotation(Dict[str, List[int]]), 
            "Dict[str, List[int]]"
        )
        
    def test_union_types(self):
        """Test that Union types are properly formatted."""
        self.assertEqual(
            codebase.stringify_annotation(Union[int, str]), 
            "Union[int, str]"
        )
        self.assertEqual(
            codebase.stringify_annotation(Union[int, None]), 
            "Union[int, None]"
        )
        
    def test_literal_type(self):
        """Test that Literal types are properly formatted."""
        try:
            self.assertEqual(
                codebase.stringify_annotation(Literal["a", "b"]), 
                "Literal['a', 'b']"
            )
        except (AttributeError, NameError):
            # Skip this test if Literal is not supported in this Python version
            pass
            
    def test_type_references(self):
        """Test that type references are properly created for typing types."""
        ref = codebase.create_type_reference("typing.List")
        self.assertEqual(ref["reftype"], "obj")  # Should be 'obj' not 'class'
        self.assertEqual(ref["reftarget"], "typing.List")
        self.assertEqual(ref["reftext"], "List")  # Module prefix removed
        
        # Test parametrized type
        ref = codebase.create_type_reference("typing.List[int]")
        self.assertEqual(ref["reftype"], "obj")
        self.assertEqual(ref["reftext"], "List[int]")
        
    def test_parse_type_target(self):
        """Test the parse_type_target function with typing module types."""
        reftype, target, title, specific = codebase.parse_type_target("typing.List")
        self.assertEqual(reftype, "obj")
        self.assertEqual(target, "typing.List")
        self.assertEqual(title, "List")
        self.assertFalse(specific)
        
        # Test with a suppress_prefix flag
        reftype, target, title, specific = codebase.parse_type_target("typing.Dict[str, int]", True)
        self.assertEqual(reftype, "obj")
        self.assertEqual(title, "Dict[str, int]")
        
        # Test with ~ prefix
        reftype, target, title, specific = codebase.parse_type_target("~typing.Optional[int]")
        self.assertEqual(target, "typing.Optional[int]")
        self.assertEqual(title, "Optional[int]")


if __name__ == '__main__':
    unittest.main()