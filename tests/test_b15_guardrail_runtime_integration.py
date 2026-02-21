from types import SimpleNamespace

from app.guardrails.guardrail_classifier import GuardrailResult
from app.guardrails.guardrail_strategy import GuardrailAction, GUARDRAIL_STRATEGY_VERSION
from app.inference import InferenceEngine
from scripts.decision_trace import build_decision_trace


class _MemoryStub:
    def __init__(self, value: str):
        self.value = value

    def lookup(self, _prompt):
        return self.value


def _engine_stub(*, previous_skeleton: str = "A", emotional_turn_index: int = 0) -> InferenceEngine:
    engine = object.__new__(InferenceEngine)
    engine.voice_state = SimpleNamespace(
        escalation_state="none",
        latched_theme=None,
        emotional_turn_index=emotional_turn_index,
        last_skeleton=previous_skeleton,
    )
    engine._voice_state_turn_snapshot = None
    engine.memory = _MemoryStub("I hear you. We can take one step.")
    return engine


def _install_non_override_guardrail(monkeypatch, *, category: str, severity: str):
    monkeypatch.setattr(
        "app.inference.classify_user_input",
        lambda _text: GuardrailResult("14.1", category, severity, category != "SAFE"),
    )
    monkeypatch.setattr(
        "app.inference.apply_guardrail_strategy",
        lambda _result: GuardrailAction(GUARDRAIL_STRATEGY_VERSION, False, None, False),
    )


def _install_emotional_handle(engine: InferenceEngine, *, base_skeleton: str = "B"):
    engine.handle_user_input = lambda _text: (
        "emotional",
        "en",
        "empathy: hello",
        SimpleNamespace(emotional_skeleton=base_skeleton, emotional_lang="en"),
    )


def test_b15_runtime_safe_keeps_skeleton_and_no_override(monkeypatch):
    engine = _engine_stub(previous_skeleton="A")
    _install_non_override_guardrail(monkeypatch, category="SAFE", severity="LOW")
    _install_emotional_handle(engine, base_skeleton="B")

    seen = {}

    def _post(prompt, intent, lang, conditioned_prompt, text, meta, max_new_tokens, resolution):
        seen["resolution"] = resolution
        return text, meta

    engine._post_process_response = _post

    output, meta = engine.generate("Tell me a small step", return_meta=True)
    assert output == "I hear you. We can take one step."
    assert meta == {"source": "memory_exact"}
    assert seen["resolution"].base_emotional_skeleton == "B"
    assert seen["resolution"].after_guardrail_skeleton == "B"
    assert seen["resolution"].emotional_skeleton == "B"


def test_b15_runtime_self_harm_non_override_forces_c(monkeypatch):
    engine = _engine_stub(previous_skeleton="A")
    _install_non_override_guardrail(monkeypatch, category="SELF_HARM_RISK", severity="HIGH")
    _install_emotional_handle(engine, base_skeleton="B")

    seen = {}

    def _post(prompt, intent, lang, conditioned_prompt, text, meta, max_new_tokens, resolution):
        seen["resolution"] = resolution
        return text, meta

    engine._post_process_response = _post
    engine.generate("Need help", return_meta=True)

    assert seen["resolution"].base_emotional_skeleton == "B"
    assert seen["resolution"].after_guardrail_skeleton == "C"
    assert seen["resolution"].emotional_skeleton == "C"
    assert engine.voice_state.last_skeleton == "C"


def test_b15_runtime_abuse_legal_transition_to_a(monkeypatch):
    engine = _engine_stub(previous_skeleton="C")
    _install_non_override_guardrail(monkeypatch, category="ABUSE_HARASSMENT", severity="HIGH")
    _install_emotional_handle(engine, base_skeleton="B")

    seen = {}

    def _post(prompt, intent, lang, conditioned_prompt, text, meta, max_new_tokens, resolution):
        seen["resolution"] = resolution
        return text, meta

    engine._post_process_response = _post
    engine.generate("Need help", return_meta=True)

    assert seen["resolution"].base_emotional_skeleton == "B"
    assert seen["resolution"].after_guardrail_skeleton == "A"
    assert seen["resolution"].emotional_skeleton == "A"


