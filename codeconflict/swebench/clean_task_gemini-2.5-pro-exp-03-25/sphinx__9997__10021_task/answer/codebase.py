# answer/codebase.py
import typing
import collections # Using another standard module for contrast

# --- Configuration ---
_config = {
    'use_short_names': False
}

def set_config(use_short_names: bool):
    """Sets the global configuration for type hint formatting."""
    global _config
    _config['use_short_names'] = use_short_names

def get_config():
    """Gets the current configuration."""
    return _config.copy()
# --- End Configuration ---

class CustomClass:
    """A sample custom class."""
    pass

def _get_type_name(hint: type, force_short_name: bool) -> str:
    """
    Helper function to determine the display name of a type based on configuration.
    Handles the core logic of Feature 1 and Feature 2 interaction.
    """
    module = getattr(hint, '__module__', None)
    name = getattr(hint, '__name__', None)

    if not name:
        return repr(hint) # Fallback if no name

    is_builtin = module == 'builtins'
    is_typing = module == 'typing'

    # Feature 2: If use_short_names is True, always return the short name.
    if force_short_name:
        return name
    # Feature 1 (as default behavior when not forcing short names):
    # Show short names for builtins and typing module types.
    elif is_builtin or is_typing:
        return name
    # Default: Show full name for other modules.
    else:
        return f"{module}.{name}"

def format_typehint(hint: typing.Any, use_short_names: bool = None) -> str:
    """
    Formats a type hint into a string, respecting the configuration.

    Args:
        hint: The type hint to format.
        use_short_names: Override the global config for this call.
                         If None, use the global config.
    """
    global _config
    if use_short_names is None:
        use_short_names = _config['use_short_names']

    origin = typing.get_origin(hint)
    args = typing.get_args(hint)

    if hint is None or hint is type(None):
        return "None"
    elif isinstance(hint, str): # Handle forward references as strings
        return hint
    elif origin: # Generic types like List[int], Dict[str, int], Optional[str]
        # Handle Optional[X] which is represented as Union[X, NoneType]
        is_optional = (origin is typing.Union and
                       type(None) in args and
                       len(args) == 2)

        if is_optional:
            origin_display_name = _get_type_name(typing.Optional, use_short_names)
            # Find the non-None argument
            non_none_arg = next(a for a in args if a is not type(None))
            arg_strs = [format_typehint(non_none_arg, use_short_names)]
        else:
            origin_display_name = _get_type_name(origin, use_short_names)
            arg_strs = [format_typehint(arg, use_short_names) for arg in args]

        if arg_strs:
            return f"{origin_display_name}[{', '.join(arg_strs)}]"
        else:
            # Handle cases like typing.List without args
            return origin_display_name
    elif isinstance(hint, type): # Basic types like int, str, or custom classes
         return _get_type_name(hint, use_short_names)
    else:
        # Fallback for things like Literals, TypeVars etc.
        # A real implementation would handle these more gracefully.
        return repr(hint)

# Example usage (not part of the required execution)
# if __name__ == '__main__':
#     print("--- Default Config (use_short_names=False) ---")
#     print(f"int -> {format_typehint(int)}")
#     print(f"List[int] -> {format_typehint(typing.List[int])}")
#     print(f"deque -> {format_typehint(collections.deque)}")
#     print(f"CustomClass -> {format_typehint(CustomClass)}")
#     print(f"Optional[str] -> {format_typehint(typing.Optional[str])}")
#     print(f"Union[int, str] -> {format_typehint(typing.Union[int, str])}")

#     set_config(use_short_names=True)
#     print("\n--- Config (use_short_names=True) ---")
#     print(f"int -> {format_typehint(int)}")
#     print(f"List[int] -> {format_typehint(typing.List[int])}")
#     print(f"deque -> {format_typehint(collections.deque)}")
#     print(f"CustomClass -> {format_typehint(CustomClass)}")
#     print(f"Optional[str] -> {format_typehint(typing.Optional[str])}")
#     print(f"Union[int, str] -> {format_typehint(typing.Union[int, str])}")