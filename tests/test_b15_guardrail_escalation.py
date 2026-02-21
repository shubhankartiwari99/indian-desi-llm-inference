from app.guardrails.guardrail_classifier import GuardrailResult
from app.guardrails.guardrail_escalation import compute_guardrail_escalation


def _result(category: str, severity: str, requires_guardrail: bool = True) -> GuardrailResult:
    return GuardrailResult(
        guardrail_schema_version="14.1",
        risk_category=category,
        severity=severity,
        requires_guardrail=requires_guardrail,
    )


def test_safe_a_stays_a():
    assert compute_guardrail_escalation(_result("SAFE", "LOW", False), "A") == "A"


def test_safe_c_stays_c():
    assert compute_guardrail_escalation(_result("SAFE", "LOW", False), "C") == "C"


def test_self_harm_a_to_c():
    assert compute_guardrail_escalation(_result("SELF_HARM_RISK", "HIGH"), "A") == "C"


def test_self_harm_b_to_c():
    assert compute_guardrail_escalation(_result("SELF_HARM_RISK", "HIGH"), "B") == "C"


def test_self_harm_c_to_c():
    assert compute_guardrail_escalation(_result("SELF_HARM_RISK", "HIGH"), "C") == "C"


def test_self_harm_d_to_c():
    assert compute_guardrail_escalation(_result("SELF_HARM_RISK", "CRITICAL"), "D") == "C"


def test_abuse_c_to_a():
    assert compute_guardrail_escalation(_result("ABUSE_HARASSMENT", "MEDIUM"), "C") == "A"


def test_abuse_b_to_a():
    assert compute_guardrail_escalation(_result("ABUSE_HARASSMENT", "HIGH"), "B") == "A"


def test_extremism_c_to_a():
    assert compute_guardrail_escalation(_result("EXTREMISM", "HIGH"), "C") == "A"


def test_jailbreak_c_to_a():
    assert compute_guardrail_escalation(_result("JAILBREAK_ATTEMPT", "HIGH"), "C") == "A"


def test_data_extraction_forces_a():
    assert compute_guardrail_escalation(_result("DATA_EXTRACTION_ATTEMPT", "HIGH"), "B") == "A"


def test_system_probe_forces_a():
    assert compute_guardrail_escalation(_result("SYSTEM_PROBE", "MEDIUM"), "C") == "A"


def test_manipulation_low_keeps_current():
    assert compute_guardrail_escalation(_result("MANIPULATION_ATTEMPT", "LOW"), "B") == "B"


def test_manipulation_medium_keeps_current():
    assert compute_guardrail_escalation(_result("MANIPULATION_ATTEMPT", "MEDIUM"), "B") == "B"


def test_manipulation_high_forces_a():
    assert compute_guardrail_escalation(_result("MANIPULATION_ATTEMPT", "HIGH"), "B") == "A"


def test_manipulation_critical_forces_a():
    assert compute_guardrail_escalation(_result("MANIPULATION_ATTEMPT", "CRITICAL"), "C") == "A"


def test_sexual_content_is_unchanged_in_b15_1():
    assert compute_guardrail_escalation(_result("SEXUAL_CONTENT", "HIGH"), "B") == "B"


def test_unknown_category_is_unchanged():
    assert compute_guardrail_escalation(_result("UNKNOWN_CATEGORY", "LOW"), "C") == "C"


def test_unknown_manipulation_severity_is_unchanged():
    assert compute_guardrail_escalation(_result("MANIPULATION_ATTEMPT", "UNKNOWN"), "D") == "D"


def test_safe_does_not_normalize_skeleton():
    assert compute_guardrail_escalation(_result("SAFE", "LOW", False), "custom-skeleton") == "custom-skeleton"


def test_self_harm_overrides_even_with_custom_skeleton():
    assert compute_guardrail_escalation(_result("SELF_HARM_RISK", "CRITICAL"), "custom-skeleton") == "C"


def test_force_a_categories_apply_at_low_severity():
    assert compute_guardrail_escalation(_result("JAILBREAK_ATTEMPT", "LOW"), "C") == "A"


def test_determinism_same_input_same_output_safe():
    result = _result("SAFE", "LOW", False)
    first = compute_guardrail_escalation(result, "A")
    second = compute_guardrail_escalation(result, "A")
    assert first == second == "A"


def test_determinism_same_input_same_output_forced():
    result = _result("MANIPULATION_ATTEMPT", "HIGH")
    first = compute_guardrail_escalation(result, "C")
    second = compute_guardrail_escalation(result, "C")
    assert first == second == "A"


def test_non_mutation_guardrail_result():
    guardrail_result = _result("MANIPULATION_ATTEMPT", "HIGH")
    original = guardrail_result.__dict__.copy()
    _ = compute_guardrail_escalation(guardrail_result, "C")
    assert guardrail_result.__dict__ == original


def test_non_mutation_current_skeleton_variable():
    current_skeleton = "B"
    _ = compute_guardrail_escalation(_result("SAFE", "LOW", False), current_skeleton)
    assert current_skeleton == "B"
