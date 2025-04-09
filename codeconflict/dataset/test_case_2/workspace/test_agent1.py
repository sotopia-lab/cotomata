import unittest
from decimal import Decimal
from textual.widgets import Button
from calculator import CalculatorApp  # Assuming your calculator file is named calculator.py

class TestCalculator(unittest.TestCase):
    def setUp(self):
        """Set up a fresh calculator instance before each test."""
        self.calculator = CalculatorApp()
        
    def test_clear_state_management(self):
        """Test the clear state management feature."""
        # Test Case 1: Initial State
        self.assertTrue(self.calculator.show_ac)
        self.assertTrue(self.calculator.query_one("#ac").display)
        self.assertFalse(self.calculator.query_one("#c").display)
        
        # Test Case 2: After Number Input
        button = Button("1", id="number-1")
        self.calculator.number_pressed(Button.Pressed(button))
        self.assertFalse(self.calculator.show_ac)
        self.assertFalse(self.calculator.query_one("#ac").display)
        self.assertTrue(self.calculator.query_one("#c").display)
        
        # Test Case 3: C Button Press
        self.calculator.pressed_c()
        self.assertEqual(self.calculator.numbers, "0")
        self.assertEqual(self.calculator.value, "")
        self.assertEqual(self.calculator.left, Decimal("0"))  # Should preserve stored value
        
        # Test Case 4: AC Button Press
        self.calculator.pressed_ac()
        self.assertEqual(self.calculator.numbers, "0")
        self.assertEqual(self.calculator.value, "")
        self.assertEqual(self.calculator.left, Decimal("0"))
        self.assertEqual(self.calculator.right, Decimal("0"))
        self.assertEqual(self.calculator.operator, "plus")

    def test_decimal_point_handling(self):
        """Test the decimal point handling feature."""
        # Test Case 1: Single Decimal Point
        self.calculator.pressed_point()
        self.assertEqual(self.calculator.numbers, "0.")
        self.assertEqual(self.calculator.value, "0.")
        
        # Test Case 2: Multiple Decimal Points Attempt
        button5 = Button("5", id="number-5")
        self.calculator.number_pressed(Button.Pressed(button5))
        self.calculator.pressed_point()
        self.calculator.pressed_point()  # Second decimal attempt
        self.assertEqual(self.calculator.numbers, "0.5")
        self.assertEqual(self.calculator.value, "0.5")
        
        # Test Case 3: Decimal After Number
        self.calculator.pressed_ac()  # Reset
        button1 = Button("1", id="number-1")
        self.calculator.number_pressed(Button.Pressed(button1))
        self.calculator.pressed_point()
        self.calculator.number_pressed(Button.Pressed(button5))
        self.assertEqual(self.calculator.numbers, "1.5")
        self.assertEqual(self.calculator.value, "1.5")
        
        # Test Case 4: Decimal Precision in Calculations
        self.calculator.pressed_ac()  # Reset
        self.calculator.number_pressed(Button.Pressed(button1))
        self.calculator.pressed_point()
        self.calculator.number_pressed(Button.Pressed(button5))
        plus_button = Button("+", id="plus")
        self.calculator.pressed_op(Button.Pressed(plus_button))
        button2 = Button("2", id="number-2")
        self.calculator.number_pressed(Button.Pressed(button2))
        self.calculator.pressed_point()
        self.calculator.number_pressed(Button.Pressed(button5))
        self.calculator.pressed_equals()
        self.assertEqual(self.calculator.numbers, "4.0")

if __name__ == '__main__':
    unittest.main()