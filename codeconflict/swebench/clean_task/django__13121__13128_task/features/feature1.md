# Feature 1: Make Duration-only Expressions Work on all Database Backends

Enable expressions involving only DurationField objects (like adding a timedelta to a DurationField) to work consistently across all database backends, including SQLite and MySQL, by properly handling duration values in expressions.