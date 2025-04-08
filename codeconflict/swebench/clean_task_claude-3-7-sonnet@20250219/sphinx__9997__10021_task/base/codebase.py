"""
A utility module for handling type annotations in documentation.

This module provides functionality to format and stringify Python type hints
for documentation systems.
"""

from typing import Any, Dict, List, Optional, Tuple, Union, TypeVar, get_type_hints
import inspect
import sys


def stringify_annotation(annotation, short_form=False) -> str:
    """
    Convert a type annotation to a string representation.
    
    Args:
        annotation: The type annotation to stringify
        short_form: If True, use the shorter form of the type name (e.g., 'List' instead of 'typing.List')
    
    Returns:
        A string representation of the type annotation
    """
    if annotation is None:
        return 'None'
    
    if isinstance(annotation, str):
        return annotation
    
    if short_form:
        # Return shorter form without module prefix
        module = getattr(annotation, '__module__', None)
        if module == 'typing':
            name = getattr(annotation, '__name__', str(annotation))
            return name.split('.')[-1]
    
    # Return fully qualified name
    if hasattr(annotation, '__origin__'):
        # Handle generic types like List[int]
        origin = annotation.__origin__.__name__
        args = annotation.__args__
        args_str = ', '.join(stringify_annotation(arg, short_form) for arg in args)
        return f"{origin}[{args_str}]"
    
    # Simple type
    return str(annotation)


def format_type_for_docs(annotation, doc_format='normal'):
    """
    Format a type annotation for inclusion in documentation.
    
    Args:
        annotation: The type annotation to format
        doc_format: The documentation format style ('normal' or 'field')
    
    Returns:
        A formatted string suitable for inclusion in documentation
    """
    type_str = stringify_annotation(annotation)
    
    if doc_format == 'field':
        # Format for field lists (e.g. :param x: description)
        return type_str
    else:
        # Default formatting
        return type_str


def type_to_reference(target: str, suppress_prefix: bool = False) -> str:
    """
    Convert a type string to a cross-reference format for documentation.
    
    Args:
        target: The type name to convert
        suppress_prefix: If True, suppress module prefix in the reference
    
    Returns:
        A string with proper cross-reference formatting
    """
    if target == 'None':
        reftype = 'obj'
    else:
        reftype = 'class'
    
    if suppress_prefix:
        text = target.split('.')[-1]
    else:
        text = target
    
    return f":py:{reftype}:`{text}`"