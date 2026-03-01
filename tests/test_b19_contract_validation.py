from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any

import pytest

from app.contract_validation import validate_contract_structure
from app.tone.tone_calibration import TONE_PROFILES


CONTRACT_PATH = Path(__file__).resolve().parents[1] / "docs/persona/voice_contract.json"


def _real_contract() -> dict[str, Any]:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def _allowed_tones() -> set[str]:
    return set(TONE_PROFILES)


def _validate(contract: dict[str, Any]) -> None:
    validate_contract_structure(contract, _allowed_tones())


def _minimal_valid_contract() -> dict[str, Any]:
    return {
        "contract_version": "test",
        "skeletons": {
            "A": {
                "en": {
                    "guardrail": {
                        "jailbreak": ["jb"],
                        "abuse": ["ab"],
                    }
                }
            },
            "C": {
                "en": {
                    "guardrail": {
                        "self_harm": ["sh"],
                    }
                }
            },
        },
    }


# ================================================
# SECTION A — Valid contract passes
# ================================================


def test_b19_contract_validation_real_contract_passes():
    _validate(_real_contract())


def test_b19_contract_validation_minimal_contract_passes():
    _validate(_minimal_valid_contract())


# ================================================
# SECTION B — Skeleton errors
# ================================================


def test_b19_contract_validation_rejects_non_dict_contract():
    with pytest.raises(ValueError, match="Contract must be a dictionary"):
        validate_contract_structure([], _allowed_tones())  # type: ignore[arg-type]


def test_b19_contract_validation_rejects_missing_skeletons_block():
    with pytest.raises(ValueError, match="Missing or invalid 'skeletons' block"):
        _validate({})


def test_b19_contract_validation_rejects_non_dict_skeletons_block():
    with pytest.raises(ValueError, match="Missing or invalid 'skeletons' block"):
        _validate({"skeletons": []})  # type: ignore[arg-type]


def test_b19_contract_validation_rejects_invalid_skeleton_key():
    contract = _minimal_valid_contract()
    contract["skeletons"]["X"] = {}
    with pytest.raises(ValueError, match="Invalid skeleton key: X"):
        _validate(contract)


def test_b19_contract_validation_rejects_missing_skeleton_c():
    contract = _minimal_valid_contract()
    del contract["skeletons"]["C"]
    with pytest.raises(ValueError, match="Skeleton C must exist"):
        _validate(contract)


def test_b19_contract_validation_rejects_missing_skeleton_a():
    contract = _minimal_valid_contract()
    del contract["skeletons"]["A"]
    with pytest.raises(ValueError, match="Skeleton A must exist"):
        _validate(contract)


def test_b19_contract_validation_rejects_non_dict_skeleton_block():
    contract = _minimal_valid_contract()
    contract["skeletons"]["A"] = "bad"  # type: ignore[assignment]
    with pytest.raises(
        ValueError,
        match="Skeleton A must contain en.guardrail.jailbreak and en.guardrail.abuse",
    ):
        _validate(contract)


# ================================================
# SECTION C — Guardrail category errors
# ================================================


def test_b19_contract_validation_rejects_unknown_guardrail_category():
    contract = _real_contract()
    contract["skeletons"]["A"]["en"]["guardrail"]["unknown_category"] = ["bad"]
    with pytest.raises(ValueError, match="Invalid guardrail category: unknown_category"):
        _validate(contract)


def test_b19_contract_validation_requires_c_en_self_harm():
    contract = _real_contract()
    del contract["skeletons"]["C"]["en"]["guardrail"]["self_harm"]
    with pytest.raises(ValueError, match="Skeleton C must contain en.guardrail.self_harm"):
        _validate(contract)


def test_b19_contract_validation_requires_a_en_jailbreak():
    contract = _real_contract()
    del contract["skeletons"]["A"]["en"]["guardrail"]["jailbreak"]
    with pytest.raises(
        ValueError,
        match="Skeleton A must contain en.guardrail.jailbreak and en.guardrail.abuse",
    ):
        _validate(contract)


def test_b19_contract_validation_requires_a_en_abuse():
    contract = _real_contract()
    del contract["skeletons"]["A"]["en"]["guardrail"]["abuse"]
    with pytest.raises(
        ValueError,
        match="Skeleton A must contain en.guardrail.jailbreak and en.guardrail.abuse",
    ):
        _validate(contract)


def test_b19_contract_validation_rejects_non_dict_guardrail_block():
    contract = _real_contract()
    contract["skeletons"]["A"]["en"]["guardrail"] = []  # type: ignore[assignment]
    with pytest.raises(
        ValueError,
        match="Skeleton A must contain en.guardrail.jailbreak and en.guardrail.abuse",
    ):
        _validate(contract)


def test_b19_contract_validation_rejects_non_list_guardrail_category_payload():
    contract = _real_contract()
    contract["skeletons"]["A"]["en"]["guardrail"]["jailbreak"] = "bad"  # type: ignore[assignment]
    with pytest.raises(ValueError, match="A.en.jailbreak must be a non-empty list"):
        _validate(contract)


