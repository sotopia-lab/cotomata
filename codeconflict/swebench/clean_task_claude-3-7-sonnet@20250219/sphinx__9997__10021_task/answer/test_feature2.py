import unittest
from typing import List, Dict, Tuple, Optional, Union, Any
from codebase import stringify_annotation, format_type_for_docs


class TestUnqualifiedTypeHints(unittest.TestCase):
    """Test the unqualified type hints functionality."""

    def test_stringify_in_smart_mode(self):
        """Test that smart mode produces unqualified type hints."""
        # Test basic types
        self.assertEqual(stringify_annotation(int, 'smart'), 'int')
        self.assertEqual(stringify_annotation(str, 'smart'), 'str')
        
        # Test typing module types
        self.assertEqual(stringify_annotation(List[int], 'smart'), 'List[int]')
        self.assertEqual(stringify_annotation(Dict[str, int], 'smart'), 'Dict[str, int]')
        self.assertEqual(stringify_annotation(Optional[int], 'smart'), 'Optional[int]')
        
        # Test nested types
        nested = List[Dict[str, Tuple[int, str]]]
        result = stringify_annotation(nested, 'smart')
        self.assertEqual(result, 'List[Dict[str, Tuple[int, str]]]')
    
    def test_stringify_in_fully_qualified_mode(self):
        """Test that fully qualified mode includes module names."""
        # Test typing module types
        self.assertEqual(stringify_annotation(List[int], 'fully-qualified'), 'typing.List[int]')
        self.assertEqual(stringify_annotation(Dict[str, int], 'fully-qualified'), 'typing.Dict[str, int]')
    
    def test_format_type_for_docs_unqualified(self):
        """Test that format_type_for_docs respects unqualified_typehints flag."""
        # With unqualified_typehints=False (default)
        self.assertEqual(format_type_for_docs(List[int]), 'List[int]')
        
        # With unqualified_typehints=True
        self.assertEqual(format_type_for_docs(List[int], unqualified_typehints=True), 'List[int]')
        
        # With field format and unqualified_typehints=True
        self.assertEqual(
            format_type_for_docs(List[int], doc_format='field', unqualified_typehints=True),
            '*List[int]*'
        )
    
    def test_complex_nested_types(self):
        """Test complex nested type annotations with unqualified hints."""
        complex_type = Dict[str, List[Optional[Union[int, str]]]]
        
        # Default mode
        default_result = stringify_annotation(complex_type)
        self.assertIn('Dict', default_result)
        self.assertIn('List', default_result)
        self.assertIn('Optional', default_result)
        self.assertIn('Union', default_result)
        
        # Smart mode (unqualified)
        smart_result = stringify_annotation(complex_type, 'smart')
        self.assertIn('Dict', smart_result)
        self.assertIn('List', smart_result)
        self.assertIn('Optional', smart_result)
        self.assertIn('Union', smart_result)
        
        # Format for documentation with unqualified hints
        doc_result = format_type_for_docs(complex_type, unqualified_typehints=True)
        self.assertIn('Dict', doc_result)
        self.assertIn('List', doc_result)
        self.assertIn('Optional', doc_result)
        self.assertIn('Union', doc_result)


if __name__ == '__main__':
    unittest.main()