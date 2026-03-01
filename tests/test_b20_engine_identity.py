from __future__ import annotations

from fastapi.testclient import TestClient

from app import api as api_module
from app.engine_identity import ENGINE_NAME, ENGINE_RELEASE_STAGE, ENGINE_VERSION
from scripts.decision_trace import build_decision_trace


def _trace_kwargs() -> dict:
    return {
        "user_input": "Need help",
        "intent": "emotional",
        "emotional_lang": "en",
        "emotional_turn_index": 1,
        "previous_skeleton": "A",
        "resolved_skeleton": "B",
        "skeleton_after_guardrail": "B",
        "escalation_state": "none",
        "latched_theme": None,
        "signals": {"overwhelm": False, "resignation": False, "guilt": False, "wants_action": False},
        "eligible_count": 4,
        "selected_variant_indices": {"opener": 0, "validation": 0, "closure": 0},
        "window_size": 8,
        "window_fill": 1,
        "immediate_repeat_blocked": False,
        "fallback": None,
        "cultural": {},
        "invariants": {"selector_called_once": True, "rotation_bounded": True, "deterministic_selector": True},
    }


def test_b20_version_endpoint_returns_200():
    client = TestClient(api_module.app)
    response = client.get("/version")
    assert response.status_code == 200


def test_b20_version_endpoint_has_exact_keys():
    client = TestClient(api_module.app)
    body = client.get("/version").json()
    assert set(body.keys()) == {"engine_name", "engine_version", "release_stage"}


def test_b20_version_endpoint_matches_identity_constants():
    client = TestClient(api_module.app)
    body = client.get("/version").json()
    assert body == {
        "engine_name": ENGINE_NAME,
        "engine_version": ENGINE_VERSION,
        "release_stage": ENGINE_RELEASE_STAGE,
    }


def test_b20_version_endpoint_has_no_extra_fields():
    client = TestClient(api_module.app)
    body = client.get("/version").json()
    assert len(body) == 3
    assert "timestamp" not in body
    assert "system_info" not in body


def test_b20_version_endpoint_deterministic_across_20_calls():
    client = TestClient(api_module.app)
    responses = [client.get("/version").json() for _ in range(20)]
    assert len({str(r) for r in responses}) == 1


def test_b20_replay_hash_unchanged_for_canonical_safe_trace():
    trace = build_decision_trace(**_trace_kwargs(), include_tone_profile=True)
    assert trace["replay_hash"] == "sha256:3fea79a9adcd0da4edcdc1171f9770737eef08affadbc188938849d7721a0697"


def test_b20_canonical_replay_hash_deterministic():
    first = build_decision_trace(**_trace_kwargs(), include_tone_profile=True)
    second = build_decision_trace(**_trace_kwargs(), include_tone_profile=True)
    assert first["replay_hash"] == second["replay_hash"]
