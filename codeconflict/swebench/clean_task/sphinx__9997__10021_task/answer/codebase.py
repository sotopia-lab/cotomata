"""
A simplified library to demonstrate Python type hints handling for documentation.

This module simulates a documentation tool's type hint processing capabilities.
"""
from typing import Any, Dict, List, Tuple, Optional, Union, Type, TypeVar, Callable

class TypeProcessor:
    """
    Process Python type hint annotations for documentation purposes.
    
    This class handles the conversion of type annotations to proper references
    in documentation.
    """
    
    def __init__(self, config=None):
        self.config = config or {}
    
    def format_type(self, annotation: Any) -> str:
        """
        Convert a type annotation to a string representation.
        
        Args:
            annotation: A type annotation from typing module or a regular class
            
        Returns:
            A string representation of the type
        """
        # Determine whether to use short form based on config
        mode = "smart" if self.config.get("unqualified_typehints") else "fully-qualified"
        return self.stringify(annotation, mode=mode)
    
    def stringify(self, annotation: Any, mode: str = "fully-qualified") -> str:
        """
        Convert a type annotation to a string.
        
        Args:
            annotation: A type annotation to convert
            mode: How to format the type names:
                - "fully-qualified": Include full module path (e.g., typing.List)
                - "smart": Use short names (e.g., List)
            
        Returns:
            String representation of the annotation
        """
        if annotation is None:
            return "None"
        
        module = getattr(annotation, "__module__", None)
        
        # Handle basic types
        if isinstance(annotation, str):
            return annotation
        elif annotation is type(None):
            return "None"
        
        # Handle typing module special cases
        if module == "typing":
            if hasattr(annotation, "__origin__"):
                # For parametrized types like List[int], Dict[str, int], etc.
                origin_str = self.stringify(annotation.__origin__, mode)
                
                # Remove typing. prefix in smart mode or for parametrized types
                if mode == "smart" or origin_str.startswith("typing."):
                    origin_str = origin_str.replace("typing.", "")
                
                if hasattr(annotation, "__args__"):
                    args = ", ".join(self.stringify(arg, mode) for arg in annotation.__args__)
                    return f"{origin_str}[{args}]"
                return origin_str
            else:
                # For non-parametrized types like Any, Callable, etc.
                name = getattr(annotation, "__name__", str(annotation))
                if mode == "smart":
                    return name
                else:
                    return f"typing.{name}"
        
        # Handle regular classes
        if hasattr(annotation, "__name__"):
            if module == "builtins":
                return annotation.__name__
            elif module:
                if mode == "smart":
                    return f"~{module}.{annotation.__name__}"
                else:
                    return f"{module}.{annotation.__name__}"
        
        # Fallback
        return str(annotation)
    
    def create_cross_reference(self, type_str: str) -> str:
        """
        Create a cross-reference link for a type.
        
        Args:
            type_str: String representation of a type
            
        Returns:
            Cross-reference link for documentation
        """
        # Parse the type string to get the right reference type and target
        reftype, target, display = self.parse_type_target(type_str)
        
        # Create the reference with appropriate styling
        return f":{reftype}:`{display} <{target}>`"
    
    def parse_type_target(self, type_str: str) -> tuple:
        """
        Parse a type string to extract reference information.
        
        Args:
            type_str: String representation of a type
            
        Returns:
            Tuple of (reference_type, target, display_text)
        """
        # Handle typing module special cases
        if type_str == "None" or type_str.startswith("typing."):
            ref_type = "obj"
        else:
            ref_type = "class"
        
        # Handle shortened display format
        if type_str.startswith("typing."):
            display = type_str[7:]  # Remove "typing." prefix for display
        elif type_str.startswith("~"):
            display = type_str.split(".")[-1]  # Take last part for shortened display
        else:
            display = type_str
            
        return ref_type, type_str, display
    
    def process_function_annotations(self, func: Callable) -> Dict[str, str]:
        """
        Process all annotations in a function for documentation.
        
        Args:
            func: A function with type annotations
            
        Returns:
            Dictionary with parameter names and their formatted type hints
        """
        import inspect
        
        # Determine format mode based on configuration
        mode = "smart" if self.config.get("unqualified_typehints") else "fully-qualified"
        
        result = {}
        try:
            sig = inspect.signature(func)
            for param_name, param in sig.parameters.items():
                if param.annotation is not param.empty:
                    result[param_name] = self.stringify(param.annotation, mode)
            
            if sig.return_annotation is not sig.empty:
                result["return"] = self.stringify(sig.return_annotation, mode)
        except (ValueError, TypeError):
            pass
            
        return result