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
            'python_use_unqualified_type_names': False
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


def type_to_xref(target: str, env: Optional[BuildEnvironment] = None) -> XRefNode:
    """Convert a type string to a cross reference node.
    
    Args:
        target: The target type string
        env: The build environment
        
    Returns:
        A cross-reference node
    """
    if target == 'None':
        reftype = 'obj'
    else:
        reftype = 'class'
    
    text = target
    
    return XRefNode(target=target, text=text, reftype=reftype)


def stringify_annotation(annotation: Any) -> str:
    """Stringify a type annotation object.
    
    Args:
        annotation: The type annotation to stringify
        
    Returns:
        String representation of the annotation
    """
    if isinstance(annotation, str):
        return annotation
    elif annotation is None:
        return 'None'
    elif hasattr(annotation, '__name__'):
        if annotation.__module__ == 'builtins':
            return annotation.__name__
        else:
            return f"{annotation.__module__}.{annotation.__name__}"
    else:
        return str(annotation)