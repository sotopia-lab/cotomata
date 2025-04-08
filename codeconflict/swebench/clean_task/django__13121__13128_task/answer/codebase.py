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
            # If other is a timedelta, wrap it in a Value with DurationField
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
    
    def __rsub__(self, other):
        return self._combine(other, self.SUB, True)


class DurationExpression(Expression):
    """Expression for handling duration operations."""
    
    def __init__(self, lhs, connector, rhs, output_field=None):
        super().__init__(output_field=output_field or DurationField())
        self.lhs = lhs
        self.connector = connector
        self.rhs = rhs
    
    def resolve_expression(self, *args, **kwargs):
        c = self.copy()
        c.lhs = c.lhs.resolve_expression(*args, **kwargs)
        c.rhs = c.rhs.resolve_expression(*args, **kwargs)
        return c
    
    def copy(self):
        clone = self.__class__(self.lhs, self.connector, self.rhs, self.output_field)
        return clone
    
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
            expressions = []
            expression_params = []
            sql, params = self.compile(self.lhs, compiler, connection)
            expressions.append(sql)
            expression_params.extend(params)
            
            expressions.append(self.connector)
            
            sql, params = self.compile(self.rhs, compiler, connection)
            expressions.append(sql)
            expression_params.extend(params)
            
            return ' '.join(expressions), expression_params
        
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
        
        return ' '.join(expressions), expression_params


class TemporalSubtraction(Expression):
    """Expression for subtracting temporal types (dates, times, datetimes)."""
    
    def __init__(self, lhs, rhs, output_field=None):
        super().__init__(output_field=output_field or DurationField())
        self.lhs = lhs
        self.rhs = rhs
    
    def resolve_expression(self, *args, **kwargs):
        c = self.copy()
        c.lhs = c.lhs.resolve_expression(*args, **kwargs)
        c.rhs = c.rhs.resolve_expression(*args, **kwargs)
        return c
    
    def copy(self):
        clone = self.__class__(self.lhs, self.rhs, self.output_field)
        return clone
    
    def as_sql(self, compiler, connection):
        connection.ops.check_expression_support(self)
        lhs_sql, lhs_params = compiler.compile(self.lhs)
        rhs_sql, rhs_params = compiler.compile(self.rhs)
        return f'({lhs_sql}) - ({rhs_sql})', lhs_params + rhs_params


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
        lhs = self.lhs.resolve_expression(*args, **kwargs)
        rhs = self.rhs.resolve_expression(*args, **kwargs)
        
        if not isinstance(self, (DurationExpression, TemporalSubtraction)):
            try:
                lhs_type = lhs.output_field.get_internal_type()
            except (AttributeError, FieldError):
                lhs_type = None
            try:
                rhs_type = rhs.output_field.get_internal_type()
            except (AttributeError, FieldError):
                rhs_type = None
            
            # Handle duration and mixed type expressions
            if 'DurationField' in {lhs_type, rhs_type} and lhs_type != rhs_type:
                return DurationExpression(self.lhs, self.connector, self.rhs).resolve_expression(
                    *args, **kwargs
                )
            
            # Handle temporal subtraction
            datetime_fields = {'DateField', 'DateTimeField', 'TimeField'}
            if self.connector == self.SUB and lhs_type in datetime_fields and lhs_type == rhs_type:
                return TemporalSubtraction(self.lhs, self.rhs).resolve_expression(
                    *args, **kwargs
                )
                
        c = self.copy()
        c.lhs = lhs
        c.rhs = rhs
        return c
    
    def copy(self):
        clone = self.__class__(self.lhs, self.connector, self.rhs)
        clone.output_field = self.output_field
        return clone
    
    def as_sql(self, compiler, connection):
        expressions = []
        expression_params = []
        
        sql, params = compiler.compile(self.lhs)
        expressions.append(sql)
        expression_params.extend(params or [])
        
        expressions.append(self.connector)
        
        sql, params = compiler.compile(self.rhs)
        expressions.append(sql)
        expression_params.extend(params or [])
        
        return ' '.join(expressions), expression_params


# Make all expression classes combinable
F.__bases__ = (Combinable, Expression)
Value.__bases__ = (Combinable, Expression)
CombinedExpression.__bases__ = (Combinable, Expression)
DurationExpression.__bases__ = (Combinable, Expression)
TemporalSubtraction.__bases__ = (Combinable, Expression)