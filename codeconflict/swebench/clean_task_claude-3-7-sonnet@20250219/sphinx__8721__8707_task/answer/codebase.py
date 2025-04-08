"""
A simplified implementation of a viewcode extension for documentation builders.

This module demonstrates how source code references can be added to documentation.
"""

from typing import Dict, Any, Optional, List, Set, Tuple
import os

class viewcode_anchor(object):
    """Node for viewcode anchors.

    This node will be processed in the resolving phase.
    For viewcode supported builders, they will be all converted to the anchors.
    For not supported builders, they will be removed.
    """
    
    def __init__(self, reftarget="", refid="", refdoc=""):
        self.attributes = {
            'reftarget': reftarget,
            'refid': refid,
            'refdoc': refdoc
        }
        self.parent = None
    
    def __getitem__(self, key):
        return self.attributes[key]


class Builder:
    """Base class for documentation builders."""
    
    def __init__(self, name='html', config=None):
        self.name = name
        self.config = config or {}
        self.env = Environment()
        self.outdir = "output"
        self.format = name if name != 'singlehtml' else 'html'
    
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
        doctree_read(self)
        process_anchors(self)
    
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
        self.document_nodes = []  # Simplified representation of document nodes


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
        
    def remove(self, node):
        """Remove a child node."""
        if node in self.children:
            self.children.remove(node)
            node.parent = None
            
    def replace_self(self, node):
        """Replace this node with another node."""
        if self.parent:
            idx = self.parent.children.index(self)
            self.parent.children[idx] = node
            node.parent = self.parent
            self.parent = None


def is_supported_builder(builder):
    """Check if the builder supports viewcode."""
    if builder.format != 'html':
        return False
    elif builder.name == 'singlehtml':
        return False
    elif builder.name.startswith('epub') and not builder.config.get('viewcode_enable_epub', False):
        return False
    else:
        return True


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
    
    # Simulate creation of a document structure with function/class nodes
    create_demo_document_structure(builder)


def create_demo_document_structure(builder):
    """Create a demo document structure with function and class nodes."""
    env = builder.env
    
    # Create a simple document tree for demonstration
    root = Node("Document Root")
    
    # Add a function node
    func_node = Node("func1")
    
    # Add viewcode anchor for the function
    modname = "spam.mod1"
    pagename = os.path.join('_modules', modname.replace('.', '/'))
    anchor = viewcode_anchor(reftarget=pagename, refid="func1", refdoc=env.docname)
    func_node.append(anchor)
    
    # Add a class node
    class_node = Node("Class1")
    
    # Add viewcode anchor for the class
    anchor = viewcode_anchor(reftarget=pagename, refid="Class1", refdoc=env.docname)
    class_node.append(anchor)
    
    # Build the document tree
    root.append(func_node)
    root.append(class_node)
    
    # Store the document tree in the environment
    env.document_nodes = [root, func_node, class_node]


def doctree_read(builder):
    """
    Process the document tree during the reading phase.
    
    In a real implementation, this would add source code links to
    the document tree for classes, functions, etc.
    """
    # This is handled in collect_modules with the demo document structure
    pass


def process_anchors(builder):
    """
    Process viewcode_anchor nodes in the document tree.
    
    For supported builders, convert them to refnodes (anchors).
    For unsupported builders, remove them.
    """
    env = builder.env
    
    # Find all viewcode_anchor nodes in the document tree
    for node in env.document_nodes:
        if isinstance(node, Node):
            for child in list(node.children):
                if isinstance(child, viewcode_anchor):
                    if is_supported_builder(builder):
                        # Convert to a reference node
                        ref_node = Node("[source]")
                        ref_node.attributes = child.attributes.copy()
                        node.children[node.children.index(child)] = ref_node
                        ref_node.parent = node
                        print(f"Created [source] link for {child['refid']} in {builder.name} builder")
                    else:
                        # Remove the anchor
                        node.children.remove(child)
                        print(f"Removed [source] link for {child['refid']} in {builder.name} builder")


def collect_pages(builder) -> List[Tuple[str, Dict[str, Any], str]]:
    """
    Generate source code pages for modules.
    
    In a real implementation, this would create HTML pages containing
    syntax-highlighted source code for each module.
    """
    env = builder.env
    
    if not hasattr(env, '_viewcode_modules'):
        return []
    
    # Skip page generation for non-supported builders
    if not is_supported_builder(builder):
        print(f"Skipping source code page generation for {builder.name} builder")
        return []
    
    # For demonstration purposes, we'll just print what would happen
    result = []
    for modname, data in env._viewcode_modules.items():
        pagename = os.path.join('_modules', modname.replace('.', '/'))
        print(f"Would generate page: {pagename} for {builder.name} builder")
        
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