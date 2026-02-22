from __future__ import annotations

TONE_PROFILES = {
    "neutral_formal",
    "warm_engaged",
    "empathetic_soft",
    "grounded_calm",
    "firm_boundary",
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
        return "empathetic_soft"

    if guardrail_category == "ABUSE_HARASSMENT":
        return "grounded_calm"

    if guardrail_category == "EXTREMISM":
        return "measured_neutral"

    if guardrail_category == "JAILBREAK_ATTEMPT":
        return "firm_boundary"

    if guardrail_category == "SYSTEM_PROBE":
        return "measured_neutral"

    if guardrail_category == "DATA_EXTRACTION_ATTEMPT":
        return "firm_boundary"

    if guardrail_category == "MANIPULATION_ATTEMPT":
        if severity in {"LOW", "MEDIUM"}:
            return "warm_engaged"
        return "grounded_calm"

    raise ValueError(f"Unknown guardrail category: {guardrail_category}")
