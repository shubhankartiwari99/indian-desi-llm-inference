import ast
import os
from pathlib import Path
import pytest

APP_ROOT = Path(__file__).parent.parent / "app"

def get_py_files():
    """Helper to collect all Python files in the app directory."""
    return list(APP_ROOT.rglob("*.py"))

# These names are related to CI-only fault injection and have no place in runtime code.
FORBIDDEN_NAMES = {
    "FaultInjection",
    "patch_selector",
    "patch_assembly",
    "ci_fault_injection_runner",
}

@pytest.mark.parametrize("py_file", get_py_files(), ids=lambda p: os.path.relpath(p, APP_ROOT))
def test_no_fault_injection_in_app(py_file):
    """
    Asserts that no app file references fault injection tooling by name.
    This is a static guard to prevent CI/testing constructs from leaking
    into the production runtime.
    """
    with open(py_file, "r", encoding="utf-8") as f:
        content = f.read()

    try:
        tree = ast.parse(content, filename=str(py_file))
    except SyntaxError as e:
        pytest.fail(f"Could not parse {py_file}: {e}")

    for node in ast.walk(tree):
        # Check for direct usage of a forbidden name (e.g., as a variable or class)
        if isinstance(node, ast.Name):
            if node.id in FORBIDDEN_NAMES:
                pytest.fail(
                    f"Found forbidden reference to '{node.id}' in {py_file} "
                    f"at line {node.lineno}."
                )
        # Check for access of a forbidden name as an attribute (e.g., obj.FaultInjection)
        elif isinstance(node, ast.Attribute):
             if node.attr in FORBIDDEN_NAMES:
                pytest.fail(
                    f"Found forbidden attribute access of '{node.attr}' in {py_file} "
                    f"at line {node.lineno}."
                )