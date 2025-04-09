"""
A simplified module representing Django's expression handling for database operations.
This is a minimal representation to demonstrate the merge conflicts.
"""
import datetime
from decimal import Decimal


class FieldError(Exception):
    """Raised when there is an error with a model field."""
    pass


class Field:
    """Base field class"""
    def get_internal_type(self):
        return self.__class__.__name__


class DateTimeField(Field):
    """Field for storing datetime values"""
    pass


class DateField(Field):
    """Field for storing date values"""
    pass


class TimeField(Field):
    """Field for storing time values"""
    pass


class DurationField(Field):
    """Field for storing time duration values"""
    pass


class DatabaseFeatures:
    """Database backend features"""
    def __init__(self):
        self.has_native_duration_field = False
        self.supports_temporal_subtraction = True


class DatabaseOperations:
    """Database operations handler"""
    def check_expression_support(self, expression):
        """Checks if the database supports the given expression"""
        pass

    def format_for_duration_arithmetic(self, sql):
        """Format SQL for duration arithmetic"""
        return sql
    
    def convert_durationfield_value(self, value, expression, connection):
        """Convert duration field value from database"""
        try:
            return str(Decimal(value) / Decimal(1000000))
        except Exception as e:
            raise e


class Connection:
    """Database connection"""
    def __init__(self):
        self.features = DatabaseFeatures()
        self.ops = DatabaseOperations()


class Expression:
    """Base class for all query expressions"""
    def resolve_expression(self, query=None, allow_joins=True, reuse=None, 
                          summarize=False, for_save=False):
        """Resolve expression into something the database can handle"""
        return self
    
    def copy(self):
        """Return a copy of the expression"""
        return self.__class__()
    
    def output_field(self):
        """Return the field that represents the output of this expression"""
        return None

    def as_sql(self, compiler, connection):
        """Return the SQL and parameters for this expression"""
        raise NotImplementedError("Subclasses must implement as_sql()")


class Combinable:
    """Methods for combining expressions"""
    ADD = '+'
    SUB = '-'
    
    def _combine(self, other, connector, reversed):
        """Combine this expression with another expression"""
        if not hasattr(other, 'resolve_expression'):
            # everything must be resolvable to an expression
            output_field = (
                DurationField()
                if isinstance(other, datetime.timedelta) else
                None
            )
            other = Value(other, output_field=output_field)
            
        if reversed:
            return CombinedExpression(other, connector, self)
        else:
            return CombinedExpression(self, connector, other)
    
    def __add__(self, other):
        return self._combine(other, self.ADD, False)
    
    def __sub__(self, other):
        return self._combine(other, self.SUB, False)
    
    def __radd__(self, other):
        return self._combine(other, self.ADD, True)
    
    def __rsub__(self, other):
        return self._combine(other, self.SUB, True)


class Value(Expression, Combinable):
    """Represents a wrapped value as a query expression"""
    def __init__(self, value, output_field=None):
        self.value = value
        self._output_field = output_field
    
    @property
    def output_field(self):
        return self._output_field
    
    def as_sql(self, compiler, connection):
        connection.ops.check_expression_support(self)
        return "%s", [self.value]


class F(Expression, Combinable):
    """Reference to a model field"""
    def __init__(self, name):
        self.name = name
        self._output_field = None

    @property
    def output_field(self):
        return self._output_field
    
    def as_sql(self, compiler, connection):
        return "%s", [self.name]


