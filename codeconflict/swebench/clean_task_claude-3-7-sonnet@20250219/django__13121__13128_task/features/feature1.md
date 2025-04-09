# Feature 1: Support Duration-Only Expressions in SQLite and MySQL

Add support for duration field expressions like `F('duration_field') + timedelta(1)` to work correctly in database backends that don't have native duration field support (SQLite and MySQL).