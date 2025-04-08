"""
Sphinx utility module for handling type annotations in Python documentation.

This module provides functionality for converting Python type hints to 
cross-reference nodes in Sphinx documentation.
"""

from typing import List, Any, Optional, Dict, Union, Tuple


class BuildEnvironment:
    """Represents the Sphinx build environment."""
    
    def __init__(self):
        self.config = {
            'python_use_unqualified_type_names': False,
            'autodoc_unqualified_typehints': False
        }


class Node:
    """Base class for documentation nodes."""
    pass


class TextNode(Node):
    """Represents a text node in documentation."""
    
    def __init__(self, text: str):
        self.text = text
    
    def __str__(self) -> str:
        return self.text


class XRefNode(Node):
    """Represents a cross-reference node in documentation."""
    
    def __init__(self, target: str, text: str, reftype: str = 'class'):
        self.target = target
        self.text = text
        self.reftype = reftype
        self.refspecific = False
    
    def __str__(self) -> str:
        return f"XRef({self.text} -> {self.target})"


def type_to_xref(target: str, env: Optional[BuildEnvironment] = None, 
                suppress_prefix: bool = False) -> XRefNode:
    """Convert a type string to a cross reference node.
    
    Args:
        target: The target type string
        env: The build environment
        suppress_prefix: Whether to suppress module prefix in display
        
    Returns:
        A cross-reference node
    """
    if target == 'None':
        reftype = 'obj'
    else:
        reftype = 'class'
    
    # Handle special prefixes (Feature 1)
    refspecific = False
    if target.startswith('.'):
        target = target[1:]
        text = target
        refspecific = True
    elif target.startswith('~'):
        target = target[1:]
        text = target.split('.')[-1]
    elif suppress_prefix:  # Feature 2
        text = target.split('.')[-1]
    else:
        text = target
    
    # Create the XRefNode with proper settings
    node = XRefNode(target=target, text=text, reftype=reftype)
    node.refspecific = refspecific
    
    return node


def stringify_annotation(annotation: Any, unqualified: bool = False) -> str:
    """Stringify a type annotation object.
    
    Args:
        annotation: The type annotation to stringify
        unqualified: Whether to remove module prefixes
        
    Returns:
        String representation of the annotation
    """
    if isinstance(annotation, str):
        return annotation
    elif annotation is None:
        return 'None'
    elif hasattr(annotation, '__name__'):
        if annotation.__module__ == 'builtins' or unqualified:
            return annotation.__name__
        else:
            return f"{annotation.__module__}.{annotation.__name__}"
    else:
        return str(annotation)