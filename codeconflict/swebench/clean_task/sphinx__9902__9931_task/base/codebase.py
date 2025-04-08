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
    
    def __init__(self, use_qualified_names=True):
        """
        Initialize the type handler.
        
        :param use_qualified_names: Whether to use fully qualified names for types
        """
        self.use_qualified_names = use_qualified_names
    
    def format_type_reference(self, target_type):
        """
        Format a type reference for documentation.
        
        :param target_type: The type to format
        :return: A formatted string representing the type
        """
        if target_type == 'None':
            return 'None'
        
        # If we don't use qualified names, extract the last part
        if not self.use_qualified_names and '.' in target_type:
            type_name = target_type.split('.')[-1]
        else:
            type_name = target_type
            
        return type_name
    
    def create_crossref(self, target_type):
        """
        Create a cross-reference for a type.
        
        :param target_type: The type to create a cross-reference for
        :return: A dictionary representing the cross-reference
        """
        if target_type == 'None':
            reftype = 'obj'
        else:
            reftype = 'class'
            
        # Format the type name for display
        display_text = self.format_type_reference(target_type)
        
        # Create the cross-reference
        ref = {
            'reftype': reftype,
            'reftarget': target_type,
            'reftext': display_text
        }
        
        return ref
    
    def process_type_annotation(self, type_annotation):
        """
        Process a type annotation string to create a cross-reference.
        
        :param type_annotation: The type annotation string
        :return: A cross-reference dictionary
        """
        return self.create_crossref(type_annotation)