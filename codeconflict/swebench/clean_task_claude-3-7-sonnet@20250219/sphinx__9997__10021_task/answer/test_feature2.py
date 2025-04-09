"""
Unit tests for Feature 2: Respect Unqualified Type Hints Setting in Description Mode.
"""

import unittest
from typing import Dict, List, Optional, Tuple, Union, Any

import codebase


class TestUnqualifiedTypeHints(unittest.TestCase):
    """Test cases for ensuring unqualified_typehints setting is respected."""
    
    def test_unqualified_mode(self):
        """Test the 'smart' mode which uses unqualified type names."""
        # Check basic types
        self.assertEqual(
            codebase.stringify_annotation(int, mode='smart'), 
            "int"
        )
        
        # Check typing module types
        self.assertEqual(
            codebase.stringify_annotation(List[int], mode='smart'), 
            "~typing.List[int]"
        )
        self.assertEqual(
            codebase.stringify_annotation(Dict[str, float], mode='smart'), 
            "~typing.Dict[str, float]"
        )
        
        # Check nested types
        self.assertEqual(
            codebase.stringify_annotation(Optional[List[int]], mode='smart'), 
            "~typing.Optional[~typing.List[int]]"
        )
        
    def test_fully_qualified_mode(self):
        """Test the 'fully-qualified' mode which includes all module prefixes."""
        # Check typing module types
        self.assertEqual(
            codebase.stringify_annotation(List[int], mode='fully-qualified'), 
            "typing.List[int]"
        )
        self.assertEqual(
            codebase.stringify_annotation(Dict[str, float], mode='fully-qualified'), 
            "typing.Dict[str, float]"
        )
        
    def test_default_mode(self):
        """Test the default mode ('fully-qualified-except-typing')."""
        # Check typing module types
        self.assertEqual(
            codebase.stringify_annotation(List[int]), 
            "List[int]"
        )
        self.assertEqual(
            codebase.stringify_annotation(Dict[str, float]), 
            "Dict[str, float]"
        )
        
    def test_type_formatter_respects_config(self):
        """Test that the TypeFormatter respects the unqualified_typehints config setting."""
        # Create formatter with unqualified_typehints=True
        formatter = codebase.TypeFormatter({"unqualified_typehints": True})
        
        # Process some typehints
        hints = {
            "param1": List[int],
            "param2": Dict[str, Any],
            "return": Optional[str]
        }
        
        processed = formatter.process_typehints(None, hints)
        
        # Check that all processed hints use the 'smart' mode
        self.assertEqual(processed["param1"], "~typing.List[int]")
        self.assertEqual(processed["param2"], "~typing.Dict[str, ~typing.Any]")
        self.assertEqual(processed["return"], "~typing.Optional[str]")
        
        # Create formatter with unqualified_typehints=False
        formatter = codebase.TypeFormatter({"unqualified_typehints": False})
        
        processed = formatter.process_typehints(None, hints)
        
        # Check that all processed hints use the 'fully-qualified' mode
        self.assertEqual(processed["param1"], "typing.List[int]")
        self.assertEqual(processed["param2"], "typing.Dict[str, typing.Any]")
        self.assertEqual(processed["return"], "typing.Optional[str]")


if __name__ == '__main__':
    unittest.main()