from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.guardrails.guardrail_classifier import GuardrailResult
from app.guardrails.guardrail_escalation import compute_guardrail_escalation
from app.guardrails.guardrail_strategy import GUARDRAIL_STRATEGY_VERSION, GuardrailAction
from app.inference import InferenceEngine, _filter_variants_by_tone
from app.tone.tone_calibration import calibrate_tone
from app.voice.errors import VoiceContractError
from scripts.decision_trace import build_decision_trace


def _engine_stub(*, previous_skeleton: str = "A") -> InferenceEngine:
    engine = object.__new__(InferenceEngine)
    engine.voice_state = SimpleNamespace(
        escalation_state="none",
        latched_theme=None,
        emotional_turn_index=0,
        last_skeleton=previous_skeleton,
    )
    engine._voice_state_turn_snapshot = None
    return engine


def _install_self_harm_override(monkeypatch, severity: str):
    monkeypatch.setattr(
        "app.inference.classify_user_input",
        lambda _text: GuardrailResult("14.1", "SELF_HARM_RISK", severity, True),
    )
    monkeypatch.setattr(
        "app.inference.apply_guardrail_strategy",
        lambda _result: GuardrailAction(GUARDRAIL_STRATEGY_VERSION, True, None, False),
    )


def _trace_kwargs() -> dict:
    return {
        "user_input": "self-harm trace",
        "intent": "emotional",
        "emotional_lang": "en",
        "emotional_turn_index": 1,
        "previous_skeleton": "A",
        "resolved_skeleton": "B",
        "skeleton_after_guardrail": "C",
        "escalation_state": "none",
        "latched_theme": None,
        "signals": {"overwhelm": False, "resignation": False, "guilt": False, "wants_action": False},
        "eligible_count": 3,
        "selected_variant_indices": {"opener": 0, "validation": 0, "closure": 0},
        "window_size": 8,
        "window_fill": 1,
        "immediate_repeat_blocked": False,
        "fallback": None,
        "cultural": {},
        "invariants": {"selector_called_once": True, "rotation_bounded": True, "deterministic_selector": True},
    }


def _build_self_harm_trace(monkeypatch, *, severity: str):
    monkeypatch.setattr(
        "scripts.decision_trace.classify_user_input",
        lambda _text: GuardrailResult("14.1", "SELF_HARM_RISK", severity, True),
    )
    monkeypatch.setattr(
        "scripts.decision_trace.apply_guardrail_strategy",
        lambda _result: GuardrailAction(GUARDRAIL_STRATEGY_VERSION, False, None, False),
    )
    kwargs = _trace_kwargs()
    kwargs["user_input"] = f"self-harm-{severity.lower()}"
    kwargs["skeleton_after_guardrail"] = "C"
    return build_decision_trace(**kwargs, include_tone_profile=True)


@pytest.mark.parametrize("severity", ["LOW", "MEDIUM", "HIGH", "CRITICAL"])
def test_b18_self_harm_override_lock_passes_c_for_all_severities(monkeypatch, severity):
    engine = _engine_stub(previous_skeleton="A")
    _install_self_harm_override(monkeypatch, severity)
    seen = {}

    def _resolver(_self, _prompt, _severity, effective_skeleton):
        seen["skeleton"] = effective_skeleton
        return "locked"

    monkeypatch.setattr("app.inference.InferenceEngine._resolve_self_harm_override_response", _resolver)
    engine.handle_user_input = lambda _text: (_ for _ in ()).throw(AssertionError("handle_user_input must not run"))
    response = engine.generate("I need help")
    assert response == "locked"
    assert seen["skeleton"] == "C"


@pytest.mark.parametrize("base_skeleton", ["A", "B", "C", "D", "custom"])
def test_b18_self_harm_override_lock_ignores_base_skeleton(monkeypatch, base_skeleton):
    engine = _engine_stub(previous_skeleton=base_skeleton)
    _install_self_harm_override(monkeypatch, "CRITICAL")
    seen = {}

    def _resolver(_self, _prompt, _severity, effective_skeleton):
        seen["skeleton"] = effective_skeleton
        return "locked"

    monkeypatch.setattr("app.inference.InferenceEngine._resolve_self_harm_override_response", _resolver)
    engine.handle_user_input = lambda _text: (_ for _ in ()).throw(AssertionError("handle_user_input must not run"))
    response = engine.generate("I need help")
    assert response == "locked"
    assert seen["skeleton"] == "C"


