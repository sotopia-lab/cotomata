"""
A utility module for handling type annotations in documentation.

This module provides functionality to format and stringify Python type hints
for documentation systems.
"""

from typing import Any, Dict, List, Optional, Tuple, Union, TypeVar, get_type_hints
import inspect
import sys


def stringify_annotation(annotation, mode='fully-qualified-except-typing') -> str:
    """
    Convert a type annotation to a string representation.
    
    Args:
        annotation: The type annotation to stringify
        mode: The formatting mode to use:
            - 'fully-qualified-except-typing': Show the module name and qualified name of the annotation
              except the "typing" module.
            - 'smart': Show the name of the annotation without module prefixes.
            - 'fully-qualified': Show the module name and qualified name of the annotation.
    
    Returns:
        A string representation of the type annotation
    """
    if annotation is None:
        return 'None'
    
    if isinstance(annotation, str):
        return annotation
    
    # Determine module prefix based on mode
    if mode == 'smart':
        modprefix = '~'
    else:
        modprefix = ''
    
    module = getattr(annotation, '__module__', None)
    
    # Handle special case for typing module
    if module == 'typing':
        name = getattr(annotation, '__name__', str(annotation))
        if mode == 'smart' or mode == 'fully-qualified-except-typing':
            # Just return the name without 'typing.' prefix
            simple_name = name.split('.')[-1]
            
            # Handle generic types with arguments
            if hasattr(annotation, '__args__'):
                args = annotation.__args__
                args_str = ', '.join(stringify_annotation(arg, mode) for arg in args)
                return f"{simple_name}[{args_str}]"
            
            return simple_name
        else:  # fully-qualified
            # Include 'typing.' prefix
            if hasattr(annotation, '__args__'):
                args = annotation.__args__
                args_str = ', '.join(stringify_annotation(arg, mode) for arg in args)
                return f"typing.{simple_name}[{args_str}]"
            
            return f"typing.{simple_name}"
    
    # Handle generic types
    if hasattr(annotation, '__origin__'):
        origin = stringify_annotation(annotation.__origin__, mode)
        
        if hasattr(annotation, '__args__'):
            args = annotation.__args__
            args_str = ', '.join(stringify_annotation(arg, mode) for arg in args)
            return f"{origin}[{args_str}]"
    
    # Simple type
    if module and module != 'builtins' and module != '__builtin__':
        if mode == 'smart':
            return f"~{module}.{annotation.__name__}"
        else:
            return f"{module}.{annotation.__name__}"
    
    return str(annotation)


def parse_target(target: str, suppress_prefix: bool = False):
    """
    Parse a type string and return (reftype, target, display_text)
    
    Args:
        target: The type name to parse
        suppress_prefix: If True, suppress module prefix in the display text
    
    Returns:
        A tuple of (reftype, target, display_text)
    """
    refspecific = False
    
    # Handle special prefixes
    if target.startswith('.'):
        target = target[1:]
        display_text = target
        refspecific = True
    elif target.startswith('~'):
        target = target[1:]
        display_text = target.split('.')[-1]
    elif suppress_prefix:
        display_text = target.split('.')[-1]
    elif target.startswith('typing.'):
        display_text = target[7:]  # Remove 'typing.' prefix
    else:
        display_text = target
        
    # Determine reference type
    if target == 'None' or target.startswith('typing.'):
        # typing module provides non-class types, so use obj reference
        reftype = 'obj'
    else:
        reftype = 'class'
        
    return reftype, target, display_text, refspecific


def type_to_reference(target: str, suppress_prefix: bool = False) -> str:
    """
    Convert a type string to a cross-reference format for documentation.
    
    Args:
        target: The type name to convert
        suppress_prefix: If True, suppress module prefix in the reference
    
    Returns:
        A string with proper cross-reference formatting
    """
    reftype, target, display_text, _ = parse_target(target, suppress_prefix)
    
    return f":py:{reftype}:`{display_text} <{target}>`"


def format_type_for_docs(annotation, doc_format='normal', unqualified_typehints=False):
    """
    Format a type annotation for inclusion in documentation.
    
    Args:
        annotation: The type annotation to format
        doc_format: The documentation format style ('normal' or 'field')
        unqualified_typehints: If True, use shorter form of type names
    
    Returns:
        A formatted string suitable for inclusion in documentation
    """
    mode = 'smart' if unqualified_typehints else 'fully-qualified-except-typing'
    type_str = stringify_annotation(annotation, mode)
    
    if doc_format == 'field':
        # Format for field lists (e.g. :param x: description)
        return f"*{type_str}*"
    else:
        # Default formatting
        return type_str