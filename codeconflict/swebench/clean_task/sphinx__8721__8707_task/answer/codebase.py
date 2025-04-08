"""
A simple viewcode extension that displays source code links in documentation.

This extension adds "[source]" links to functions and classes in the documentation,
allowing users to view the source code directly.
"""

from enum import Enum
from typing import List, Dict, Optional, Tuple, Any, Generator

class ViewcodeAnchor(Node):
    """Node for viewcode anchors.
    
    This node will be processed in the resolving phase.
    For viewcode supported builders, they will be converted to anchors.
    For unsupported builders, they will be removed.
    """
    def __init__(self, reftarget: str, refid: str, refdoc: str):
        super().__init__()
        self.attributes = {
            "reftarget": reftarget,
            "refid": refid,
            "refdoc": refdoc
        }

class Builder:
    """Base builder class for documentation generators."""
    def __init__(self, name: str):
        self.name = name
        self.config = {}
        self.env = Environment()
        
    def build(self) -> None:
        """Build the documentation."""
        # First phase: process document tree
        doctree = Node()
        doctree_read(self, doctree)
        
        # Second phase: resolve viewcode anchors
        process_viewcode_anchors(self, doctree)
        
        # Third phase: collect and process pages
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
    
    def replace_self(self, new_node: 'Node') -> None:
        """Replace this node with a new node."""
        if self.parent:
            index = self.parent.children.index(self)
            self.parent.children[index] = new_node
            new_node.parent = self.parent
    
    def remove(self) -> None:
        """Remove this node from its parent."""
        if self.parent:
            self.parent.children.remove(self)
            self.parent = None

def is_supported_builder(builder: Builder) -> bool:
    """Check if the builder supports viewcode features."""
    if builder.name == "singlehtml":
        return False
    if builder.name.startswith("epub") and not builder.env.config.get("viewcode_enable_epub", False):
        return False
    return True

def doctree_read(builder: Builder, doctree: Node) -> None:
    """Process a document tree, adding source links to function and class nodes."""
    env = builder.env
    if not hasattr(env, '_viewcode_modules'):
        env._viewcode_modules = {}
    
    # Add viewcode anchors (regardless of builder type)
    for node in get_nodes_with_source_links(doctree):
        modname = "example_module"
        fullname = "example_function"
        pagename = f"_modules/{modname}"
        
        # Add a viewcode anchor that will be resolved later
        anchor = ViewcodeAnchor(
            reftarget=pagename,
            refid=fullname,
            refdoc=env.docname
        )
        node.add_child(anchor)
        
        # Record this module in the environment
        if modname not in env._viewcode_modules:
            env._viewcode_modules[modname] = {
                "docname": env.docname,
                "code": "def example_function():\n    return 'Hello, World!'",
                "tags": {fullname: env.docname}
            }

def process_viewcode_anchors(builder: Builder, doctree: Node) -> None:
    """Process viewcode anchors in the document tree.
    
    For supported builders, convert them to actual anchors.
    For unsupported builders, remove them.
    """
    def find_viewcode_anchors(node: Node) -> List[ViewcodeAnchor]:
        """Find all ViewcodeAnchor nodes in the tree."""
        anchors = []
        if isinstance(node, ViewcodeAnchor):
            anchors.append(node)
        for child in node.children:
            anchors.extend(find_viewcode_anchors(child))
        return anchors
    
    anchors = find_viewcode_anchors(doctree)
    
    if is_supported_builder(builder):
        # Convert anchors to actual source links for supported builders
        for anchor in anchors:
            inline = Node("[source]")
            # In a real implementation, we would create an actual link here
            anchor.replace_self(inline)
    else:
        # Remove anchors for unsupported builders
        for anchor in anchors:
            anchor.remove()

def get_nodes_with_source_links(doctree: Node) -> List[Node]:
    """Return a list of nodes that should have source links."""
    # This is a simplified version - in reality, we would identify specific node types
    return [doctree]

def collect_pages(builder: Builder) -> Generator[Tuple[str, Dict[str, Any], str], None, None]:
    """Collect pages to be included in the documentation output."""
    env = builder.env
    if not hasattr(env, '_viewcode_modules'):
        return
    
    # Check if this builder supports source pages
    if not is_supported_builder(builder):
        return
    
    # Generate pages for each module
    for modname, modinfo in env._viewcode_modules.items():
        pagename = f"_modules/{modname}"
        yield pagename, {"title": f"Source code for {modname}"}, modinfo["code"]

def setup_extension(builder: Builder) -> None:
    """Set up the viewcode extension."""
    builder.env.config["viewcode_enable_epub"] = False