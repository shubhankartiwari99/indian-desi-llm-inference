import ast
import os
from pathlib import Path
import pytest

APP_ROOT = Path(__file__).parent.parent / "app"

def get_py_files():
    """Helper to collect all Python files in the app directory."""
    return list(APP_ROOT.rglob("*.py"))

# For now, completely forbid 'time' module and specific performance names.
# If a legitimate use for 'time' arises, this guard can be made more specific.
FORBIDDEN_MODULES = {"time"}
FORBIDDEN_NAMES = {"PerfTimer", "perf_counter"}

@pytest.mark.parametrize("py_file", get_py_files(), ids=lambda p: os.path.relpath(p, APP_ROOT))
def test_no_performance_imports_in_app(py_file):
    """
    Asserts that no app file imports performance-related modules like 'time'
    or names like 'perf_counter'.
    This prevents diagnostic/performance code from leaking into the runtime.
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
                if alias.name in FORBIDDEN_MODULES:
                    pytest.fail(
                        f"Found forbidden module import in {py_file} at line {node.lineno}: "
                        f"'import {alias.name}'"
                    )
        elif isinstance(node, ast.ImportFrom):
            if node.module in FORBIDDEN_MODULES:
                # This catches 'from time import ...'
                pytest.fail(
                    f"Found forbidden import from '{node.module}' in {py_file} at line {node.lineno}."
                )
            for alias in node.names:
                if alias.name in FORBIDDEN_NAMES:
                    # This catches 'from some.module import PerfTimer'
                    pytest.fail(
                        f"Found forbidden name import '{alias.name}' from module '{node.module}' "
                        f"in {py_file} at line {node.lineno}."
                    )