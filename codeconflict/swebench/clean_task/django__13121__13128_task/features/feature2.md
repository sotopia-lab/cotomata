# Feature 2: Enable Temporal Subtraction Without ExpressionWrapper

Allow temporal subtraction between date, time, and datetime fields without requiring an ExpressionWrapper to explicitly set the output_field as a DurationField, by automatically determining the appropriate output field type.