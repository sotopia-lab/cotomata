import pytest
from codebase import TypeHandler

def test_basic_type_reference():
    """Test basic type reference formatting."""
    handler = TypeHandler()
    ref = handler.process_type_annotation("str")
    assert ref['reftext'] == "str"
    assert ref['reftarget'] == "str"
    assert ref['reftype'] == "class"

def test_qualified_type_reference():
    """Test fully qualified type reference."""
    handler = TypeHandler()
    ref = handler.process_type_annotation("module.submodule.Type")
    assert ref['reftext'] == "module.submodule.Type"
    assert ref['reftarget'] == "module.submodule.Type"
    assert ref['reftype'] == "class"

def test_none_reference():
    """Test None type reference."""
    handler = TypeHandler()
    ref = handler.process_type_annotation("None")
    assert ref['reftext'] == "None"
    assert ref['reftarget'] == "None"
    assert ref['reftype'] == "obj"

# Feature 1 tests: Cross-reference specifiers

def test_module_relative_reference():
    """Test module-relative reference with dot prefix."""
    handler = TypeHandler()
    ref = handler.process_type_annotation(".Type")
    assert ref['reftext'] == "Type"
    assert ref['reftarget'] == "Type"
    assert ref['refspecific'] == True
    assert ref['reftype'] == "class"

def test_display_only_class_name():
    """Test displaying only class name with tilde prefix."""
    handler = TypeHandler()
    ref = handler.process_type_annotation("~module.submodule.Type")
    assert ref['reftext'] == "Type"
    assert ref['reftarget'] == "module.submodule.Type"
    assert ref.get('refspecific', False) == False
    assert ref['reftype'] == "class"

# Feature 2 tests: Unqualified type hints

def test_use_unqualified_names():
    """Test using unqualified names with config option."""
    handler = TypeHandler(unqualified_typehints=True)
    ref = handler.process_type_annotation("module.submodule.Type")
    assert ref['reftext'] == "Type"
    assert ref['reftarget'] == "module.submodule.Type"
    assert ref['reftype'] == "class"

def test_unqualified_with_nested_types():
    """Test unqualified_typehints with nested module structure."""
    handler = TypeHandler(unqualified_typehints=True)
    ref = handler.process_type_annotation("a.very.long.module.path.Type")
    assert ref['reftext'] == "Type"
    assert ref['reftarget'] == "a.very.long.module.path.Type"
    assert ref['reftype'] == "class"

def test_interaction_between_features():
    """Test interaction between cross-reference specifiers and unqualified_typehints."""
    # Feature 1 should take precedence over Feature 2
    handler = TypeHandler(unqualified_typehints=True)
    
    # Module-relative reference (Feature 1)
    ref = handler.process_type_annotation(".CustomType")
    assert ref['reftext'] == "CustomType"
    assert ref['reftarget'] == "CustomType"
    assert ref['refspecific'] == True
    
    # Display only class name with tilde (Feature 1)
    ref = handler.process_type_annotation("~very.long.path.Type")
    assert ref['reftext'] == "Type"
    assert ref['reftarget'] == "very.long.path.Type"

def test_backward_compatibility():
    """Test backward compatibility with existing use_qualified_names."""
    # Original behavior with use_qualified_names=False
    handler = TypeHandler(use_qualified_names=False, unqualified_typehints=False)
    ref = handler.process_type_annotation("module.Type")
    assert ref['reftext'] == "Type"
    assert ref['reftarget'] == "module.Type"
    
    # New behavior with unqualified_typehints=True should be similar
    handler = TypeHandler(use_qualified_names=True, unqualified_typehints=True)
    ref = handler.process_type_annotation("module.Type")
    assert ref['reftext'] == "Type"
    assert ref['reftarget'] == "module.Type"

if __name__ == "__main__":
    pytest.main(["-v", "test.py"])