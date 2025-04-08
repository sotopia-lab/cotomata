import datetime
from decimal import Decimal

class DurationField:
    """A field for storing duration values"""
    def __init__(self):
        self.name = None
    
    def get_internal_type(self):
        return 'DurationField'

class DateTimeField:
    """A field for storing datetime values"""
    def __init__(self):
        self.name = None
    
    def get_internal_type(self):
        return 'DateTimeField'

class FieldError(Exception):
    """Raised when a field operation is not valid"""
    pass

class Connection:
    """Represents a database connection"""
    def __init__(self, has_native_duration_field=False):
        self.features = ConnectionFeatures(has_native_duration_field)
        self.ops = DatabaseOperations()

class ConnectionFeatures:
    """Database features configuration"""
    def __init__(self, has_native_duration_field):
        self.has_native_duration_field = has_native_duration_field
        self.supports_temporal_subtraction = True

class DatabaseOperations:
    """Database operations handler"""
    def check_expression_support(self, expression):
        """Check if the expression is supported by the database"""
        pass
    
    def format_for_duration_arithmetic(self, sql):
        """Format SQL for duration arithmetic"""
        return sql

class Value:
    """Represents a constant value in a database expression"""
    def __init__(self, value, output_field=None):
        self.value = value
        self.output_field = output_field
    
    def resolve_expression(self, query=None, allow_joins=True, reuse=None, summarize=False, for_save=False):
        return self
    
    def as_sql(self, compiler, connection):
        if hasattr(self.value, 'as_sql'):
            return self.value.as_sql(compiler, connection)
        return '%s', [self.value]

class F:
    """Represents a model field reference in a database expression"""
    def __init__(self, name):
        self.name = name
        self.output_field = None  # This would be set at runtime based on the model field
    
    def resolve_expression(self, query=None, allow_joins=True, reuse=None, summarize=False, for_save=False):
        return self
    
    def as_sql(self, compiler, connection):
        return self.name, []
    
    def __add__(self, other):
        return CombinedExpression(self, '+', other)
    
    def __sub__(self, other):
        return CombinedExpression(self, '-', other)

class ExpressionWrapper:
    """A wrapper for database expressions that provides an output_field"""
    def __init__(self, expression, output_field):
        self.expression = expression
        self.output_field = output_field
    
    def resolve_expression(self, query=None, allow_joins=True, reuse=None, summarize=False, for_save=False):
        return ExpressionWrapper(
            self.expression.resolve_expression(query, allow_joins, reuse, summarize, for_save),
            self.output_field
        )
    
    def as_sql(self, compiler, connection):
        return self.expression.as_sql(compiler, connection)

class CombinedExpression:
    """Represents the combination of two expressions with an operation"""
    ADD = '+'
    SUB = '-'
    
    def __init__(self, lhs, connector, rhs):
        self.lhs = lhs
        self.connector = connector
        self.rhs = rhs
        self.output_field = None
    
    def resolve_expression(self, query=None, allow_joins=True, reuse=None, summarize=False, for_save=False):
        lhs = self.lhs.resolve_expression(query, allow_joins, reuse, summarize, for_save)
        rhs = self.rhs.resolve_expression(query, allow_joins, reuse, summarize, for_save)
        
        c = self.copy()
        c.is_summary = summarize
        c.lhs = lhs
        c.rhs = rhs
        return c
    
    def copy(self):
        return CombinedExpression(self.lhs, self.connector, self.rhs)
    
    def as_sql(self, compiler, connection):
        expressions = []
        expression_params = []
        
        sql, params = compiler.compile(self.lhs)
        expressions.append(sql)
        expression_params.extend(params)
        
        expressions.append(' %s ' % self.connector)
        
        sql, params = compiler.compile(self.rhs)
        expressions.append(sql)
        expression_params.extend(params)
        
        expression_wrapper = '(%s)'
        sql = expression_wrapper % ''.join(expressions)
        return sql, expression_params

class QueryCompiler:
    """Compiles database queries"""
    def compile(self, expression):
        return expression.as_sql(self, None)

def format_duration(duration):
    """Format a duration object for database representation"""
    return str(duration.total_seconds() * 1000000)