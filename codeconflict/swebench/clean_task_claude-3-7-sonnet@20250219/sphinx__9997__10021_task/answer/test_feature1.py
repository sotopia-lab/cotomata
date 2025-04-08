import unittest
from typing import List, Dict, Tuple, Optional, Union, Any, Literal
from codebase import stringify_annotation, type_to_reference, parse_target


class TestParametrizedTypesLinks(unittest.TestCase):
    """Test that parametrized types from typing module are treated as objects not classes."""

    def test_parse_target_typing_types(self):
        """Test that typing module types are treated as object references."""
        reftype, target, _, _ = parse_target('typing.List')
        self.assertEqual(reftype, 'obj')
        self.assertEqual(target, 'typing.List')
        
        reftype, target, display_text, _ = parse_target('typing.List')
        self.assertEqual(display_text, 'List')
        
        reftype, target, _, _ = parse_target('typing.Dict')
        self.assertEqual(reftype, 'obj')
        
        reftype, target, _, _ = parse_target('typing.Optional')
        self.assertEqual(reftype, 'obj')
        
        reftype, target, _, _ = parse_target('typing.Union')
        self.assertEqual(reftype, 'obj')
    
    def test_parse_target_parametrized_types(self):
        """Test parsing parametrized types."""
        reftype, target, display_text, _ = parse_target('typing.List[int]')
        self.assertEqual(reftype, 'obj')
        self.assertEqual(target, 'typing.List[int]')
        self.assertEqual(display_text, 'List[int]')
        
        reftype, target, display_text, _ = parse_target('typing.Dict[str, int]')
        self.assertEqual(reftype, 'obj')
        self.assertEqual(display_text, 'Dict[str, int]')
    
    def test_parse_target_literal(self):
        """Test parsing Literal type, which was mentioned in the issue."""
        reftype, target, display_text, _ = parse_target('typing.Literal["a", "b"]')
        self.assertEqual(reftype, 'obj')
        self.assertEqual(display_text, 'Literal["a", "b"]')
    
    def test_type_to_reference(self):
        """Test that type_to_reference creates proper references."""
        ref = type_to_reference('typing.List')
        self.assertIn(':py:obj:', ref)
        self.assertIn('List', ref)
        
        ref = type_to_reference('typing.Dict[str, int]')
        self.assertIn(':py:obj:', ref)
        self.assertIn('Dict[str, int]', ref)
        
        # Test Literal type specifically
        ref = type_to_reference('typing.Literal["a", "b"]')
        self.assertIn(':py:obj:', ref)
        self.assertIn('Literal["a", "b"]', ref)
    
    def test_stringify_literal_type(self):
        """Test that Literal types are properly stringified."""
        if hasattr(__import__('typing'), 'Literal'):
            literal_type = Literal["a", "b"]
            result = stringify_annotation(literal_type)
            self.assertEqual(result, 'Literal["a", "b"]')
    
    def test_stringify_nested_types(self):
        """Test that nested types are properly stringified."""
        nested_type = Dict[str, List[Tuple[int, str]]]
        result = stringify_annotation(nested_type)
        # The exact format might vary, but should contain the nested structure
        self.assertIn('Dict', result)
        self.assertIn('List', result)
        self.assertIn('Tuple', result)
        self.assertIn('int', result)
        self.assertIn('str', result)


if __name__ == '__main__':
    unittest.main()