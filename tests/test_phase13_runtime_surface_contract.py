import pytest
from app.inference import InferenceEngine

# These keys are for CI/CD and diagnostics, and should not be present in the
# default runtime response surface.
FORBIDDEN_META_KEYS = [
    "self_digest",
    "linked_digests",
    "replay_hash",
    "performance_report_version",
    "drift_report_version",
    "stress_integrity_report_version",
    "decision_trace_validation",
    "semantic_consistency_version",
    "decision_trace_snapshot",
]

@pytest.fixture(scope="module")
def inference_engine():
    """Provides a shared InferenceEngine instance for the test module."""
    # Using the default model path from run_eval.py.
    # This path must be valid for the test to run.
    return InferenceEngine("artifacts/alignment_lora/final")

def test_runtime_surface_contract_has_no_forbidden_fields(inference_engine):
    """
    Runs a single inference and asserts that no forbidden meta keys are present.
    This enforces a clean boundary between production runtime and diagnostic/CI surfaces.
    """
    prompt = "I feel lost"  # A simple emotional prompt
    
    response, meta = inference_engine.generate(
        prompt,
        max_new_tokens=128,  # Keep it short and fast
        return_meta=True,
    )

    assert response is not None
    assert isinstance(meta, dict)

    for key in FORBIDDEN_META_KEYS:
        assert key not in meta, f"Forbidden key '{key}' found in runtime inference metadata"