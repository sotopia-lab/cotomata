import unittest
import datetime
from codebase import F, Value, DurationField, Connection, FieldError, CombinedExpression

# Mock objects for testing
class MockField:
    def __init__(self, field_type):
        self.field_type = field_type
        
    def get_internal_type(self):
        return self.field_type

class MockExpression:
    def __init__(self, output_field=None):
        self._output_field = output_field
        
    @property
    def output_field(self):
        if self._output_field is None:
            raise FieldError("No output field")
        return self._output_field
        
    def resolve_expression(self, *args, **kwargs):
        return self

class MockCompiler:
    def compile(self, expression):
        # Simple mock that returns a field name if it's an F expression
        if hasattr(expression, 'name'):
            return expression.name, []
        return "value", [expression.value] if hasattr(expression, 'value') else []

class TestDurationExpressions(unittest.TestCase):
    def setUp(self):
        self.connection = Connection()
        self.compiler = MockCompiler()
        
        # Mock F expression with DurationField
        self.duration_field = F('estimated_time')
        self.duration_field._output_field = MockField('DurationField')
        
        # Mock timedelta value
        self.delta = datetime.timedelta(days=1)
    
    def test_duration_plus_timedelta(self):
        """Test that F('duration_field') + timedelta works correctly"""
        # Create the expression: F('estimated_time') + timedelta(days=1)
        expression = self.duration_field + self.delta
        
        # Verify the expression is a CombinedExpression
        self.assertIsInstance(expression, CombinedExpression)
        
        # Verify that the right side is a Value with a DurationField output_field
        self.assertEqual(expression.rhs.value, self.delta)
        self.assertIsInstance(expression.rhs.output_field, DurationField)
        
        # Test resolving the expression (simulates what happens when the ORM processes it)
        resolved = expression.resolve_expression()
        
        # The result should be a DurationExpression after resolution
        from codebase import DurationExpression
        self.assertIsInstance(resolved, DurationExpression)
    
    def test_timedelta_plus_duration(self):
        """Test that timedelta + F('duration_field') works correctly (reversed order)"""
        # Create the expression: timedelta(days=1) + F('estimated_time')
        expression = self.delta + self.duration_field
        
        # Verify the expression is a CombinedExpression
        self.assertIsInstance(expression, CombinedExpression)
        
        # Verify that the left side is a Value with a DurationField output_field
        self.assertEqual(expression.lhs.value, self.delta)
        self.assertIsInstance(expression.lhs.output_field, DurationField)
        
        # Test resolving the expression
        resolved = expression.resolve_expression()
        
        # The result should be a DurationExpression after resolution
        from codebase import DurationExpression
        self.assertIsInstance(resolved, DurationExpression)
    
    def test_duration_expression_sql_generation(self):
        """Test SQL generation for duration expressions in non-native duration databases"""
        # Create the expression: F('estimated_time') + timedelta(days=1)
        expression = self.duration_field + self.delta
        
        # Resolve to get a DurationExpression
        resolved = expression.resolve_expression()
        
        # Get SQL from the expression
        sql, params = resolved.as_sql(self.compiler, self.connection)
        
        # Verify the expression formats correctly with format_for_duration_arithmetic
        # The expected format would be something like "(estimated_time + %s)" with params [timedelta]
        self.assertIn("estimated_time", sql)
        self.assertIn("+", sql)
        self.assertEqual(params, [self.delta])
        
    def test_duration_with_non_duration_expression(self):
        """Test mixing duration fields with non-duration values"""
        # Mock a non-duration field
        int_value = Value(42)
        
        # Create the expression: F('estimated_time') + 42
        expression = self.duration_field + int_value
        
        # Resolve to get a DurationExpression
        resolved = expression.resolve_expression()
        
        # Verify it's properly converted to a DurationExpression
        from codebase import DurationExpression
        self.assertIsInstance(resolved, DurationExpression)

if __name__ == '__main__':
    unittest.main()