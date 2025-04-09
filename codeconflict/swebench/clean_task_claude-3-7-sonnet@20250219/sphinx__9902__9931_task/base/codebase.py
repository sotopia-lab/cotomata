"""
Utilities for handling type annotations in Python docstrings.
"""


class TypeProcessor:
    """
    Process Python type annotations for display in documentation.
    """
    
    def __init__(self, use_full_names=True):
        """
        Initialize TypeProcessor.
        
        Args:
            use_full_names: Whether to use fully qualified names (with module prefixes)
        """
        self.use_full_names = use_full_names
    
    def format_type(self, type_name):
        """
        Format a type name for display in documentation.
        
        Args:
            type_name: The type name to format
            
        Returns:
            str: Formatted type name
        """
        # Basic implementation that just returns the type name
        return type_name
    
    def get_crossref(self, target):
        """
        Generate a cross-reference for a type.
        
        Args:
            target: Target type to reference
            
        Returns:
            dict: Cross-reference information
        """
        return {
            'reftype': 'class',
            'reftarget': target,
            'reftext': target
        }