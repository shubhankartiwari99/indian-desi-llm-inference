import pytest

from app.tone.tone_calibration import TONE_PROFILES, calibrate_tone


def test_tone_profiles_is_closed_set():
    assert TONE_PROFILES == {
        "neutral_formal",
        "warm_engaged",
        "empathetic_soft",
        "empathetic_high_intensity",
        "empathetic_crisis_support",
        "grounded_calm",
        "grounded_calm_strong",
        "firm_boundary",
        "firm_boundary_strict",
        "measured_neutral",
        "supportive_low_intensity",
    }


def test_safe_a_low_neutral_formal():
    assert calibrate_tone("A", "LOW", "SAFE") == "neutral_formal"


def test_safe_a_medium_warm_engaged():
    assert calibrate_tone("A", "MEDIUM", "SAFE") == "warm_engaged"


def test_safe_b_low_warm_engaged():
    assert calibrate_tone("B", "LOW", "SAFE") == "warm_engaged"


def test_safe_c_low_empathetic_soft():
    assert calibrate_tone("C", "LOW", "SAFE") == "empathetic_soft"


def test_safe_b_high_warm_engaged():
    assert calibrate_tone("B", "HIGH", "SAFE") == "warm_engaged"


def test_safe_c_critical_empathetic_soft():
    assert calibrate_tone("C", "CRITICAL", "SAFE") == "empathetic_soft"


def test_self_harm_a_low_empathetic_soft():
    assert calibrate_tone("A", "LOW", "SELF_HARM_RISK") == "empathetic_soft"


def test_self_harm_b_medium_empathetic_soft():
    assert calibrate_tone("B", "MEDIUM", "SELF_HARM_RISK") == "empathetic_soft"


def test_self_harm_c_high_empathetic_soft():
    assert calibrate_tone("C", "HIGH", "SELF_HARM_RISK") == "empathetic_high_intensity"


def test_self_harm_a_critical_empathetic_soft():
    assert calibrate_tone("A", "CRITICAL", "SELF_HARM_RISK") == "empathetic_crisis_support"


def test_abuse_grounded_calm():
    assert calibrate_tone("A", "MEDIUM", "ABUSE_HARASSMENT") == "grounded_calm"


def test_extremism_measured_neutral():
    assert calibrate_tone("C", "HIGH", "EXTREMISM") == "firm_boundary_strict"


def test_jailbreak_firm_boundary():
    assert calibrate_tone("A", "MEDIUM", "JAILBREAK_ATTEMPT") == "firm_boundary"


def test_system_probe_measured_neutral():
    assert calibrate_tone("B", "LOW", "SYSTEM_PROBE") == "measured_neutral"


def test_data_extraction_firm_boundary():
    assert calibrate_tone("C", "CRITICAL", "DATA_EXTRACTION_ATTEMPT") == "firm_boundary_strict"


def test_manipulation_low_warm_engaged():
    assert calibrate_tone("A", "LOW", "MANIPULATION_ATTEMPT") == "grounded_calm"


def test_manipulation_medium_warm_engaged():
    assert calibrate_tone("B", "MEDIUM", "MANIPULATION_ATTEMPT") == "grounded_calm"


def test_manipulation_high_grounded_calm():
    assert calibrate_tone("B", "HIGH", "MANIPULATION_ATTEMPT") == "grounded_calm_strong"


def test_manipulation_critical_grounded_calm():
    assert calibrate_tone("C", "CRITICAL", "MANIPULATION_ATTEMPT") == "grounded_calm_strong"


def test_determinism_safe_output_is_stable():
    first = calibrate_tone("A", "LOW", "SAFE")
    second = calibrate_tone("A", "LOW", "SAFE")
    assert first == second == "neutral_formal"


def test_determinism_non_safe_output_is_stable():
    first = calibrate_tone("B", "HIGH", "MANIPULATION_ATTEMPT")
    second = calibrate_tone("B", "HIGH", "MANIPULATION_ATTEMPT")
    assert first == second == "grounded_calm_strong"


def test_unknown_guardrail_category_raises_value_error():
    with pytest.raises(ValueError, match="Unknown guardrail category"):
        calibrate_tone("A", "LOW", "UNKNOWN_CATEGORY")


def test_unknown_severity_raises_value_error():
    with pytest.raises(ValueError, match="Unknown severity"):
        calibrate_tone("A", "UNKNOWN", "SAFE")


def test_unknown_skeleton_raises_value_error():
    with pytest.raises(ValueError, match="Unknown skeleton"):
        calibrate_tone("D", "LOW", "SAFE")