class DurationExpression(Expression, Combinable):
    """An expression that deals with duration arithmetic"""
    def __init__(self, lhs, connector, rhs):
        self.lhs = lhs
        self.connector = connector
        self.rhs = rhs
        self.is_summary = False
    
    def compile(self, side, compiler, connection):
        try:
            output = side.output_field
        except (AttributeError, FieldError):
            pass
        else:
            if output and output.get_internal_type() == 'DurationField':
                sql, params = compiler.compile(side)
                return connection.ops.format_for_duration_arithmetic(sql), params
        return compiler.compile(side)
    
    def as_sql(self, compiler, connection):
        if connection.features.has_native_duration_field:
            # Fall back to regular combined expression behavior
            return CombinedExpression(self.lhs, self.connector, self.rhs).as_sql(compiler, connection)
            
        connection.ops.check_expression_support(self)
        expressions = []
        expression_params = []
        
        sql, params = self.compile(self.lhs, compiler, connection)
        expressions.append(sql)
        expression_params.extend(params)
        
        expressions.append(self.connector)
        
        sql, params = self.compile(self.rhs, compiler, connection)
        expressions.append(sql)
        expression_params.extend(params)
        
        expression_wrapper = '(%s)'
        sql = ' '.join(expressions)
        return expression_wrapper % sql, expression_params
    
    def resolve_expression(self, query=None, allow_joins=True, reuse=None, summarize=False, for_save=False):
        c = self.__class__(
            self.lhs.resolve_expression(query, allow_joins, reuse, summarize, for_save),
            self.connector,
            self.rhs.resolve_expression(query, allow_joins, reuse, summarize, for_save)
        )
        c.is_summary = summarize
        return c


class TemporalSubtraction(DurationExpression):
    """An expression that converts the subtraction of temporal fields to a duration"""
    def __init__(self, lhs, rhs):
        super().__init__(lhs, '-', rhs)
        self._output_field = DurationField()
    
    @property
    def output_field(self):
        return self._output_field


class CombinedExpression(Expression, Combinable):
    """Combines two expressions with a connector"""
    def __init__(self, lhs, connector, rhs):
        self.lhs = lhs
        self.connector = connector
        self.rhs = rhs
        self.is_summary = False
    
    def set_source_expressions(self, exprs):
        self.lhs, self.rhs = exprs
    
    def as_sql(self, compiler, connection):
        expressions = []
        expression_params = []
        
        sql, params = compiler.compile(self.lhs)
        expressions.append(sql)
        expression_params.extend(params)
        
        expressions.append(self.connector)
        
        sql, params = compiler.compile(self.rhs)
        expressions.append(sql)
        expression_params.extend(params)
        
        expression_wrapper = '(%s)'
        sql = ' '.join(expressions)
        return expression_wrapper % sql, expression_params
    
    def resolve_expression(self, query=None, allow_joins=True, reuse=None, summarize=False, for_save=False):
        lhs = self.lhs.resolve_expression(query, allow_joins, reuse, summarize, for_save)
        rhs = self.rhs.resolve_expression(query, allow_joins, reuse, summarize, for_save)
        
        if not isinstance(self, (DurationExpression, TemporalSubtraction)):
            try:
                lhs_type = lhs.output_field.get_internal_type()
            except (AttributeError, FieldError):
                lhs_type = None
                
            try:
                rhs_type = rhs.output_field.get_internal_type()
            except (AttributeError, FieldError):
                rhs_type = None
                
            # Handle Duration mixed type expressions
            if 'DurationField' in {lhs_type, rhs_type} and lhs_type != rhs_type:
                return DurationExpression(self.lhs, self.connector, self.rhs).resolve_expression(
                    query, allow_joins, reuse, summarize, for_save,
                )
                
            # Handle temporal subtraction
            datetime_fields = {'DateField', 'DateTimeField', 'TimeField'}
            if self.connector == self.SUB and lhs_type in datetime_fields and lhs_type == rhs_type:
                return TemporalSubtraction(self.lhs, self.rhs).resolve_expression(
                    query, allow_joins, reuse, summarize, for_save,
                )
                
        c = self.copy()
        c.is_summary = summarize
        c.lhs = lhs
        c.rhs = rhs
        return c


class ExpressionWrapper(Expression):
    """Wrapper for expressions with a specific output field"""
    def __init__(self, expression, output_field):
        self.expression = expression
        self._output_field = output_field
    
    @property
    def output_field(self):
        return self._output_field
    
    def as_sql(self, compiler, connection):
        return compiler.compile(self.expression)