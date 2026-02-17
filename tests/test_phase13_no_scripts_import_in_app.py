import ast
import os
from pathlib import Path

import pytest

APP_ROOT = Path(__file__).parent.parent / "app"

def get_py_files():
    # Helper to collect all Python files in the app directory
    return list(APP_ROOT.rglob("*.py"))

@pytest.mark.parametrize("py_file", get_py_files(), ids=lambda p: os.path.relpath(p, APP_ROOT))
def test_no_scripts_import_in_app(py_file):
    """
    Asserts that no Python file within the 'app' directory imports from 'scripts'.
    
    This is a static boundary guard to ensure CI/CD and diagnostic tooling
    is not bundled into the production runtime.
    """
    with open(py_file, "r", encoding="utf-8") as f:
        content = f.read()
    
    try:
        tree = ast.parse(content, filename=str(py_file))
    except SyntaxError as e:
        pytest.fail(f"Could not parse {py_file}: {e}")

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("scripts"):
                    pytest.fail(
                        f"Found forbidden import in {py_file} at line {node.lineno}: "
                        f"'import {alias.name}'"
                    )
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.module.startswith("scripts"):
                pytest.fail(
                    f"Found forbidden import in {py_file} at line {node.lineno}: "
                    f"'from {node.module} import ...'"
                )