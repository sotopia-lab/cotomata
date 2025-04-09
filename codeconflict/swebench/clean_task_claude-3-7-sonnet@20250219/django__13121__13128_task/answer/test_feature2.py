import unittest
import datetime
from codebase import F, Value, DateTimeField, TimeField, DateField, DurationField, Connection, TemporalSubtraction

# Mock objects for testing
class MockField:
    def __init__(self, field_type):
        self.field_type = field_type
        
    def get_internal_type(self):
        return self.field_type

class MockCompiler:
    def compile(self, expression):
        # Simple mock that returns a field name if it's an F expression
        if hasattr(expression, 'name'):
            return expression.name, []
        return "value", [expression.value] if hasattr(expression, 'value') else []

class TestTemporalSubtraction(unittest.TestCase):
    def setUp(self):
        self.connection = Connection()
        self.compiler = MockCompiler()
        
        # Mock F expressions with different temporal fields
        self.start_field = F('start')
        self.start_field._output_field = MockField('DateTimeField')
        
        self.end_field = F('end')
        self.end_field._output_field = MockField('DateTimeField')
        
        self.date_field = F('date')
        self.date_field._output_field = MockField('DateField')
        
        self.time_field = F('time')
        self.time_field._output_field = MockField('TimeField')
    
    def test_datetime_subtraction_auto_resolution(self):
        """Test that F('end') - F('start') auto-resolves to TemporalSubtraction with DurationField"""
        # Create expression: F('end') - F('start')
        expression = self.end_field - self.start_field
        
        # Resolve the expression
        resolved = expression.resolve_expression()
        
        # Verify it's converted to TemporalSubtraction
        self.assertIsInstance(resolved, TemporalSubtraction)
        
        # Verify the output field is DurationField
        self.assertIsInstance(resolved.output_field, DurationField)
    
    def test_date_subtraction_auto_resolution(self):
        """Test that F('date_field') - F('date_field') auto-resolves to TemporalSubtraction"""
        # Create expression with date fields
        expression = self.date_field - self.date_field
        
        # Resolve the expression
        resolved = expression.resolve_expression()
        
        # Verify it's converted to TemporalSubtraction
        self.assertIsInstance(resolved, TemporalSubtraction)
        
        # Verify the output field is DurationField
        self.assertIsInstance(resolved.output_field, DurationField)
    
    def test_time_subtraction_auto_resolution(self):
        """Test that F('time_field') - F('time_field') auto-resolves to TemporalSubtraction"""
        # Create expression with time fields
        expression = self.time_field - self.time_field
        
        # Resolve the expression
        resolved = expression.resolve_expression()
        
        # Verify it's converted to TemporalSubtraction
        self.assertIsInstance(resolved, TemporalSubtraction)
        
        # Verify the output field is DurationField
        self.assertIsInstance(resolved.output_field, DurationField)
    
    def test_datetime_subtraction_with_value(self):
        """Test subtraction with a datetime value"""
        # Create a datetime value
        dt_value = Value(datetime.datetime.now(), output_field=DateTimeField())
        
        # Create expression: F('start') - dt_value
        expression = self.start_field - dt_value
        
        # Resolve the expression
        resolved = expression.resolve_expression()
        
        # Verify it's converted to TemporalSubtraction
        self.assertIsInstance(resolved, TemporalSubtraction)
        
        # Verify the output field is DurationField
        self.assertIsInstance(resolved.output_field, DurationField)
    
    def test_mixed_temporal_fields_not_handled(self):
        """Test that mixing different temporal field types doesn't produce a TemporalSubtraction"""
        # Create expression with different field types: datetime - date
        expression = self.start_field - self.date_field
        
        # Resolve the expression
        resolved = expression.resolve_expression()
        
        # Verify it's NOT converted to TemporalSubtraction
        # Since they are different field types, it should remain a normal CombinedExpression
        from codebase import CombinedExpression
        self.assertIsInstance(resolved, CombinedExpression)
        self.assertNotIsInstance(resolved, TemporalSubtraction)

if __name__ == '__main__':
    unittest.main()