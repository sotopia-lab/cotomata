# answer/calculator.py
import operator

class CalculatorError(Exception):
    """Base exception for calculator errors."""
    pass

class UnsupportedOperandError(CalculatorError, TypeError):
    """Raised when an operation involves unsupported types."""
    def __init__(self, op_symbol, type_a, type_b):
        # More specific error message
        message = (
            f"Unsupported operand types for {op_symbol}: "
            f"'{type_a.__name__}' and '{type_b.__name__}'"
        )
        super().__init__(message)
        self.op_symbol = op_symbol
        self.type_a = type_a
        self.type_b = type_b

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

class Calculator:
    """
    A simple calculator that can perform basic arithmetic operations.
    Supports numeric and Duration addition, and numeric subtraction.
    Uses a central dispatch method for operations.
    """

    def _dispatch_operation(self, a, b, op_func, op_symbol):
        """
        Checks types and performs the operation if supported.
        Raises UnsupportedOperandError otherwise.
        """
        # Feature 1 Logic: Handle Duration + Duration
        if op_symbol == '+' and isinstance(a, Duration) and isinstance(b, Duration):
            return Duration(op_func(a.seconds, b.seconds))

        # Original & Feature 2 Logic: Handle numeric operations
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            return op_func(a, b)

        # Feature 2 Logic: Raise specific error for unsupported types
        raise UnsupportedOperandError(op_symbol, type(a), type(b))

    def add(self, a, b):
        """
        Adds two operands. Supports numbers or two Durations.
        """
        # Feature 2 Refactoring: Delegate to dispatcher
        return self._dispatch_operation(a, b, operator.add, '+')

    def subtract(self, a, b):
        """
        Subtracts the second operand from the first. Supports only numbers.
        """
        # Feature 2 Refactoring: Delegate to dispatcher
        return self._dispatch_operation(a, b, operator.sub, '-')