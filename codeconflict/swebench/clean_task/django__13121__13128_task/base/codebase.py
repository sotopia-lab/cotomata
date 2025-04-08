import datetime
import decimal
from enum import Enum


class FieldError(Exception):
    """Exception raised when there's a problem with a model field."""
    pass


class Field:
    """Base field class for all model fields."""
    
    def __init__(self, output_field=None):
        self.output_field = output_field

    def get_internal_type(self):
        """Return the field's type."""
        return self.__class__.__name__


class DateField(Field):
    """Field to store date values."""
    pass


class DateTimeField(Field):
    """Field to store datetime values."""
    pass


class TimeField(Field):
    """Field to store time values."""
    pass


class DurationField(Field):
    """Field to store duration/timedelta values."""
    pass


class Expression:
    """Base class for all query expressions."""
    
    def __init__(self, output_field=None):
        self.output_field = output_field

    def resolve_expression(self, *args, **kwargs):
        return self

    def copy(self):
        clone = self.__class__()
        clone.output_field = self.output_field
        return clone


class F(Expression):
    """An object that represents a model field reference."""
    
    def __init__(self, field_name, output_field=None):
        super().__init__(output_field=output_field)
        self.field_name = field_name

    def copy(self):
        clone = self.__class__(self.field_name)
        clone.output_field = self.output_field
        return clone


class Value(Expression):
    """An expression that represents a fixed value."""
    
    def __init__(self, value, output_field=None):
        super().__init__(output_field=output_field)
        self.value = value
        
    def as_sql(self, compiler, connection):
        return '%s', [self.value]


class BaseDatabaseOperations:
    """Base database operations class."""
    
    def check_expression_support(self, expression):
        pass
    
    def date_interval_sql(self, timedelta):
        """
        Implement the date interval functionality for expressions.
        """
        raise NotImplementedError('subclasses of BaseDatabaseOperations may require a date_interval_sql() method')
    
    def convert_durationfield_value(self, value, expression, connection):
        """Convert duration values from the database to Python values."""
        if value is not None:
            value = str(decimal.Decimal(value) / decimal.Decimal(1000000))
        return value
    
    def format_for_duration_arithmetic(self, sql):
        """Format SQL for duration arithmetic operations."""
        return sql


class DatabaseFeatures:
    """Database backend features."""
    
    def __init__(self):
        self.has_native_duration_field = False
        self.supports_temporal_subtraction = True


class Connection:
    """Database connection."""
    
    def __init__(self):
        self.ops = BaseDatabaseOperations()
        self.features = DatabaseFeatures()
        

class Combinable:
    """Mixin that provides the ability to combine expressions."""
    
    ADD = '+'
    SUB = '-'
    MUL = '*'
    DIV = '/'
    
    def _combine(self, other, connector, reversed):
        if not hasattr(other, 'resolve_expression'):
            other = Value(other)
        
        if reversed:
            return CombinedExpression(other, connector, self)
        else:
            return CombinedExpression(self, connector, other)
    
    def __add__(self, other):
        return self._combine(other, self.ADD, False)
    
    def __sub__(self, other):
        return self._combine(other, self.SUB, False)
    
    def __rsub__(self, other):
        return self._combine(other, self.SUB, True)


class CombinedExpression(Expression):
    """Represents a combination of expressions with an operator."""
    
    ADD = '+'
    SUB = '-'
    MUL = '*'
    DIV = '/'
    
    def __init__(self, lhs, connector, rhs, output_field=None):
        super().__init__(output_field=output_field)
        self.lhs = lhs
        self.connector = connector
        self.rhs = rhs
        
    def resolve_expression(self, *args, **kwargs):
        c = self.copy()
        c.lhs = c.lhs.resolve_expression(*args, **kwargs)
        c.rhs = c.rhs.resolve_expression(*args, **kwargs)
        return c
    
    def copy(self):
        clone = self.__class__(self.lhs, self.connector, self.rhs)
        clone.output_field = self.output_field
        return clone
    
    def as_sql(self, compiler, connection):
        try:
            lhs_output = self.lhs.output_field
        except (AttributeError, FieldError):
            lhs_output = None
        try:
            rhs_output = self.rhs.output_field
        except (AttributeError, FieldError):
            rhs_output = None
            
        datetime_fields = {'DateField', 'DateTimeField', 'TimeField'}
        if (lhs_output and rhs_output and self.connector == self.SUB and
            lhs_output.get_internal_type() in datetime_fields and
            lhs_output.get_internal_type() == rhs_output.get_internal_type()):
            # Return temporal subtraction SQL
            connection.ops.check_expression_support(self)
            sql1, params1 = compiler.compile(self.lhs)
            sql2, params2 = compiler.compile(self.rhs)
            return f'({sql1}) - ({sql2})', params1 + params2
            
        # Standard expression SQL
        sql_parts = []
        params = []
        
        sql, param = compiler.compile(self.lhs)
        sql_parts.append(sql)
        params.extend(param or [])
        
        sql_parts.append(self.connector)
        
        sql, param = compiler.compile(self.rhs)
        sql_parts.append(sql)
        params.extend(param or [])
        
        return ' '.join(sql_parts), params


class DurationValue(Value):
    """A value representing a duration/timedelta."""
    
    def as_sql(self, compiler, connection):
        connection.ops.check_expression_support(self)
        if connection.features.has_native_duration_field:
            return super().as_sql(compiler, connection)
        return connection.ops.date_interval_sql(self.value), []


# Make all expression classes combinable
F.__bases__ = (Combinable, Expression)
Value.__bases__ = (Combinable, Expression)
CombinedExpression.__bases__ = (Combinable, Expression)