def test_b18_self_harm_critical_lock_survives_escalation_regression(monkeypatch):
    engine = _engine_stub(previous_skeleton="A")
    _install_self_harm_override(monkeypatch, "CRITICAL")
    monkeypatch.setattr("app.inference.compute_guardrail_escalation", lambda *_args, **_kwargs: "A")
    seen = {}

    def _resolver(_self, _prompt, _severity, effective_skeleton):
        seen["skeleton"] = effective_skeleton
        return "locked"

    monkeypatch.setattr("app.inference.InferenceEngine._resolve_self_harm_override_response", _resolver)
    engine.handle_user_input = lambda _text: (_ for _ in ()).throw(AssertionError("handle_user_input must not run"))
    response = engine.generate("I need help")
    assert response == "locked"
    assert seen["skeleton"] == "C"


def test_b18_self_harm_high_lock_survives_escalation_regression(monkeypatch):
    engine = _engine_stub(previous_skeleton="B")
    _install_self_harm_override(monkeypatch, "HIGH")
    monkeypatch.setattr("app.inference.compute_guardrail_escalation", lambda *_args, **_kwargs: "A")
    seen = {}

    def _resolver(_self, _prompt, _severity, effective_skeleton):
        seen["skeleton"] = effective_skeleton
        return "locked"

    monkeypatch.setattr("app.inference.InferenceEngine._resolve_self_harm_override_response", _resolver)
    engine.handle_user_input = lambda _text: (_ for _ in ()).throw(AssertionError("handle_user_input must not run"))
    response = engine.generate("I need help")
    assert response == "locked"
    assert seen["skeleton"] == "C"


@pytest.mark.parametrize("severity", ["LOW", "MEDIUM", "HIGH", "CRITICAL"])
def test_b18_self_harm_all_severities_trace_after_guardrail_c(monkeypatch, severity):
    result = GuardrailResult("14.1", "SELF_HARM_RISK", severity, True)
    expected_after = compute_guardrail_escalation(result, "A")
    monkeypatch.setattr(
        "scripts.decision_trace.classify_user_input",
        lambda _text: GuardrailResult("14.1", "SELF_HARM_RISK", severity, True),
    )
    monkeypatch.setattr(
        "scripts.decision_trace.apply_guardrail_strategy",
        lambda _result: GuardrailAction(GUARDRAIL_STRATEGY_VERSION, False, None, False),
    )
    kwargs = _trace_kwargs()
    kwargs["skeleton_after_guardrail"] = expected_after
    trace = build_decision_trace(**kwargs, include_tone_profile=True)
    assert trace["skeleton"]["after_guardrail"] == "C"


def test_b18_self_harm_critical_tone_is_crisis(monkeypatch):
    trace = _build_self_harm_trace(monkeypatch, severity="CRITICAL")
    assert trace["tone_profile"] == "empathetic_crisis_support"


def test_b18_self_harm_high_tone_is_not_crisis(monkeypatch):
    trace = _build_self_harm_trace(monkeypatch, severity="HIGH")
    assert trace["tone_profile"] != "empathetic_crisis_support"


def test_b18_self_harm_high_tone_is_high_intensity(monkeypatch):
    trace = _build_self_harm_trace(monkeypatch, severity="HIGH")
    assert trace["tone_profile"] == "empathetic_high_intensity"


def test_b18_self_harm_low_tone_is_soft(monkeypatch):
    trace = _build_self_harm_trace(monkeypatch, severity="LOW")
    assert trace["tone_profile"] == "empathetic_soft"


def test_b18_self_harm_medium_tone_is_soft(monkeypatch):
    trace = _build_self_harm_trace(monkeypatch, severity="MEDIUM")
    assert trace["tone_profile"] == "empathetic_soft"


def test_b18_self_harm_replay_hash_differs_high_vs_critical(monkeypatch):
    high_trace = _build_self_harm_trace(monkeypatch, severity="HIGH")
    critical_trace = _build_self_harm_trace(monkeypatch, severity="CRITICAL")
    assert high_trace["replay_hash"] != critical_trace["replay_hash"]


def test_b18_self_harm_replay_hash_deterministic_for_high(monkeypatch):
    first = _build_self_harm_trace(monkeypatch, severity="HIGH")
    second = _build_self_harm_trace(monkeypatch, severity="HIGH")
    assert first["replay_hash"] == second["replay_hash"]


def test_b18_self_harm_replay_hash_deterministic_for_critical(monkeypatch):
    first = _build_self_harm_trace(monkeypatch, severity="CRITICAL")
    second = _build_self_harm_trace(monkeypatch, severity="CRITICAL")
    assert first["replay_hash"] == second["replay_hash"]


