# Feature 2: Auto-Resolve Mixed Temporal Type Expressions

Make temporal expressions with mixed types (such as datetime subtraction) work without requiring explicit `ExpressionWrapper` with `output_field=DurationField()`.