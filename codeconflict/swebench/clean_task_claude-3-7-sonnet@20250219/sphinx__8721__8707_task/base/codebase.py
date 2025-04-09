"""
Viewcode extension for HTML documentation generation.

This extension allows viewing source code for modules in documentation.
"""

import os
from typing import Dict, Any, Optional, Tuple, List, Set

class Node:
    """Base class for document nodes."""
    def __init__(self, **kwargs):
        self.attributes = kwargs
        self.children = []
        self.parent = None

    def __getitem__(self, key):
        return self.attributes[key]
    
    def __setitem__(self, key, value):
        self.attributes[key] = value
    
    def add_child(self, child):
        self.children.append(child)
        child.parent = self
    
    def remove(self):
        if self.parent:
            self.parent.children.remove(self)
            self.parent = None


class TextNode(Node):
    """A node that contains text."""
    def __init__(self, text, **kwargs):
        super().__init__(**kwargs)
        self.text = text


class Builder:
    """Base class for documentation builders."""
    def __init__(self, config):
        self.config = config
        self.name = "base"
        self.format = "base"
        self.env = Environment()
        
    def build_all(self):
        """Build all documentation files."""
        pass
    
    def get_relative_uri(self, from_path, to_path):
        """Calculate relative path from from_path to to_path."""
        return os.path.relpath(to_path, os.path.dirname(from_path))


class HTMLBuilder(Builder):
    """Builder for HTML documentation."""
    def __init__(self, config):
        super().__init__(config)
        self.name = "html"
        self.format = "html"
        self.highlighter = "pygments"


class SingleHTMLBuilder(HTMLBuilder):
    """Builder that creates a single HTML file."""
    def __init__(self, config):
        super().__init__(config)
        self.name = "singlehtml"


class EPUBBuilder(HTMLBuilder):
    """Builder for EPUB documentation."""
    def __init__(self, config):
        super().__init__(config)
        self.name = "epub"


class Application:
    """Application class that manages the documentation generation process."""
    def __init__(self, builder_name="html", config=None):
        if config is None:
            config = Config()
        
        # Initialize builder based on name
        if builder_name == "html":
            self.builder = HTMLBuilder(config)
        elif builder_name == "singlehtml":
            self.builder = SingleHTMLBuilder(config)
        elif builder_name == "epub":
            self.builder = EPUBBuilder(config)
        else:
            self.builder = Builder(config)
        
        self.config = config
        self.transforms = []
    
    def add_transform(self, transform):
        """Add a post-transform to the application."""
        self.transforms.append(transform)


class Environment:
    """Environment for the documentation build process."""
    def __init__(self):
        self.docname = "index"
        self._viewcode_modules = {}


class Config:
    """Configuration for the documentation build process."""
    def __init__(self):
        # Default configuration values
        self.viewcode_enable_epub = False


# Main viewcode functions

def collect_pages(app):
    """Collect source code pages for modules."""
    env = app.builder.env
    if not hasattr(env, '_viewcode_modules'):
        return
    
    # Generate module pages
    for modname, entry in env._viewcode_modules.items():
        code = entry.get('code', '')
        yield (f'_modules/{modname}', {'title': modname, 'code': code}, 'module.html')


def doctree_read(app, doctree):
    """Process a doctree when it's read."""
    env = app.builder.env
    if not hasattr(env, '_viewcode_modules'):
        env._viewcode_modules = {}

    # For each function/class reference in the document:
    # Add source links if appropriate
    for node in doctree.traverse():
        if getattr(node, 'tagname', '') == 'function':
            modname = node.get('module')
            if modname:
                # Add source link to function node
                add_source_link(env, node, modname, node.get('name'))


def add_source_link(env, node, modname, name):
    """Add a source link to a node."""
    pagename = f'_modules/{modname}'
    
    # Create source link node
    inline = TextNode('[source]', classes=['viewcode-link'])
    source_ref = Node(
        reftype='viewcode',
        refdomain='std',
        refexplicit=False,
        reftarget=pagename,
        refid=name,
        refdoc=env.docname
    )
    source_ref.add_child(inline)
    
    only_html = Node(expr='html')
    only_html.add_child(source_ref)
    
    node.add_child(only_html)


def setup(app):
    """Set up the viewcode extension."""
    app.config.viewcode_enable_epub = False
    
    # Connect event handlers
    app.doctree_read = doctree_read
    app.collect_pages = collect_pages
    
    return {
        'version': '1.0',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }