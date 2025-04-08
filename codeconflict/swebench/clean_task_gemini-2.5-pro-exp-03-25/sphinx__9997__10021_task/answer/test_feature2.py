# answer/test_feature2.py
import unittest
import typing
import collections
from answer import codebase # Import the merged codebase

class TestFeature2(unittest.TestCase):
    """
    Tests Feature 2: All types are displayed using short names when
    the global 'use_short_names' config is True.
    """
    original_config = None

    @classmethod
    def setUpClass(cls):
        """Store original config and set for Feature 2 tests."""
        cls.original_config = codebase.get_config()
        codebase.set_config(use_short_names=True)

    @classmethod
    def tearDownClass(cls):
        """Restore original config after all tests."""
        if cls.original_config is not None:
            codebase.set_config(use_short_names=cls.original_config['use_short_names'])

    def test_typing_list_short(self):
        self.assertEqual(codebase.format_typehint(typing.List[int]), "List[int]")

    def test_typing_dict_short(self):
        # Now collections.deque should also be short
        self.assertEqual(codebase.format_typehint(typing.Dict[str, collections.deque]), "Dict[str, deque]")

    def test_typing_optional_short(self):
        self.assertEqual(codebase.format_typehint(typing.Optional[str]), "Optional[str]")

    def test_typing_union_short(self):
        self.assertEqual(codebase.format_typehint(typing.Union[int, collections.deque]), "Union[int, deque]")

    def test_non_typing_module_short(self):
        # collections.deque should now be short
        self.assertEqual(codebase.format_typehint(collections.deque), "deque")

    def test_custom_class_short(self):
        # Custom class should now be short
        self.assertEqual(codebase.format_typehint(codebase.CustomClass), "CustomClass")

    def test_builtin_types_short(self):
        # Builtins remain short
        self.assertEqual(codebase.format_typehint(int), "int")
        self.assertEqual(codebase.format_typehint(str), "str")
        self.assertEqual(codebase.format_typehint(type(None)), "None")

    def test_explicit_override_false(self):
         # Test overriding the global config for a single call
        self.assertEqual(codebase.format_typehint(collections.deque, use_short_names=False), "collections.deque")

    def test_explicit_override_true_when_global_is_false(self):
        # Temporarily set global to False and test override True
        codebase.set_config(use_short_names=False)
        self.assertEqual(codebase.format_typehint(collections.deque, use_short_names=True), "deque")
        # Set back for other tests in the class
        codebase.set_config(use_short_names=True)


if __name__ == '__main__':
    unittest.main()