from dataclasses import FrozenInstanceError

import pytest

from app.guardrails.guardrail_classifier import GuardrailResult
from app.guardrails.guardrail_strategy import (
    GUARDRAIL_STRATEGY_VERSION,
    GuardrailAction,
    apply_guardrail_strategy,
)


def _result(category: str, severity: str) -> GuardrailResult:
    return GuardrailResult(
        guardrail_schema_version="14.1",
        risk_category=category,
        severity=severity,
        requires_guardrail=(category != "SAFE"),
    )


def _assert_action(input_result: GuardrailResult, override: bool, has_response: bool) -> GuardrailAction:
    action_1 = apply_guardrail_strategy(input_result)
    action_2 = apply_guardrail_strategy(input_result)

    assert action_1 == action_2
    assert action_1.guardrail_strategy_version == GUARDRAIL_STRATEGY_VERSION
    assert action_1.override is override
    assert action_1.block_inference is False
    if has_response:
        assert action_1.response_text is not None
        assert action_1.response_text.strip() != ""
    else:
        assert action_1.response_text is None
    return action_1


def test_safe_low_no_override():
    _assert_action(_result("SAFE", "LOW"), override=False, has_response=False)


def test_safe_high_still_no_override():
    _assert_action(_result("SAFE", "HIGH"), override=False, has_response=False)


def test_self_harm_high_override():
    _assert_action(_result("SELF_HARM_RISK", "HIGH"), override=True, has_response=False)


def test_self_harm_critical_override():
    _assert_action(_result("SELF_HARM_RISK", "CRITICAL"), override=True, has_response=False)


def test_self_harm_medium_no_override():
    _assert_action(_result("SELF_HARM_RISK", "MEDIUM"), override=False, has_response=False)


def test_abuse_medium_override():
    _assert_action(_result("ABUSE_HARASSMENT", "MEDIUM"), override=True, has_response=False)


def test_abuse_high_override():
    _assert_action(_result("ABUSE_HARASSMENT", "HIGH"), override=True, has_response=False)


def test_abuse_low_no_override():
    _assert_action(_result("ABUSE_HARASSMENT", "LOW"), override=False, has_response=False)


def test_sexual_medium_override():
    _assert_action(_result("SEXUAL_CONTENT", "MEDIUM"), override=True, has_response=True)


def test_sexual_critical_override():
    _assert_action(_result("SEXUAL_CONTENT", "CRITICAL"), override=True, has_response=True)


def test_sexual_low_no_override():
    _assert_action(_result("SEXUAL_CONTENT", "LOW"), override=False, has_response=False)


def test_extremism_high_override():
    _assert_action(_result("EXTREMISM", "HIGH"), override=True, has_response=False)


def test_extremism_critical_override():
    _assert_action(_result("EXTREMISM", "CRITICAL"), override=True, has_response=False)


def test_extremism_medium_no_override():
    _assert_action(_result("EXTREMISM", "MEDIUM"), override=False, has_response=False)


def test_manipulation_high_override():
    _assert_action(_result("MANIPULATION_ATTEMPT", "HIGH"), override=True, has_response=False)


def test_manipulation_medium_no_override():
    _assert_action(_result("MANIPULATION_ATTEMPT", "MEDIUM"), override=False, has_response=False)


def test_jailbreak_high_override():
    _assert_action(_result("JAILBREAK_ATTEMPT", "HIGH"), override=True, has_response=False)


def test_jailbreak_medium_no_override():
    _assert_action(_result("JAILBREAK_ATTEMPT", "MEDIUM"), override=True, has_response=False)


def test_system_probe_medium_override():
    _assert_action(_result("SYSTEM_PROBE", "MEDIUM"), override=True, has_response=False)


def test_system_probe_high_override():
    _assert_action(_result("SYSTEM_PROBE", "HIGH"), override=True, has_response=False)


def test_system_probe_low_no_override():
    _assert_action(_result("SYSTEM_PROBE", "LOW"), override=False, has_response=False)


def test_data_extraction_high_override():
    _assert_action(_result("DATA_EXTRACTION_ATTEMPT", "HIGH"), override=True, has_response=False)


def test_data_extraction_critical_override():
    _assert_action(_result("DATA_EXTRACTION_ATTEMPT", "CRITICAL"), override=True, has_response=False)


def test_data_extraction_medium_no_override():
    _assert_action(_result("DATA_EXTRACTION_ATTEMPT", "MEDIUM"), override=False, has_response=False)


def test_unknown_category_defaults_to_no_override():
    _assert_action(_result("UNKNOWN_CATEGORY", "HIGH"), override=False, has_response=False)


def test_strategy_action_is_frozen():
    action = apply_guardrail_strategy(_result("SAFE", "LOW"))
    with pytest.raises(FrozenInstanceError):
        action.override = True


def test_strategy_result_type():
    action = apply_guardrail_strategy(_result("SAFE", "LOW"))
    assert isinstance(action, GuardrailAction)
