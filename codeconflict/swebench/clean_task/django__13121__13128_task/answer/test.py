import unittest
import datetime
from codebase import (
    F, Value, Connection, DurationField, DateField, DateTimeField, TimeField, 
    FieldError, DurationExpression, TemporalSubtraction
)

class MockCompiler:
    def __init__(self):
        self.connection = Connection()
    
    def compile(self, expression):
        if isinstance(expression, F):
            return f"{expression.field_name}", []
        elif isinstance(expression, Value):
            return "%s", [expression.value]
        return "unknown", []

class TestFeatures(unittest.TestCase):
    def setUp(self):
        self.compiler = MockCompiler()
        self.connection = Connection()
        
        # Setup test values
        self.duration1 = datetime.timedelta(hours=2, minutes=30)
        self.duration2 = datetime.timedelta(hours=1, minutes=15)
        self.date1 = datetime.date(2023, 1, 1)
        self.date2 = datetime.date(2023, 1, 5)
        self.time1 = datetime.time(12, 30)
        self.time2 = datetime.time(15, 45)
        self.datetime1 = datetime.datetime(2023, 1, 1, 12, 30)
        self.datetime2 = datetime.datetime(2023, 1, 5, 15, 45)
        
    def test_feature1_duration_only_expression(self):
        """Test Feature 1: Duration-only expressions work properly."""
        # Setup F objects with duration fields
        estimated_time = F('estimated_time')
        estimated_time.output_field = DurationField()
        
        # Test adding a timedelta to a duration field
        expr = estimated_time + self.duration1
        
        # Verify the expression is a DurationExpression when resolved
        resolved_expr = expr.resolve_expression()
        self.assertIsInstance(resolved_expr, DurationExpression)
        
        # Check output_field is set correctly
        self.assertEqual(resolved_expr.output_field.get_internal_type(), 'DurationField')
        
        # Test the SQL generation
        sql, params = resolved_expr.as_sql(self.compiler, self.connection)
        self.assertEqual(params, [])  # No direct params in the duration SQL
        
        # Test with native duration field support
        self.connection.features.has_native_duration_field = True
        sql, params = resolved_expr.as_sql(self.compiler, self.connection)
        self.connection.features.has_native_duration_field = False  # Reset
        
    def test_feature2_temporal_subtraction_without_wrapper(self):
        """Test Feature 2: Temporal subtraction works without ExpressionWrapper."""
        # Setup F objects with temporal fields
        start = F('start')
        start.output_field = DateTimeField()
        end = F('end')
        end.output_field = DateTimeField()
        
        # Create a temporal subtraction expression
        expr = end - start
        
        # Verify the expression is resolved to a TemporalSubtraction
        resolved_expr = expr.resolve_expression()
        self.assertIsInstance(resolved_expr, TemporalSubtraction)
        
        # Check output_field is set automatically to DurationField
        self.assertEqual(resolved_expr.output_field.get_internal_type(), 'DurationField')
        
        # Test the SQL generation
        sql, params = resolved_expr.as_sql(self.compiler, self.connection)
        self.assertEqual(sql, "(end) - (start)")
        self.assertEqual(params, [])
        
    def test_combined_features(self):
        """Test both features working together."""
        # Setup fields
        start = F('start')
        start.output_field = DateTimeField()
        end = F('end')
        end.output_field = DateTimeField()
        estimated_time = F('estimated_time')
        estimated_time.output_field = DurationField()
        
        # Create a complex expression that uses both features
        temporal_diff = end - start  # Feature 2: Auto-resolved temporal subtraction
        complex_expr = temporal_diff + self.duration1  # Feature 1: Duration arithmetic
        
        # Resolve the expression
        resolved_expr = complex_expr.resolve_expression()
        
        # Test expression is of correct type and has correct output field
        self.assertEqual(resolved_expr.output_field.get_internal_type(), 'DurationField')
        
    def test_different_field_type_combinations(self):
        """Test that mixed field types trigger appropriate conversions."""
        # Test datetime - date (mixed types)
        datetime_field = F('datetime_field')
        datetime_field.output_field = DateTimeField()
        date_field = F('date_field')
        date_field.output_field = DateField()
        
        # This should be handled by DurationExpression
        expr = datetime_field - date_field
        resolved_expr = expr.resolve_expression()
        self.assertIsInstance(resolved_expr, DurationExpression)
        
        # Test duration + time (mixed types)
        duration_field = F('duration_field')
        duration_field.output_field = DurationField()
        time_field = F('time_field')
        time_field.output_field = TimeField()
        
        expr = duration_field + time_field
        resolved_expr = expr.resolve_expression()
        self.assertIsInstance(resolved_expr, DurationExpression)

if __name__ == '__main__':
    unittest.main()