def test_b19_contract_validation_rejects_empty_guardrail_category_payload():
    contract = _real_contract()
    contract["skeletons"]["A"]["en"]["guardrail"]["jailbreak"] = []
    with pytest.raises(ValueError, match="A.en.jailbreak must be a non-empty list"):
        _validate(contract)


# ================================================
# SECTION D — Variant shape errors
# ================================================


def test_b19_contract_validation_rejects_invalid_variant_entry_type():
    contract = _real_contract()
    contract["skeletons"]["A"]["en"]["guardrail"]["jailbreak"] = [123]  # type: ignore[list-item]
    with pytest.raises(ValueError, match="Invalid variant entry in A.en.jailbreak"):
        _validate(contract)


def test_b19_contract_validation_rejects_variant_dict_missing_text():
    contract = _real_contract()
    contract["skeletons"]["A"]["en"]["guardrail"]["jailbreak"] = [{"tone_tags": ["firm_boundary"]}]
    with pytest.raises(ValueError, match="Variant entry missing valid 'text' in A.en.jailbreak"):
        _validate(contract)


def test_b19_contract_validation_rejects_variant_dict_non_string_text():
    contract = _real_contract()
    contract["skeletons"]["A"]["en"]["guardrail"]["jailbreak"] = [{"text": 101}]  # type: ignore[list-item]
    with pytest.raises(ValueError, match="Variant entry missing valid 'text' in A.en.jailbreak"):
        _validate(contract)


def test_b19_contract_validation_rejects_non_list_tone_tags():
    contract = _real_contract()
    contract["skeletons"]["A"]["en"]["guardrail"]["jailbreak"] = [
        {"text": "x", "tone_tags": "firm_boundary"}  # type: ignore[list-item]
    ]
    with pytest.raises(ValueError, match="'tone_tags' must be list in A.en.jailbreak"):
        _validate(contract)


def test_b19_contract_validation_rejects_non_string_tone_tag_entry():
    contract = _real_contract()
    contract["skeletons"]["A"]["en"]["guardrail"]["jailbreak"] = [
        {"text": "x", "tone_tags": ["firm_boundary", 7]}  # type: ignore[list-item]
    ]
    with pytest.raises(ValueError, match="Invalid tone tag type in A.en.jailbreak"):
        _validate(contract)


def test_b19_contract_validation_rejects_unknown_tone_tag():
    contract = _real_contract()
    contract["skeletons"]["A"]["en"]["guardrail"]["jailbreak"] = [
        {"text": "x", "tone_tags": ["unknown_tone"]}
    ]
    with pytest.raises(ValueError, match="Unknown tone profile 'unknown_tone' in A.en.jailbreak"):
        _validate(contract)


def test_b19_contract_validation_does_not_mutate_input_contract():
    contract = _real_contract()
    original = deepcopy(contract)
    _validate(contract)
    assert contract == original


# ================================================
# SECTION E — Language block errors
# ================================================


def test_b19_contract_validation_rejects_non_dict_language_block():
    contract = _real_contract()
    contract["skeletons"]["A"]["hi"] = "bad"  # type: ignore[assignment]
    with pytest.raises(
        ValueError,
        match="Language block 'hi' under skeleton 'A' must be a dictionary",
    ):
        _validate(contract)


def test_b19_contract_validation_rejects_language_guardrail_not_dict():
    contract = _real_contract()
    contract["skeletons"]["A"]["hi"]["guardrail"] = "bad"  # type: ignore[assignment]
    with pytest.raises(ValueError, match="'guardrail' under A.hi must be a dictionary"):
        _validate(contract)


# ================================================
# SECTION F — Tone profile validation
# ================================================


def test_b19_contract_validation_accepts_valid_tone_tags():
    contract = _minimal_valid_contract()
    contract["skeletons"]["A"]["en"]["guardrail"]["jailbreak"] = [
        {"text": "x", "tone_tags": ["firm_boundary"]}
    ]
    _validate(contract)


def test_b19_contract_validation_accepts_multiple_valid_tone_tags():
    contract = _minimal_valid_contract()
    contract["skeletons"]["A"]["en"]["guardrail"]["jailbreak"] = [
        {"text": "x", "tone_tags": ["firm_boundary", "firm_boundary_strict"]}
    ]
    _validate(contract)


def test_b19_contract_validation_accepts_dict_variant_without_tone_tags():
    contract = _minimal_valid_contract()
    contract["skeletons"]["A"]["en"]["guardrail"]["jailbreak"] = [{"text": "x"}]
    _validate(contract)


def test_b19_contract_validation_accepts_dict_variant_with_none_tone_tags():
    contract = _minimal_valid_contract()
    contract["skeletons"]["A"]["en"]["guardrail"]["jailbreak"] = [{"text": "x", "tone_tags": None}]
    _validate(contract)


def test_b19_contract_validation_accepts_plain_string_variants():
    contract = _minimal_valid_contract()
    contract["skeletons"]["A"]["en"]["guardrail"]["jailbreak"] = ["x", "y", "z"]
    _validate(contract)
