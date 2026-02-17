import os
from pathlib import Path
import pytest

APP_ROOT = Path(__file__).parent.parent / "app"

def get_all_files():
    """Helper to collect all files in the app directory, respecting .gitignore if possible."""
    # This is a simple implementation. A more robust one might parse .gitignore.
    return [p for p in APP_ROOT.rglob("*") if p.is_file() and ".git" not in p.parts]

# These strings correspond to build-time artifacts and diagnostic reports.
# The production 'app' code should be completely unaware of their existence.
FORBIDDEN_STRINGS = [
    "artifacts/",
    "decision_trace_snapshot.json",
    "performance_report.json",
    "stress_integrity_report.json",
]

@pytest.mark.parametrize("file_path", get_all_files(), ids=lambda p: os.path.relpath(p, APP_ROOT))
def test_no_artifact_references_in_app(file_path):
    """
    Asserts that no file in the 'app' directory contains references to
    build-time artifact paths or filenames.
    This enforces a strict separation between the runtime bundle and the
    CI/diagnostic artifacts, ensuring a clean release.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except UnicodeDecodeError:
        # This can happen for binary files, which are unlikely to contain the forbidden strings.
        # We can safely skip them.
        return

    for forbidden_string in FORBIDDEN_STRINGS:
        if forbidden_string in content:
            pytest.fail(
                f"Found forbidden string '{forbidden_string}' in file {file_path}. "
                "The 'app' directory must not contain references to build artifacts."
            )