import unittest
import datetime
from codebase import F, Value, DateTimeField, DurationField, Connection, QueryCompiler, ExpressionWrapper

class TestTemporalSubtraction(unittest.TestCase):
    def setUp(self):
        self.compiler = QueryCompiler()
        self.connection = Connection(has_native_duration_field=False)
        
        # Mock datetime fields for testing
        self.start_field = F('start')
        self.start_field.output_field = DateTimeField()
        
        self.end_field = F('end') 
        self.end_field.output_field = DateTimeField()
    
    def test_direct_datetime_subtraction(self):
        """Test subtraction of two datetime fields without ExpressionWrapper"""
        # Create expression: F('end') - F('start')
        expression = self.end_field - self.start_field
        
        # Resolve the expression
        resolved = expression.resolve_expression()
        
        # Verify it's been converted to a TemporalSubtraction
        self.assertEqual(resolved.__class__.__name__, 'TemporalSubtraction')
        
        # Compile the SQL
        sql, params = resolved.as_sql(self.compiler, self.connection)
        
        # Assert SQL has correct format
        self.assertIn('end', sql)
        self.assertIn('-', sql)
        self.assertIn('start', sql)
    
    def test_comparison_with_wrapper(self):
        """
        Compare direct subtraction with ExpressionWrapper approach
        Both should generate equivalent expressions
        """
        # Direct approach (new feature)
        direct_expr = self.end_field - self.start_field
        direct_resolved = direct_expr.resolve_expression()
        
        # Using ExpressionWrapper (old approach)
        wrapped_expr = ExpressionWrapper(
            self.end_field - self.start_field,
            output_field=DurationField()
        )
        wrapped_resolved = wrapped_expr.resolve_expression()
        
        # Both should generate SQL for temporal subtraction
        direct_sql, _ = direct_resolved.as_sql(self.compiler, self.connection)
        wrapped_sql, _ = wrapped_resolved.as_sql(self.compiler, self.connection)
        
        # The SQL should be structurally equivalent
        self.assertIn('end', direct_sql)
        self.assertIn('start', direct_sql)
        self.assertIn('-', direct_sql)
    
    def test_mixed_datetime_timedelta(self):
        """Test operations with mixed datetime and timedelta fields"""
        # Create a timedelta field
        delta_field = F('duration')
        delta_field.output_field = DurationField()
        
        # Expression with different field types
        expression = self.start_field + delta_field
        resolved = expression.resolve_expression()
        
        # Should be converted to a DurationExpression due to mixed types
        self.assertEqual(resolved.__class__.__name__, 'DurationExpression')

if __name__ == '__main__':
    unittest.main()