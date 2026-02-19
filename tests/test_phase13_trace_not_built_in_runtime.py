import pytest
import os
from app.inference import InferenceEngine

pytestmark = pytest.mark.requires_model

# These keys are examples of diagnostic data that should only be generated
# when RUNTIME_DIAGNOSTICS is explicitly enabled. This is not an exhaustive list,
# but covers the primary fields that constitute the 'decision trace'.
DIAGNOSTIC_META_KEYS = [
    "shaped",
    "shape",
    "escalation_active",
    "post_regen",
    "post_regen_prompt",
    "semantic_dropped",
    "semantic_dropped_reason",
]

@pytest.fixture(scope="module")
def inference_engine():
    """Provides a shared InferenceEngine instance for the test module."""
    # This path must be valid for the test to run.
    return InferenceEngine("artifacts/alignment_lora/final")

def test_decision_trace_not_built_in_runtime(inference_engine):
    """
    Verifies that diagnostic fields (the 'decision trace') are not added to
    the metadata when RUNTIME_DIAGNOSTICS is not enabled.
    
    This test ensures that the production path is clean by default.
    """
    # Explicitly ensure the environment variable is not set for this test.
    original_value = os.environ.pop("RUNTIME_DIAGNOSTICS", None)

    try:
        prompt = "I feel overwhelmed and can't focus."
        _, meta = inference_engine.generate(
            prompt,
            max_new_tokens=128,
            return_meta=True,
        )

        assert isinstance(meta, dict)

        for key in DIAGNOSTIC_META_KEYS:
            assert key not in meta, f"Diagnostic key '{key}' found in meta when it should not be."

        # Special case: 'source' may exist, but should not be 'model' in the default path.
        if "source" in meta:
            assert meta["source"] != "model", (
                "Diagnostic key 'source' was 'model' in default runtime. "
                "This should only happen with RUNTIME_DIAGNOSTICS=1."
            )
            
    finally:
        # Restore the environment variable to avoid side effects
        if original_value is not None:
            os.environ["RUNTIME_DIAGNOSTICS"] = original_value