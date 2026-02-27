from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

from app.inference import _filter_variants_by_tone
from app.tone.tone_calibration import calibrate_tone


CONTRACT_PATH = Path(__file__).resolve().parents[1] / "docs/persona/voice_contract.json"


def _raw_jailbreak_variants() -> list:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    return contract["skeletons"]["A"]["en"]["guardrail"]["jailbreak"]


def _normalized_variants() -> list[dict]:
    variants = []
    for raw in _raw_jailbreak_variants():
        if isinstance(raw, str):
            variants.append({"text": raw, "tone_tags": None})
            continue
        variants.append(raw)
    return variants


def _filtered_texts_for_severity(severity: str) -> tuple[str, list[str]]:
    tone_profile = calibrate_tone("A", severity, "JAILBREAK_ATTEMPT")
    filtered = _filter_variants_by_tone(_normalized_variants(), tone_profile)
    return tone_profile, [variant["text"] for variant in filtered]


def test_b17_contract_jailbreak_section_exists():
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    assert "guardrail" in contract["skeletons"]["A"]["en"]
    assert "jailbreak" in contract["skeletons"]["A"]["en"]["guardrail"]


def test_b17_contract_jailbreak_has_three_entries():
    variants = _raw_jailbreak_variants()
    assert len(variants) == 3


def test_b17_contract_jailbreak_keeps_universal_string_entry():
    variants = _raw_jailbreak_variants()
    assert "I have to follow system rules." in variants


def test_b17_jailbreak_low_maps_to_firm_boundary_tone():
    tone_profile, _texts = _filtered_texts_for_severity("LOW")
    assert tone_profile == "firm_boundary"


def test_b17_jailbreak_high_maps_to_firm_boundary_strict_tone():
    tone_profile, _texts = _filtered_texts_for_severity("HIGH")
    assert tone_profile == "firm_boundary_strict"


def test_b17_jailbreak_low_filter_pool_has_boundary_and_universal():
    _tone_profile, texts = _filtered_texts_for_severity("LOW")
    assert texts == [
        "I can't ignore system instructions.",
        "I have to follow system rules.",
    ]


def test_b17_jailbreak_high_filter_pool_has_strict_and_universal():
    _tone_profile, texts = _filtered_texts_for_severity("HIGH")
    assert texts == [
        "I must strictly follow system instructions.",
        "I have to follow system rules.",
    ]


def test_b17_jailbreak_low_and_high_filtered_pools_differ():
    _low_tone, low_texts = _filtered_texts_for_severity("LOW")
    _high_tone, high_texts = _filtered_texts_for_severity("HIGH")
    assert low_texts != high_texts


def test_b17_jailbreak_universal_line_present_for_low_and_high():
    _low_tone, low_texts = _filtered_texts_for_severity("LOW")
    _high_tone, high_texts = _filtered_texts_for_severity("HIGH")
    assert "I have to follow system rules." in low_texts
    assert "I have to follow system rules." in high_texts


def test_b17_jailbreak_filter_deterministic_for_low():
    _first_tone, first = _filtered_texts_for_severity("LOW")
    _second_tone, second = _filtered_texts_for_severity("LOW")
    assert first == second


def test_b17_jailbreak_filter_deterministic_for_high():
    _first_tone, first = _filtered_texts_for_severity("HIGH")
    _second_tone, second = _filtered_texts_for_severity("HIGH")
    assert first == second


def test_b17_jailbreak_filter_preserves_order_for_low_and_high():
    _low_tone, low_texts = _filtered_texts_for_severity("LOW")
    _high_tone, high_texts = _filtered_texts_for_severity("HIGH")
    assert low_texts[0] == "I can't ignore system instructions."
    assert low_texts[1] == "I have to follow system rules."
    assert high_texts[0] == "I must strictly follow system instructions."
    assert high_texts[1] == "I have to follow system rules."


def test_b17_jailbreak_filter_does_not_mutate_normalized_input():
    variants = _normalized_variants()
    original = deepcopy(variants)
    _ = _filter_variants_by_tone(variants, "firm_boundary")
    assert variants == original
