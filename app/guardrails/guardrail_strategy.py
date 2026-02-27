from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.guardrails.guardrail_classifier import GuardrailResult


GUARDRAIL_STRATEGY_VERSION = "14.2"


@dataclass(frozen=True)
class GuardrailAction:
    guardrail_strategy_version: str
    override: bool
    response_text: Optional[str]
    block_inference: bool


SELF_HARM_SUPPORTIVE_MESSAGE = (
    "I'm really sorry you're feeling this way. You don't have to handle this alone. "
    "If you're in immediate danger, please contact local emergency services or a trusted person near you."
)

ABUSE_DE_ESCALATION_MESSAGE = (
    "I want to keep this conversation respectful and safe. I can help if we continue without threats or abuse."
)

SEXUAL_BOUNDARY_MESSAGE = (
    "I can't help with explicit sexual content. I can help with safer, non-explicit information instead."
)

EXTREMISM_NON_ENDORSEMENT_MESSAGE = (
    "I can't support extremist or violent activity. I can help with safe, lawful, and constructive alternatives."
)

MANIPULATION_REFUSAL_MESSAGE = (
    "I can't bypass my safety boundaries, even hypothetically or as a test."
)

SYSTEM_PROBE_GENERIC_MESSAGE = (
    "I can provide high-level information about how I work, but I don't expose internal system details."
)

DATA_EXTRACTION_PRIVACY_MESSAGE = (
    "I can't provide private training records, memory dumps, or internal data exports."
)


def _action(override: bool, response_text: Optional[str], block_inference: bool) -> GuardrailAction:
    return GuardrailAction(
        guardrail_strategy_version=GUARDRAIL_STRATEGY_VERSION,
        override=override,
        response_text=response_text,
        block_inference=block_inference,
    )


def apply_guardrail_strategy(result: GuardrailResult) -> GuardrailAction:
    risk_category = result.risk_category
    severity = result.severity

    if risk_category == "SAFE":
        return _action(False, None, False)

    if risk_category == "SELF_HARM_RISK" and severity in {"HIGH", "CRITICAL"}:
        return _action(True, SELF_HARM_SUPPORTIVE_MESSAGE, False)

    if risk_category == "ABUSE_HARASSMENT" and severity in {"MEDIUM", "HIGH", "CRITICAL"}:
        return _action(True, None, False)

    if risk_category == "SEXUAL_CONTENT" and severity in {"MEDIUM", "HIGH", "CRITICAL"}:
        return _action(True, SEXUAL_BOUNDARY_MESSAGE, False)

    if risk_category == "EXTREMISM" and severity in {"HIGH", "CRITICAL"}:
        return _action(True, EXTREMISM_NON_ENDORSEMENT_MESSAGE, False)

    if risk_category == "MANIPULATION_ATTEMPT" and severity in {"HIGH", "CRITICAL"}:
        return _action(True, MANIPULATION_REFUSAL_MESSAGE, False)

    if risk_category == "JAILBREAK_ATTEMPT":
        return _action(True, None, False)

    if risk_category == "SYSTEM_PROBE" and severity in {"MEDIUM", "HIGH", "CRITICAL"}:
        return _action(True, SYSTEM_PROBE_GENERIC_MESSAGE, False)

    if risk_category == "DATA_EXTRACTION_ATTEMPT" and severity in {"HIGH", "CRITICAL"}:
        return _action(True, DATA_EXTRACTION_PRIVACY_MESSAGE, False)

    return _action(False, None, False)
