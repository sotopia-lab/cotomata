"""
A simplified implementation of a viewcode extension for documentation builders.

This module demonstrates how source code references can be added to documentation.
"""

from typing import Dict, Any, Optional, List, Set, Tuple
import os

class Builder:
    """Base class for documentation builders."""
    
    def __init__(self, name='html', config=None):
        self.name = name
        self.config = config or {}
        self.env = Environment()
        self.outdir = "output"
    
    def build(self):
        """Build the documentation."""
        self.prepare()
        self.generate_pages()
        
    def prepare(self):
        """Prepare the build environment."""
        self.process_doctree()
        
    def process_doctree(self):
        """Process the document tree."""
        # In a real implementation, this would process a document tree
        # For our example, we'll just simulate collecting module information
        collect_modules(self)
    
    def generate_pages(self):
        """Generate output pages."""
        # In a real implementation, this would generate HTML or other format pages
        # For our example, we'll just simulate the process
        collect_pages(self)
        
    def get_relative_uri(self, from_path, to_path):
        """Get relative URI between two paths."""
        return os.path.join("_modules", to_path)


class HTMLBuilder(Builder):
    """HTML builder implementation."""
    
    def __init__(self, config=None):
        super().__init__('html', config)


class SingleHTMLBuilder(Builder):
    """Single HTML page builder implementation."""
    
    def __init__(self, config=None):
        super().__init__('singlehtml', config)


class EPUBBuilder(Builder):
    """EPUB builder implementation."""
    
    def __init__(self, config=None):
        super().__init__('epub', config)


class Environment:
    """Build environment to store document information."""
    
    def __init__(self):
        self._viewcode_modules = {}
        self.docname = "index"


class Node:
    """Base class for document tree nodes."""
    
    def __init__(self, content=""):
        self.content = content
        self.children = []
        self.parent = None
        self.attributes = {}
    
    def __iadd__(self, node):
        self.append(node)
        return self
    
    def append(self, node):
        """Add a child node."""
        self.children.append(node)
        node.parent = self


def collect_modules(builder):
    """
    Collect module information during document reading phase.
    
    This function simulates the process of extracting module information
    from a Python source file and storing it in the environment.
    """
    env = builder.env
    
    # Sample module data for demonstration
    module_data = {
        'spam.mod1': {
            'path': 'spam/mod1.py',
            'items': {
                'func1': ('function', 'index'),
                'Class1': ('class', 'index'),
            },
            'lines': [
                'def func1():',
                '    """Sample function."""',
                '    return True',
                '',
                'class Class1:',
                '    """Sample class."""',
                '    pass',
            ]
        }
    }
    
    env._viewcode_modules = module_data


def doctree_read(builder):
    """
    Process the document tree during the reading phase.
    
    In a real implementation, this would add source code links to
    the document tree for classes, functions, etc.
    """
    # In the real implementation, this function would add [source] links to
    # function and class definitions
    pass


def collect_pages(builder) -> List[Tuple[str, Dict[str, Any], str]]:
    """
    Generate source code pages for modules.
    
    In a real implementation, this would create HTML pages containing
    syntax-highlighted source code for each module.
    """
    env = builder.env
    
    if not hasattr(env, '_viewcode_modules'):
        return []
    
    # For demonstration purposes, we'll just print what would happen
    result = []
    for modname, data in env._viewcode_modules.items():
        pagename = os.path.join('_modules', modname.replace('.', '/'))
        print(f"Would generate page: {pagename}")
        
        # In a real implementation, this would create a page with
        # syntax-highlighted source code
        code = "\n".join(data['lines'])
        context = {
            'title': f"Source code for {modname}",
            'body': f"<pre>{code}<pre>"
        }
        result.append((pagename, context, 'module.html'))
    
    return result


def setup(app) -> Dict[str, Any]:
    """
    Set up the viewcode extension.
    
    This function registers the extension with the documentation application.
    """
    app.add_config_value('viewcode_enable_epub', False, 'html')
    return {
        'version': '1.0',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }