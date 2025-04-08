# base/codebase.py
import typing
import collections # Using another standard module for contrast

class CustomClass:
    """A sample custom class."""
    pass

def format_typehint(hint: typing.Any) -> str:
    """
    Formats a type hint into a basic string representation, including module name.
    """
    origin = typing.get_origin(hint)
    args = typing.get_args(hint)

    if hint is None or hint is type(None):
        return "None"
    elif isinstance(hint, str): # Handle forward references as strings
        return hint
    elif origin: # Generic types like List[int], Dict[str, int]
        origin_name = f"{origin.__module__}.{origin.__name__}"
        if args:
            arg_strs = [format_typehint(arg) for arg in args]
            # Special case Optional[X] -> Union[X, NoneType]
            if origin is typing.Union and type(None) in args and len(args) == 2:
                 non_none_arg = next(a for a in args if a is not type(None))
                 return f"typing.Optional[{format_typehint(non_none_arg)}]" # Use Optional format
            return f"{origin_name}[{', '.join(arg_strs)}]"
        else:
            return origin_name
    elif hasattr(hint, '__module__') and hasattr(hint, '__name__'):
        # Basic types like int, str, or custom classes
        if hint.__module__ == 'builtins':
            return hint.__name__
        return f"{hint.__module__}.{hint.__name__}"
    else:
        return repr(hint) # Fallback

# Example usage (not part of the required execution)
# if __name__ == '__main__':
#     print(f"int -> {format_typehint(int)}")
#     print(f"List[int] -> {format_typehint(typing.List[int])}")
#     print(f"deque -> {format_typehint(collections.deque)}")
#     print(f"CustomClass -> {format_typehint(CustomClass)}")
#     print(f"Optional[str] -> {format_typehint(typing.Optional[str])}")
#     print(f"Union[int, str] -> {format_typehint(typing.Union[int, str])}")