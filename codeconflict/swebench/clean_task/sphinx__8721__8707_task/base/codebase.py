"""
A simple viewcode extension that displays source code links in documentation.

This extension adds "[source]" links to functions and classes in the documentation,
allowing users to view the source code directly.
"""

from enum import Enum
from typing import List, Dict, Optional, Tuple, Any, Generator

class Builder:
    """Base builder class for documentation generators."""
    def __init__(self, name: str):
        self.name = name
        self.config = {}
        self.env = Environment()
        
    def build(self) -> None:
        """Build the documentation."""
        # Collect and process pages
        pages = list(collect_pages(self))
        
        # Generate output based on builder type
        print(f"Building with {self.name} builder")
        for page in pages:
            pagename, _, _ = page
            print(f"  - Generated page: {pagename}")

class Environment:
    """Environment for storing documentation data."""
    def __init__(self):
        self.docname = "index"
        self._viewcode_modules = {}
        self.config = {
            "viewcode_enable_epub": False
        }

class Node:
    """Base class for document nodes."""
    def __init__(self, content: str = ""):
        self.content = content
        self.children = []
        self.parent = None
        self.attributes = {}
    
    def add_child(self, child: 'Node') -> None:
        """Add a child node."""
        self.children.append(child)
        child.parent = self

def doctree_read(builder: Builder, doctree: Node) -> None:
    """Process a document tree, adding source links to function and class nodes."""
    env = builder.env
    if not hasattr(env, '_viewcode_modules'):
        env._viewcode_modules = {}
    
    # This is where we decide whether to add source links based on builder type
    if builder.name == "singlehtml":
        return
    if builder.name.startswith("epub") and not env.config.get("viewcode_enable_epub", False):
        return
    
    # Add source links to the doctree
    for node in get_nodes_with_source_links(doctree):
        modname = "example_module"
        fullname = "example_function"
        
        # Add a source link
        inline = Node("[source]")
        node.add_child(inline)
        
        # Record this module in the environment
        if modname not in env._viewcode_modules:
            env._viewcode_modules[modname] = {
                "docname": env.docname,
                "code": "def example_function():\n    return 'Hello, World!'",
                "tags": {fullname: env.docname}
            }

def get_nodes_with_source_links(doctree: Node) -> List[Node]:
    """Return a list of nodes that should have source links."""
    # This is a simplified version - in reality, we would identify specific node types
    return [doctree]

def collect_pages(builder: Builder) -> Generator[Tuple[str, Dict[str, Any], str], None, None]:
    """Collect pages to be included in the documentation output."""
    env = builder.env
    if not hasattr(env, '_viewcode_modules'):
        return
    
    # These checks determine if source pages should be generated at all
    if builder.name == "singlehtml":
        return
    if builder.name.startswith("epub") and not env.config.get("viewcode_enable_epub", False):
        return
    
    # Generate pages for each module
    for modname, modinfo in env._viewcode_modules.items():
        pagename = f"_modules/{modname}"
        yield pagename, {"title": f"Source code for {modname}"}, modinfo["code"]

def setup_extension(builder: Builder) -> None:
    """Set up the viewcode extension."""
    builder.env.config["viewcode_enable_epub"] = False