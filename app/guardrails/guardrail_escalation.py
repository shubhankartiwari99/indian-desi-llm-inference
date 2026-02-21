from __future__ import annotations

from app.guardrails.guardrail_classifier import GuardrailResult


_FORCE_A_CATEGORIES = {
    "ABUSE_HARASSMENT",
    "EXTREMISM",
    "SYSTEM_PROBE",
    "DATA_EXTRACTION_ATTEMPT",
    "JAILBREAK_ATTEMPT",
}

_MANIPULATION_FORCE_A_SEVERITIES = {"HIGH", "CRITICAL"}


def compute_guardrail_escalation(
    guardrail_result: GuardrailResult,
    current_skeleton: str,
) -> str:
    """
    Deterministic, side-effect-free skeleton escalation mapping.

    B15.1 scope:
      - Pure mapping only
      - No runtime state access
      - No mutation
      - No I/O
    """
    risk_category = guardrail_result.risk_category
    severity = guardrail_result.severity

    if risk_category == "SAFE":
        return current_skeleton

    if risk_category == "SELF_HARM_RISK":
        return "C"

    if risk_category in _FORCE_A_CATEGORIES:
        return "A"

    if risk_category == "MANIPULATION_ATTEMPT":
        if severity in _MANIPULATION_FORCE_A_SEVERITIES:
            return "A"
        return current_skeleton

    # Unspecified categories remain unchanged in B15.1.
    return current_skeleton
