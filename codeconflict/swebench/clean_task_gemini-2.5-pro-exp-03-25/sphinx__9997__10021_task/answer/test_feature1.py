# answer/test_feature1.py
import unittest
import typing
import collections
from answer import codebase # Import the merged codebase

class TestFeature1(unittest.TestCase):
    """
    Tests Feature 1: `typing` module types are displayed without the prefix
    when the global 'use_short_names' config is False (default).
    """

    def setUp(self):
        """Ensure default configuration before each test."""
        codebase.set_config(use_short_names=False)

    def test_typing_list(self):
        self.assertEqual(codebase.format_typehint(typing.List), "List")

    def test_typing_list_with_arg(self):
        self.assertEqual(codebase.format_typehint(typing.List[int]), "List[int]")

    def test_typing_dict(self):
        self.assertEqual(codebase.format_typehint(typing.Dict), "Dict")

    def test_typing_dict_with_args(self):
        result = codebase.format_typehint(typing.Dict[str, collections.deque])
        # collections.deque should still have its module name
        self.assertEqual(result, "Dict[str, collections.deque]")

    def test_typing_optional(self):
        self.assertEqual(codebase.format_typehint(typing.Optional[str]), "Optional[str]")

    def test_typing_union(self):
        # Union itself should be shortened
        self.assertEqual(codebase.format_typehint(typing.Union[int, str]), "Union[int, str]")

    def test_non_typing_module(self):
        # Ensure types from other modules retain their prefix
        self.assertEqual(codebase.format_typehint(collections.deque), "collections.deque")

    def test_custom_class(self):
        # Ensure custom class retains its module prefix (answer.codebase in this case)
        expected_name = f"{codebase.CustomClass.__module__}.{codebase.CustomClass.__name__}"
        self.assertEqual(codebase.format_typehint(codebase.CustomClass), expected_name)

    def test_builtin_types(self):
        # Builtins should always be short
        self.assertEqual(codebase.format_typehint(int), "int")
        self.assertEqual(codebase.format_typehint(str), "str")
        self.assertEqual(codebase.format_typehint(type(None)), "None") # Check None formatting


if __name__ == '__main__':
    unittest.main()