import unittest
import datetime
from codebase import F, Value, DurationField, Connection, QueryCompiler

class TestDurationExpressions(unittest.TestCase):
    def setUp(self):
        self.compiler = QueryCompiler()
        self.connection = Connection(has_native_duration_field=False)
        
        # Mock field values for tests
        self.duration_field = F('estimated_time')
        self.duration_field.output_field = DurationField()
    
    def test_direct_duration_addition(self):
        """Test addition of duration field with timedelta value"""
        delta = datetime.timedelta(days=1)
        
        # Create expression: F('estimated_time') + timedelta(days=1)
        expression = self.duration_field + delta
        
        # Ensure expression is properly resolved
        resolved = expression.resolve_expression()
        
        # Check that proper handling for duration arithmetic is used
        self.assertEqual(resolved.__class__.__name__, 'DurationExpression')
        
        # Compile the SQL and check the result
        sql, params = resolved.as_sql(self.compiler, self.connection)
        
        # Assert SQL has the right format
        self.assertIn('estimated_time', sql)
        self.assertIn('+', sql)
    
    def test_duration_with_different_databases(self):
        """Test duration expressions with both native and non-native duration support"""
        delta = datetime.timedelta(hours=3)
        expression = self.duration_field + delta
        resolved = expression.resolve_expression()
        
        # Test with a database without native duration support
        non_native_conn = Connection(has_native_duration_field=False)
        sql_non_native, _ = resolved.as_sql(self.compiler, non_native_conn)
        self.assertIn('estimated_time', sql_non_native)
        
        # Test with a database that has native duration support
        native_conn = Connection(has_native_duration_field=True)
        sql_native, _ = resolved.as_sql(self.compiler, native_conn)
        self.assertIn('estimated_time', sql_native)
        
        # The SQL should be different based on database capabilities
        self.assertNotEqual(type(resolved).__name__, 'CombinedExpression')
        self.assertEqual(type(resolved).__name__, 'DurationExpression')
    
    def test_duration_value_handling(self):
        """Test that duration values are properly wrapped"""
        delta = datetime.timedelta(minutes=45)
        
        # Create an expression with a timedelta value
        expression = self.duration_field + delta
        resolved = expression.resolve_expression()
        
        # The right-hand side should be a Value with output_field=DurationField
        self.assertEqual(resolved.rhs.output_field.__class__.__name__, 'DurationField')

if __name__ == '__main__':
    unittest.main()