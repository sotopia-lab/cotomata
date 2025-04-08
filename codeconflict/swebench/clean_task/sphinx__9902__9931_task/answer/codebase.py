"""
A simple Python documentation utility that processes type information
in docstrings to generate cross-references and type signatures.
"""

class TypeHandler:
    """
    Handles type annotations and references in documentation.
    
    This class provides utilities to process type annotations and
    create cross-references for documentation generation.
    """
    
    def __init__(self, use_qualified_names=True, unqualified_typehints=False):
        """
        Initialize the type handler.
        
        :param use_qualified_names: Whether to use fully qualified names for types
        :param unqualified_typehints: Whether to suppress module name prefixes 
                                      in type hints (overrides use_qualified_names)
        """
        self.use_qualified_names = use_qualified_names
        self.unqualified_typehints = unqualified_typehints
    
    def format_type_reference(self, target_type):
        """
        Format a type reference for documentation.
        
        :param target_type: The type to format
        :return: A formatted string representing the type
        """
        if target_type == 'None':
            return 'None'
        
        # Extract the display text for the type
        if target_type.startswith('.'):
            # Module-relative reference
            display_text = target_type[1:]
            is_relative = True
        elif target_type.startswith('~'):
            # Display only the class name, not the full path
            display_text = target_type[1:].split('.')[-1]
            is_relative = False
        elif self.unqualified_typehints:
            # Config setting to always display unqualified names
            display_text = target_type.split('.')[-1]
            is_relative = False
        elif not self.use_qualified_names and '.' in target_type:
            # For backward compatibility
            display_text = target_type.split('.')[-1]
            is_relative = False
        else:
            display_text = target_type
            is_relative = False
            
        return display_text, is_relative
    
    def create_crossref(self, target_type, suppress_prefix=False):
        """
        Create a cross-reference for a type.
        
        :param target_type: The type to create a cross-reference for
        :param suppress_prefix: Whether to suppress module name prefixes
        :return: A dictionary representing the cross-reference
        """
        if target_type == 'None':
            reftype = 'obj'
        else:
            reftype = 'class'
            
        # Handle special prefixes for reference specifiers
        actual_target = target_type
        refspecific = False
        
        if target_type.startswith('.'):
            # Module-relative reference
            actual_target = target_type[1:]
            refspecific = True
        elif target_type.startswith('~'):
            # Display only the class name, not the full path
            actual_target = target_type[1:]
            
        # Format the type name for display
        display_text, is_relative = self.format_type_reference(target_type)
        
        # Create the cross-reference
        ref = {
            'reftype': reftype,
            'reftarget': actual_target,
            'reftext': display_text,
            'refspecific': refspecific
        }
        
        return ref
    
    def process_type_annotation(self, type_annotation, suppress_prefix=False):
        """
        Process a type annotation string to create a cross-reference.
        
        :param type_annotation: The type annotation string
        :param suppress_prefix: Whether to suppress module name prefixes
        :return: A cross-reference dictionary
        """
        # Handle special notation in the annotation
        if type_annotation.startswith('~') or suppress_prefix or self.unqualified_typehints:
            return self.create_crossref(type_annotation, suppress_prefix=True)
        
        return self.create_crossref(type_annotation)