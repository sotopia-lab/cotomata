# answer/formatter.py
"""
A simple utility to format type strings, incorporating features for
explicit shortening and global shortening.
"""

def format_type(type_string: str, force_short_name: bool = False) -> str:
    """
    Formats a type string for display.

    Supports explicit shortening via '~' prefix and global shortening via flag.

    Args:
        type_string: The potentially qualified type string (e.g., "collections.deque", "~collections.deque").
        force_short_name: If True, always attempts to shorten the name.

    Returns:
        The formatted type string.
    """
    original_string = type_string
    explicitly_shorten = False

    # Feature 1: Check for explicit shorten request prefix '~'
    if type_string.startswith('~'):
        explicitly_shorten = True
        type_string = type_string[1:] # Remove the prefix for further processing

    # Determine if shortening should occur
    should_shorten = force_short_name or explicitly_shorten

    # Perform shortening if required
    if should_shorten and '.' in type_string:
        # Feature 2 logic (also used by Feature 1 when explicitly requested)
        return type_string.split('.')[-1]
    elif explicitly_shorten:
        # Handle case where ~ was used but no '.' exists (e.g., "~MyType")
        # Return the string without the tilde
        return type_string
    else:
        # Return the original string (without '~' if it was present but not shortening)
        # Or the unmodified string if no shortening conditions met
        return type_string # Return the processed string (tilde removed if applicable)

# answer/__init__.py (can be empty)