"""
Utilities for handling type annotations in Python docstrings.
"""


class TypeProcessor:
    """
    Process Python type annotations for display in documentation.
    """
    
    def __init__(self, use_full_names=True, unqualified_typehints=False):
        """
        Initialize TypeProcessor.
        
        Args:
            use_full_names: Whether to use fully qualified names (with module prefixes)
            unqualified_typehints: Whether to suppress module prefixes in type annotations
        """
        self.use_full_names = use_full_names
        self.unqualified_typehints = unqualified_typehints
    
    def format_type(self, type_name):
        """
        Format a type name for display in documentation.
        
        Args:
            type_name: The type name to format
            
        Returns:
            str: Formatted type name
        """
        # Feature 2: Support for unqualified type names
        if self.unqualified_typehints and '.' in type_name and not type_name.startswith(('.', '~')):
            # Keep only the class name part (after the last dot)
            return type_name.split('.')[-1]
            
        return type_name
    
    def get_crossref(self, target):
        """
        Generate a cross-reference for a type.
        
        Args:
            target: Target type to reference
            
        Returns:
            dict: Cross-reference information with reftype, reftarget, reftext, and optional
                 refspecific flag
        """
        refspecific = False
        reftext = target
        
        # Feature 1: Support for cross-reference specifiers
        if target.startswith('.'):
            # Relative reference (to current module)
            target = target[1:]
            reftext = target
            refspecific = True
        elif target.startswith('~'):
            # Shortened reference (only show the class name)
            target = target[1:]
            reftext = target.split('.')[-1]
        # Feature 2: Support for unqualified type names
        elif self.unqualified_typehints and '.' in target:
            reftext = target.split('.')[-1]
        
        return {
            'reftype': 'class',
            'reftarget': target,
            'reftext': reftext,
            'refspecific': refspecific
        }