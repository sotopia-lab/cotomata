# base/calculator.py
import operator

class CalculatorError(Exception):
    """Base exception for calculator errors."""
    pass

class UnsupportedOperandError(CalculatorError, TypeError):
    """Raised when an operation involves unsupported types."""
    pass

class Calculator:
    """
    A simple calculator that can perform basic arithmetic operations.
    Initially supports only numeric addition and subtraction.
    """

    def _validate_numeric(self, *args):
        """Checks if all arguments are integers or floats."""
        for arg in args:
            if not isinstance(arg, (int, float)):
                return False
        return True

    def add(self, a, b):
        """Adds two numbers."""
        if self._validate_numeric(a, b):
            return a + b
        else:
            # Generic error, less informative
            raise UnsupportedOperandError(f"Unsupported operand types for +")

    def subtract(self, a, b):
        """Subtracts second number from the first."""
        if self._validate_numeric(a, b):
            return a - b
        else:
            # Generic error, less informative
            raise UnsupportedOperandError(f"Unsupported operand types for -")

# Example of a custom type we might want to support later
class Duration:
    """Represents a duration in seconds."""
    def __init__(self, seconds):
        if not isinstance(seconds, (int, float)):
            raise TypeError("Duration seconds must be numeric")
        self.seconds = seconds

    def __eq__(self, other):
        return isinstance(other, Duration) and self.seconds == other.seconds

    def __repr__(self):
        return f"Duration({self.seconds})"