import unittest
from answer.codebase import Calculator, Duration, UnsupportedOperandError

class TestFeature1DurationAddition(unittest.TestCase):

    def setUp(self):
        self.calculator = Calculator()

    def test_add_two_durations(self):
        """Test adding two Duration objects."""
        d1 = Duration(10)
        d2 = Duration(5)
        expected = Duration(15)
        result = self.calculator.add(d1, d2)
        self.assertEqual(result, expected, "Should correctly add two Durations")

    def test_add_duration_and_number_raises_error(self):
        """Test that adding a Duration and a number raises an error."""
        d1 = Duration(10)
        num = 5
        with self.assertRaisesRegex(UnsupportedOperandError, "Unsupported operand types for \+: 'Duration' and 'int'"):
            self.calculator.add(d1, num)
        with self.assertRaisesRegex(UnsupportedOperandError, "Unsupported operand types for \+: 'int' and 'Duration'"):
            self.calculator.add(num, d1)

    def test_add_duration_and_string_raises_error(self):
        """Test that adding a Duration and a string raises an error."""
        d1 = Duration(10)
        s = "hello"
        with self.assertRaisesRegex(UnsupportedOperandError, "Unsupported operand types for \+: 'Duration' and 'str'"):
            self.calculator.add(d1, s)

    def test_numeric_addition_still_works(self):
        """Ensure standard numeric addition is unaffected."""
        self.assertEqual(self.calculator.add(5, 3), 8)
        self.assertEqual(self.calculator.add(2.5, 1.5), 4.0)

if __name__ == '__main__':
    unittest.main()