from __future__ import annotations

import pytest

from app.inference import InferenceEngine


def _engine_stub() -> InferenceEngine:
    return object.__new__(InferenceEngine)


def test_b18_lang_resolver_prefers_requested_language():
    skeleton_block = {
        "hi": {"guardrail": {"self_harm": ["hi_variant"]}},
        "en": {"guardrail": {"self_harm": ["en_variant"]}},
    }
    variants = InferenceEngine._resolve_guardrail_language_block(skeleton_block, "hi", "self_harm")
    assert variants == ["hi_variant"]


def test_b18_lang_resolver_falls_back_to_en_when_language_missing():
    skeleton_block = {
        "en": {"guardrail": {"self_harm": ["en_variant"]}},
    }
    variants = InferenceEngine._resolve_guardrail_language_block(skeleton_block, "pa", "self_harm")
    assert variants == ["en_variant"]


def test_b18_lang_resolver_falls_back_to_en_when_language_has_no_guardrail():
    skeleton_block = {
        "hi": {},
        "en": {"guardrail": {"self_harm": ["en_variant"]}},
    }
    variants = InferenceEngine._resolve_guardrail_language_block(skeleton_block, "hi", "self_harm")
    assert variants == ["en_variant"]


def test_b18_lang_resolver_falls_back_to_en_when_language_missing_category():
    skeleton_block = {
        "hi": {"guardrail": {"abuse": ["x"]}},
        "en": {"guardrail": {"self_harm": ["en_variant"]}},
    }
    variants = InferenceEngine._resolve_guardrail_language_block(skeleton_block, "hi", "self_harm")
    assert variants == ["en_variant"]


def test_b18_lang_resolver_raises_when_language_and_en_missing():
    skeleton_block = {"hi": {"guardrail": {"abuse": ["x"]}}}
    with pytest.raises(RuntimeError):
        InferenceEngine._resolve_guardrail_language_block(skeleton_block, "hi", "self_harm")


def test_b18_lang_resolver_raises_when_en_present_without_guardrail():
    skeleton_block = {"en": {}}
    with pytest.raises(RuntimeError):
        InferenceEngine._resolve_guardrail_language_block(skeleton_block, "hi", "self_harm")


def test_b18_lang_resolver_raises_when_en_category_not_list():
    skeleton_block = {"en": {"guardrail": {"self_harm": "bad"}}}
    with pytest.raises(RuntimeError):
        InferenceEngine._resolve_guardrail_language_block(skeleton_block, "hi", "self_harm")


def test_b18_load_variants_falls_back_to_en_within_same_skeleton():
    variants = InferenceEngine._load_contract_guardrail_variants("pa", "self_harm", skeleton="C")
    assert variants[0]["text"] == "I'm really sorry that you're feeling this way. You don't have to face this alone."


def test_b18_load_variants_no_cross_skeleton_fallback():
    with pytest.raises(RuntimeError):
        InferenceEngine._load_contract_guardrail_variants("hi", "self_harm", skeleton="A")


def test_b18_self_harm_hindi_critical_resolves_hindi_crisis_text():
    engine = _engine_stub()
    text = engine._resolve_self_harm_override_response("मैं मरना चाहता हूँ", "CRITICAL", "C")
    assert text == "मुझे बहुत दुख है कि आप ऐसा महसूस कर रहे हैं। आपको यह अकेले नहीं झेलना है।"


def test_b18_self_harm_hindi_high_resolves_hindi_high_intensity_text():
    engine = _engine_stub()
    text = engine._resolve_self_harm_override_response("मैं बहुत टूट गया हूँ", "HIGH", "C")
    assert text == "मैं आपके साथ हूँ।"


def test_b18_self_harm_hindi_low_resolves_hindi_universal_text():
    engine = _engine_stub()
    text = engine._resolve_self_harm_override_response("मैं ठीक नहीं हूँ", "LOW", "C")
    assert text == "आप अकेले नहीं हैं।"


def test_b18_self_harm_non_hindi_falls_back_to_en_within_c_skeleton():
    engine = _engine_stub()
    text = engine._resolve_self_harm_override_response("I want to die", "CRITICAL", "C")
    assert text == "I'm really sorry that you're feeling this way. You deserve support, and reaching out to someone you trust could help."