def test_b15_runtime_abuse_does_not_bypass_illegal_transition(monkeypatch):
    engine = _engine_stub(previous_skeleton="B")
    _install_non_override_guardrail(monkeypatch, category="ABUSE_HARASSMENT", severity="HIGH")
    _install_emotional_handle(engine, base_skeleton="B")

    seen = {}

    def _post(prompt, intent, lang, conditioned_prompt, text, meta, max_new_tokens, resolution):
        seen["resolution"] = resolution
        return text, meta

    engine._post_process_response = _post
    engine.generate("Need help", return_meta=True)

    # B -> A is illegal in current transition table; mapping must fall back to base.
    assert seen["resolution"].base_emotional_skeleton == "B"
    assert seen["resolution"].after_guardrail_skeleton == "B"
    assert seen["resolution"].emotional_skeleton == "B"


def test_b15_runtime_manipulation_medium_unchanged(monkeypatch):
    engine = _engine_stub(previous_skeleton="A")
    _install_non_override_guardrail(monkeypatch, category="MANIPULATION_ATTEMPT", severity="MEDIUM")
    _install_emotional_handle(engine, base_skeleton="B")

    seen = {}

    def _post(prompt, intent, lang, conditioned_prompt, text, meta, max_new_tokens, resolution):
        seen["resolution"] = resolution
        return text, meta

    engine._post_process_response = _post
    engine.generate("Need help", return_meta=True)

    assert seen["resolution"].base_emotional_skeleton == "B"
    assert seen["resolution"].after_guardrail_skeleton == "B"
    assert seen["resolution"].emotional_skeleton == "B"


def test_b15_runtime_determinism_same_inputs_same_effective_skeleton(monkeypatch):
    engine = _engine_stub(previous_skeleton="A")
    _install_non_override_guardrail(monkeypatch, category="SELF_HARM_RISK", severity="HIGH")
    _install_emotional_handle(engine, base_skeleton="B")

    seen = []

    def _post(prompt, intent, lang, conditioned_prompt, text, meta, max_new_tokens, resolution):
        seen.append((resolution.base_emotional_skeleton, resolution.after_guardrail_skeleton, resolution.emotional_skeleton))
        return text, meta

    engine._post_process_response = _post

    out1, meta1 = engine.generate("Need help", return_meta=True)
    out2, meta2 = engine.generate("Need help", return_meta=True)
    assert out1 == out2
    assert meta1 == meta2
    assert seen[0] == seen[1] == ("B", "C", "C")


def test_b15_runtime_override_short_circuits_before_escalation(monkeypatch):
    engine = _engine_stub(previous_skeleton="A")

    monkeypatch.setattr(
        "app.inference.classify_user_input",
        lambda _text: GuardrailResult("14.1", "SELF_HARM_RISK", "HIGH", True),
    )
    monkeypatch.setattr(
        "app.inference.apply_guardrail_strategy",
        lambda _result: GuardrailAction(GUARDRAIL_STRATEGY_VERSION, True, "override", False),
    )
    monkeypatch.setattr(
        "app.inference.compute_guardrail_escalation",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("escalation must not run on override path")),
    )

    engine.handle_user_input = lambda _text: (_ for _ in ()).throw(AssertionError("handle_user_input must not run"))
    response, meta = engine.generate("I want to kill myself", return_meta=True)
    assert response == "override"
    assert meta == {}


def test_b15_runtime_emotional_turn_index_not_changed_by_escalation(monkeypatch):
    engine = _engine_stub(previous_skeleton="A", emotional_turn_index=11)
    _install_non_override_guardrail(monkeypatch, category="SELF_HARM_RISK", severity="HIGH")
    _install_emotional_handle(engine, base_skeleton="B")
    engine._post_process_response = lambda prompt, intent, lang, conditioned_prompt, text, meta, max_new_tokens, resolution: (text, meta)

    _, _ = engine.generate("Need help", return_meta=True)
    assert engine.voice_state.emotional_turn_index == 11


def test_b15_replay_hash_changes_when_after_guardrail_changes():
    kwargs = dict(
        user_input="Need help",
        intent="emotional",
        emotional_lang="en",
        emotional_turn_index=1,
        previous_skeleton="A",
        resolved_skeleton="B",
        escalation_state="none",
        latched_theme=None,
        signals={"overwhelm": False, "resignation": False, "guilt": False, "wants_action": False},
        eligible_count=4,
        selected_variant_indices={"opener": 0, "validation": 0, "closure": 0},
        window_size=8,
        window_fill=1,
        immediate_repeat_blocked=False,
        fallback=None,
        cultural={},
        invariants={"selector_called_once": True, "rotation_bounded": True, "deterministic_selector": True},
    )

    trace_same = build_decision_trace(**kwargs, skeleton_after_guardrail="B")
    trace_changed = build_decision_trace(**kwargs, skeleton_after_guardrail="C")
    assert trace_same["replay_hash"] != trace_changed["replay_hash"]
