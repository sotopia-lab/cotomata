import unittest
from answer.codebase import Calculator, Duration, UnsupportedOperandError

class TestFeature2RefactoringAndTypeError(unittest.TestCase):

    def setUp(self):
        self.calculator = Calculator()

    def test_numeric_addition(self):
        """Test basic numeric addition via dispatcher."""
        self.assertEqual(self.calculator.add(10, 5), 15)
        self.assertEqual(self.calculator.add(3.5, 2.5), 6.0)

    def test_numeric_subtraction(self):
        """Test basic numeric subtraction via dispatcher."""
        self.assertEqual(self.calculator.subtract(10, 5), 5)
        self.assertEqual(self.calculator.subtract(3.5, 2.5), 1.0)

    def test_add_incompatible_types_clear_error(self):
        """Test adding incompatible types raises specific error."""
        with self.assertRaisesRegex(UnsupportedOperandError, "Unsupported operand types for \+: 'int' and 'str'"):
            self.calculator.add(10, "5")
        with self.assertRaisesRegex(UnsupportedOperandError, "Unsupported operand types for \+: 'str' and 'float'"):
            self.calculator.add("hello", 2.0)

    def test_subtract_incompatible_types_clear_error(self):
        """Test subtracting incompatible types raises specific error."""
        with self.assertRaisesRegex(UnsupportedOperandError, "Unsupported operand types for -: 'int' and 'str'"):
            self.calculator.subtract(10, "5")
        # Test subtracting Durations (not supported)
        d1 = Duration(10)
        d2 = Duration(5)
        with self.assertRaisesRegex(UnsupportedOperandError, "Unsupported operand types for -: 'Duration' and 'Duration'"):
            self.calculator.subtract(d1, d2)
        with self.assertRaisesRegex(UnsupportedOperandError, "Unsupported operand types for -: 'int' and 'Duration'"):
            self.calculator.subtract(10, d2)


if __name__ == '__main__':
    unittest.main()