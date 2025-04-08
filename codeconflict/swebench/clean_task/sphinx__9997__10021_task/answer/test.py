"""
Unit tests for verifying the TypeProcessor class works correctly.
"""
import unittest
from typing import List, Dict, Optional, Union, Tuple, Any, Callable

from codebase import TypeProcessor

# Example functions with type annotations for testing
def example_func(x: int, y: str) -> bool:
    return bool(x) and bool(y)

def complex_func(
    items: List[Dict[str, Any]],
    callback: Optional[Callable[[int], str]] = None
) -> Tuple[int, Union[str, None]]:
    return (len(items), None)


class TestTypeProcessor(unittest.TestCase):
    """Test TypeProcessor functionality"""
    
    def test_basic_stringify(self):
        """Test basic type stringification"""
        processor = TypeProcessor()
        
        # Basic types
        self.assertEqual(processor.stringify(int), "int")
        self.assertEqual(processor.stringify(str), "str")
        self.assertEqual(processor.stringify(None), "None")
        
        # Typing module types
        self.assertEqual(processor.stringify(List), "typing.List")
        self.assertEqual(processor.stringify(Dict), "typing.Dict")
        self.assertEqual(processor.stringify(Optional), "typing.Optional")

    def test_parametrized_stringify(self):
        """Test stringification of parametrized types"""
        processor = TypeProcessor()
        
        # Simple parametrized types
        self.assertEqual(processor.stringify(List[int]), "typing.List[int]")
        self.assertEqual(processor.stringify(Dict[str, int]), "typing.Dict[str, int]")
        
        # Nested parametrized types
        self.assertEqual(
            processor.stringify(List[Dict[str, int]]), 
            "typing.List[typing.Dict[str, int]]"
        )
        
        # Union and Optional
        self.assertEqual(
            processor.stringify(Union[str, int]), 
            "typing.Union[str, int]"
        )
        self.assertEqual(
            processor.stringify(Optional[str]), 
            "typing.Optional[str]"
        )
        
    def test_unqualified_typehints(self):
        """Test unqualified (short) typehint formatting"""
        processor = TypeProcessor({"unqualified_typehints": True})
        
        # Basic typing types should have "typing." prefix removed
        self.assertEqual(processor.format_type(List), "List")
        self.assertEqual(processor.format_type(Dict), "Dict")
        
        # Parametrized types should also use short form
        self.assertEqual(processor.format_type(List[int]), "List[int]")
        self.assertEqual(processor.format_type(Dict[str, int]), "Dict[str, int]")
        
        # Nested types should be shortened at all levels
        self.assertEqual(
            processor.format_type(List[Dict[str, Optional[int]]]),
            "List[Dict[str, Optional[int]]]"
        )
    
    def test_cross_references(self):
        """Test generation of cross-references"""
        processor = TypeProcessor()
        
        # Basic cross-references for different types
        self.assertEqual(
            processor.create_cross_reference("int"),
            ":class:`int <int>`"
        )
        self.assertEqual(
            processor.create_cross_reference("typing.List"),
            ":obj:`List <typing.List>`"
        )
        
        # Test shortened display for typing module types
        self.assertEqual(
            processor.create_cross_reference("typing.Optional"),
            ":obj:`Optional <typing.Optional>`"
        )
    
    def test_function_annotations(self):
        """Test processing of function annotations"""
        # Test with default settings (fully qualified)
        processor = TypeProcessor()
        annotations = processor.process_function_annotations(example_func)
        
        self.assertEqual(annotations["x"], "int")
        self.assertEqual(annotations["y"], "str")
        self.assertEqual(annotations["return"], "bool")
        
        # Test with complex function and fully qualified types
        annotations = processor.process_function_annotations(complex_func)
        self.assertEqual(
            annotations["items"], 
            "typing.List[typing.Dict[str, typing.Any]]"
        )
        self.assertEqual(
            annotations["callback"], 
            "typing.Optional[typing.Callable[[int], str]]"
        )
        
        # Test with unqualified type hints
        processor = TypeProcessor({"unqualified_typehints": True})
        annotations = processor.process_function_annotations(complex_func)
        
        self.assertEqual(
            annotations["items"], 
            "List[Dict[str, Any]]"
        )
        self.assertEqual(
            annotations["callback"], 
            "Optional[Callable[[int], str]]"
        )
        
    def test_combined_features(self):
        """
        Test both features working together:
        1. Proper handling of parametrized types
        2. Unqualified type hints option
        """
        # Initialize processor with unqualified_typehints enabled
        processor = TypeProcessor({"unqualified_typehints": True})
        
        # Process a function with various typing.* annotations
        annotations = processor.process_function_annotations(complex_func)
        
        # Verify correct output format for each parameter
        self.assertEqual(
            annotations["items"], 
            "List[Dict[str, Any]]",
            "Parametrized types should be properly nested and use short form"
        )
        
        self.assertEqual(
            annotations["callback"], 
            "Optional[Callable[[int], str]]",
            "Optional and Callable should be properly handled with short form"
        )
        
        self.assertEqual(
            annotations["return"], 
            "Tuple[int, Union[str, None]]",
            "Return type should be formatted with short form"
        )
        
        # Test cross-reference generation with the combined features
        cross_ref = processor.create_cross_reference("typing.List[typing.Dict[str, int]]")
        self.assertEqual(
            cross_ref,
            ":obj:`List <typing.List[typing.Dict[str, int]]>`",
            "Cross-references should display short form but link to full form"
        )


if __name__ == "__main__":
    unittest.main()