import pytest

from app.tone.tone_calibration import TONE_PROFILES, calibrate_tone


@pytest.mark.parametrize(
    "tone_profile",
    [
        "empathetic_high_intensity",
        "empathetic_crisis_support",
        "firm_boundary_strict",
        "grounded_calm_strong",
    ],
)
def test_b17_new_tone_profiles_exist_in_closed_set(tone_profile):
    assert tone_profile in TONE_PROFILES


def test_b17_tone_profiles_closed_set_extended():
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


@pytest.mark.parametrize(
    ("severity", "expected"),
    [
        ("LOW", "empathetic_soft"),
        ("MEDIUM", "empathetic_soft"),
        ("HIGH", "empathetic_high_intensity"),
        ("CRITICAL", "empathetic_crisis_support"),
    ],
)
def test_b17_self_harm_severity_scaling(severity, expected):
    assert calibrate_tone("C", severity, "SELF_HARM_RISK") == expected


def test_b17_self_harm_low_not_equal_high():
    assert calibrate_tone("A", "LOW", "SELF_HARM_RISK") != calibrate_tone(
        "A",
        "HIGH",
        "SELF_HARM_RISK",
    )


def test_b17_self_harm_high_not_equal_critical():
    assert calibrate_tone("B", "HIGH", "SELF_HARM_RISK") != calibrate_tone(
        "B",
        "CRITICAL",
        "SELF_HARM_RISK",
    )


@pytest.mark.parametrize(
    ("severity", "expected"),
    [
        ("MEDIUM", "firm_boundary"),
        ("HIGH", "firm_boundary_strict"),
    ],
)
def test_b17_jailbreak_severity_scaling(severity, expected):
    assert calibrate_tone("A", severity, "JAILBREAK_ATTEMPT") == expected


@pytest.mark.parametrize(
    ("severity", "expected"),
    [
        ("LOW", "grounded_calm"),
        ("HIGH", "grounded_calm_strong"),
    ],
)
def test_b17_abuse_severity_scaling(severity, expected):
    assert calibrate_tone("A", severity, "ABUSE_HARASSMENT") == expected


def test_b17_abuse_low_not_equal_high():
    assert calibrate_tone("C", "LOW", "ABUSE_HARASSMENT") != calibrate_tone(
        "C",
        "HIGH",
        "ABUSE_HARASSMENT",
    )


@pytest.mark.parametrize(
    ("severity", "expected"),
    [
        ("LOW", "measured_neutral"),
        ("HIGH", "firm_boundary_strict"),
    ],
)
def test_b17_extremism_severity_scaling(severity, expected):
    assert calibrate_tone("A", severity, "EXTREMISM") == expected


@pytest.mark.parametrize(
    ("severity", "expected"),
    [
        ("LOW", "firm_boundary"),
        ("HIGH", "firm_boundary_strict"),
    ],
)
def test_b17_data_extraction_severity_scaling(severity, expected):
    assert calibrate_tone("B", severity, "DATA_EXTRACTION_ATTEMPT") == expected


@pytest.mark.parametrize(
    ("severity", "expected"),
    [
        ("MEDIUM", "grounded_calm"),
        ("HIGH", "grounded_calm_strong"),
    ],
)
def test_b17_manipulation_severity_scaling(severity, expected):
    assert calibrate_tone("A", severity, "MANIPULATION_ATTEMPT") == expected


def test_b17_determinism_same_inputs_same_output():
    first = calibrate_tone("C", "HIGH", "SELF_HARM_RISK")
    second = calibrate_tone("C", "HIGH", "SELF_HARM_RISK")
    assert first == second == "empathetic_high_intensity"


def test_b17_unknown_severity_raises_value_error():
    with pytest.raises(ValueError, match="Unknown severity"):
        calibrate_tone("A", "UNKNOWN", "SAFE")


@pytest.mark.parametrize(
    ("skeleton", "severity", "expected"),
    [
        ("A", "LOW", "neutral_formal"),
        ("A", "MEDIUM", "warm_engaged"),
        ("B", "LOW", "warm_engaged"),
        ("C", "LOW", "empathetic_soft"),
    ],
)
def test_b17_safe_mapping_unchanged(skeleton, severity, expected):
    assert calibrate_tone(skeleton, severity, "SAFE") == expected
