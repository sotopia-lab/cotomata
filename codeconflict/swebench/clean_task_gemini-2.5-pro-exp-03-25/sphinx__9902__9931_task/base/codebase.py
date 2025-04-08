# base/formatter.py
"""
A simple utility to format type strings.
"""

def format_type(type_string: str) -> str:
    """
    Formats a type string for display.

    Args:
        type_string: The potentially qualified type string (e.g., "collections.deque").

    Returns:
        The formatted type string.
    """
    # Base implementation simply returns the original string
    return type_string

# Create an empty __init__.py if needed for imports, though not strictly necessary for this simple example.
# base/__init__.py (can be empty)