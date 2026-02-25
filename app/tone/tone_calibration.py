from __future__ import annotations

TONE_PROFILES = {
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

_SAFE_SKELETON_SEVERITY_TO_TONE = {
    ("A", "LOW"): "neutral_formal",
    ("A", "MEDIUM"): "warm_engaged",
    ("B", "LOW"): "warm_engaged",
    ("B", "MEDIUM"): "warm_engaged",
    ("B", "HIGH"): "warm_engaged",
    ("B", "CRITICAL"): "warm_engaged",
    ("C", "LOW"): "empathetic_soft",
    ("C", "MEDIUM"): "empathetic_soft",
    ("C", "HIGH"): "empathetic_soft",
    ("C", "CRITICAL"): "empathetic_soft",
}

_VALID_SKELETONS = {"A", "B", "C"}
_VALID_SEVERITIES = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
_VALID_GUARDRAIL_CATEGORIES = {
    "SAFE",
    "SELF_HARM_RISK",
    "ABUSE_HARASSMENT",
    "EXTREMISM",
    "JAILBREAK_ATTEMPT",
    "SYSTEM_PROBE",
    "DATA_EXTRACTION_ATTEMPT",
    "MANIPULATION_ATTEMPT",
}

_SELF_HARM_SEVERITY_TO_TONE = {
    "LOW": "empathetic_soft",
    "MEDIUM": "empathetic_soft",
    "HIGH": "empathetic_high_intensity",
    "CRITICAL": "empathetic_crisis_support",
}

_ABUSE_SEVERITY_TO_TONE = {
    "LOW": "grounded_calm",
    "MEDIUM": "grounded_calm",
    "HIGH": "grounded_calm_strong",
    "CRITICAL": "grounded_calm_strong",
}

_EXTREMISM_SEVERITY_TO_TONE = {
    "LOW": "measured_neutral",
    "MEDIUM": "measured_neutral",
    "HIGH": "firm_boundary_strict",
    "CRITICAL": "firm_boundary_strict",
}

_JAILBREAK_SEVERITY_TO_TONE = {
    "LOW": "firm_boundary",
    "MEDIUM": "firm_boundary",
    "HIGH": "firm_boundary_strict",
    "CRITICAL": "firm_boundary_strict",
}

_DATA_EXTRACTION_SEVERITY_TO_TONE = {
    "LOW": "firm_boundary",
    "MEDIUM": "firm_boundary",
    "HIGH": "firm_boundary_strict",
    "CRITICAL": "firm_boundary_strict",
}

_MANIPULATION_SEVERITY_TO_TONE = {
    "LOW": "grounded_calm",
    "MEDIUM": "grounded_calm",
    "HIGH": "grounded_calm_strong",
    "CRITICAL": "grounded_calm_strong",
}


def calibrate_tone(
    skeleton: str,
    severity: str,
    guardrail_category: str,
) -> str:
    if skeleton not in _VALID_SKELETONS:
        raise ValueError(f"Unknown skeleton: {skeleton}")
    if severity not in _VALID_SEVERITIES:
        raise ValueError(f"Unknown severity: {severity}")
    if guardrail_category not in _VALID_GUARDRAIL_CATEGORIES:
        raise ValueError(f"Unknown guardrail category: {guardrail_category}")

    if guardrail_category == "SAFE":
        return _SAFE_SKELETON_SEVERITY_TO_TONE[(skeleton, severity)]

    if guardrail_category == "SELF_HARM_RISK":
        return _SELF_HARM_SEVERITY_TO_TONE[severity]

    if guardrail_category == "ABUSE_HARASSMENT":
        return _ABUSE_SEVERITY_TO_TONE[severity]

    if guardrail_category == "EXTREMISM":
        return _EXTREMISM_SEVERITY_TO_TONE[severity]

    if guardrail_category == "JAILBREAK_ATTEMPT":
        return _JAILBREAK_SEVERITY_TO_TONE[severity]

    if guardrail_category == "SYSTEM_PROBE":
        return "measured_neutral"

    if guardrail_category == "DATA_EXTRACTION_ATTEMPT":
        return _DATA_EXTRACTION_SEVERITY_TO_TONE[severity]

    if guardrail_category == "MANIPULATION_ATTEMPT":
        return _MANIPULATION_SEVERITY_TO_TONE[severity]

    raise ValueError(f"Unknown guardrail category: {guardrail_category}")