def test_b18_self_harm_missing_contract_raises_runtime_error(monkeypatch):
    engine = _engine_stub(previous_skeleton="A")
    _install_self_harm_override(monkeypatch, "CRITICAL")
    monkeypatch.setattr(
        "app.inference.InferenceEngine._load_contract_guardrail_variants",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(VoiceContractError("missing")),
    )
    engine.handle_user_input = lambda _text: (_ for _ in ()).throw(AssertionError("handle_user_input must not run"))
    with pytest.raises(RuntimeError):
        engine.generate("I want to die")


def test_b18_self_harm_missing_contract_runtime_error_message_stable(monkeypatch):
    engine = _engine_stub(previous_skeleton="A")
    _install_self_harm_override(monkeypatch, "CRITICAL")
    monkeypatch.setattr(
        "app.inference.InferenceEngine._load_contract_guardrail_variants",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(VoiceContractError("missing")),
    )
    engine.handle_user_input = lambda _text: (_ for _ in ()).throw(AssertionError("handle_user_input must not run"))
    with pytest.raises(RuntimeError) as exc:
        engine.generate("I want to die")
    assert str(exc.value) == "Self-harm guardrail contract missing for skeleton C."


def test_b18_self_harm_empty_contract_variants_raises_runtime_error(monkeypatch):
    engine = _engine_stub(previous_skeleton="A")
    _install_self_harm_override(monkeypatch, "CRITICAL")
    monkeypatch.setattr("app.inference.InferenceEngine._load_contract_guardrail_variants", lambda *_args, **_kwargs: [])
    engine.handle_user_input = lambda _text: (_ for _ in ()).throw(AssertionError("handle_user_input must not run"))
    with pytest.raises(RuntimeError):
        engine.generate("I want to die")


def test_b18_self_harm_resolver_forces_skeleton_c_when_called_with_a(monkeypatch):
    engine = _engine_stub(previous_skeleton="A")
    seen = {}

    def _load(_self, _language, _subtype, *, skeleton):
        seen["skeleton"] = skeleton
        return [
            {"text": "crisis", "tone_tags": ["empathetic_crisis_support"]},
            {"text": "fallback", "tone_tags": None},
        ]

    monkeypatch.setattr("app.inference.InferenceEngine._load_contract_guardrail_variants", _load)
    text = engine._resolve_self_harm_override_response("I want to die", "CRITICAL", "A")
    assert seen["skeleton"] == "C"
    assert text == "crisis"


def test_b18_self_harm_resolver_forces_skeleton_c_when_called_with_d(monkeypatch):
    engine = _engine_stub(previous_skeleton="A")
    seen = {}

    def _load(_self, _language, _subtype, *, skeleton):
        seen["skeleton"] = skeleton
        return [
            {"text": "high", "tone_tags": ["empathetic_high_intensity"]},
            {"text": "fallback", "tone_tags": None},
        ]

    monkeypatch.setattr("app.inference.InferenceEngine._load_contract_guardrail_variants", _load)
    text = engine._resolve_self_harm_override_response("Life feels pointless", "HIGH", "D")
    assert seen["skeleton"] == "C"
    assert text == "high"


def test_b18_self_harm_filter_never_empty_for_critical():
    variants = InferenceEngine._load_contract_guardrail_variants("en", "self_harm", skeleton="C")
    tone = calibrate_tone("C", "CRITICAL", "SELF_HARM_RISK")
    filtered = _filter_variants_by_tone(variants, tone)
    assert filtered


def test_b18_self_harm_filter_never_empty_for_high():
    variants = InferenceEngine._load_contract_guardrail_variants("en", "self_harm", skeleton="C")
    tone = calibrate_tone("C", "HIGH", "SELF_HARM_RISK")
    filtered = _filter_variants_by_tone(variants, tone)
    assert filtered


def test_b18_self_harm_filter_never_empty_for_low():
    variants = InferenceEngine._load_contract_guardrail_variants("en", "self_harm", skeleton="C")
    tone = calibrate_tone("C", "LOW", "SELF_HARM_RISK")
    filtered = _filter_variants_by_tone(variants, tone)
    assert filtered


def test_b18_self_harm_repeated_override_calls_never_downgrade(monkeypatch):
    engine = _engine_stub(previous_skeleton="A")
    _install_self_harm_override(monkeypatch, "CRITICAL")
    seen = []

    def _resolver(_self, _prompt, _severity, effective_skeleton):
        seen.append(effective_skeleton)
        return "locked"

    monkeypatch.setattr("app.inference.InferenceEngine._resolve_self_harm_override_response", _resolver)
    engine.handle_user_input = lambda _text: (_ for _ in ()).throw(AssertionError("handle_user_input must not run"))

    first = engine.generate("I want to die")
    engine.voice_state.last_skeleton = "B"
    second = engine.generate("I want to die")

    assert first == "locked"
    assert second == "locked"
    assert seen == ["C", "C"]
