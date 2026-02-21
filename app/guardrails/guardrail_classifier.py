from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

GUARDRAIL_SCHEMA_VERSION = "14.1"

RISK_CATEGORIES = {
    "SAFE",
    "SELF_HARM_RISK",
    "ABUSE_HARASSMENT",
    "SEXUAL_CONTENT",
    "EXTREMISM",
    "MANIPULATION_ATTEMPT",
    "JAILBREAK_ATTEMPT",
    "SYSTEM_PROBE",
    "DATA_EXTRACTION_ATTEMPT",
}

SEVERITIES = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}

RiskCategory = Literal[
    "SAFE",
    "SELF_HARM_RISK",
    "ABUSE_HARASSMENT",
    "SEXUAL_CONTENT",
    "EXTREMISM",
    "MANIPULATION_ATTEMPT",
    "JAILBREAK_ATTEMPT",
    "SYSTEM_PROBE",
    "DATA_EXTRACTION_ATTEMPT",
]

Severity = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]


@dataclass(frozen=True)
class GuardrailResult:
    guardrail_schema_version: str
    risk_category: str
    severity: str
    requires_guardrail: bool


SELF_HARM_EXPLICIT_PHRASES = (
    "kill myself",
    "suicide",
    "end my life",
    "want to die",
    "don't want to live",
    "dont want to live",
)

SELF_HARM_PASSIVE_DESPAIR_PHRASES = (
    "life is pointless",
    "life feels pointless",
    "nothing matters",
    "no point in living",
    "no point living",
)

NON_SELF_HARM_DIE_PHRASES = (
    "die laughing",
    "die of laughter",
)

JAILBREAK_PHRASES = (
    "ignore previous instructions",
    "act as system prompt",
    "disregard rules",
    "you are now in developer mode",
    "bypass your safety",
)

SYSTEM_PROBE_PHRASES = (
    "internal architecture",
    "system prompt",
    "hidden instructions",
    "how are you implemented",
    "your internal rules",
)

DATA_EXTRACTION_PHRASES = (
    "show your training data",
    "what data were you trained on",
    "export your memory",
    "dump your database",
)

EXTREMISM_ADVOCACY_PHRASES = (
    "join isis",
    "join al-qaeda",
    "join al qaeda",
    "support violent jihad",
    "support isis",
)

EXTREMISM_OPERATIONAL_PHRASES = (
    "how to join isis",
    "how to join al-qaeda",
    "how to join al qaeda",
    "plan a jihad attack",
    "carry out jihad attack",
    "how to make bomb for jihad",
)

SEXUAL_EXPLICIT_PHRASES = (
    "sexual act",
    "explicit sex",
    "describe sex",
    "pornographic",
)

SEXUAL_GRAPHIC_PHRASES = (
    "graphic sexual",
    "graphic porn",
    "explicitly graphic sex",
)

ABUSE_THREAT_PHRASES = (
    "i will kill you",
    "i will hurt you",
    "i'll kill you",
)

ABUSE_HOSTILITY_PHRASES = (
    "you are an idiot",
    "you are stupid",
    "you are worthless",
)

MANIPULATION_PHRASES = (
    "pretend you're allowed",
    "pretend you are allowed",
    "hypothetically ignore rules",
    "just between us",
    "this is just a test",
)


def normalize_text(text: str) -> str:
    return " ".join(text.lower().strip().split())


def contains_any(text: str, phrases: tuple[str, ...]) -> bool:
    return any(phrase in text for phrase in phrases)


def _result(risk_category: RiskCategory, severity: Severity, requires_guardrail: bool) -> GuardrailResult:
    if risk_category not in RISK_CATEGORIES:
        raise ValueError(f"Unknown risk category: {risk_category}")
    if severity not in SEVERITIES:
        raise ValueError(f"Unknown severity: {severity}")
    return GuardrailResult(
        guardrail_schema_version=GUARDRAIL_SCHEMA_VERSION,
        risk_category=risk_category,
        severity=severity,
        requires_guardrail=requires_guardrail,
    )


def classify_user_input(text: str) -> GuardrailResult:
    normalized = normalize_text(text or "")

    # 1) SELF_HARM_RISK
    explicit_self_harm = contains_any(normalized, SELF_HARM_EXPLICIT_PHRASES)
    benign_die_phrase = contains_any(normalized, NON_SELF_HARM_DIE_PHRASES)
    if explicit_self_harm and not benign_die_phrase:
        return _result("SELF_HARM_RISK", "CRITICAL", True)
    if contains_any(normalized, SELF_HARM_PASSIVE_DESPAIR_PHRASES):
        return _result("SELF_HARM_RISK", "HIGH", True)

    # 2) JAILBREAK_ATTEMPT
    if contains_any(normalized, JAILBREAK_PHRASES):
        return _result("JAILBREAK_ATTEMPT", "HIGH", True)

    # 3) SYSTEM_PROBE
    if contains_any(normalized, SYSTEM_PROBE_PHRASES):
        return _result("SYSTEM_PROBE", "MEDIUM", True)

    # 4) DATA_EXTRACTION_ATTEMPT
    if contains_any(normalized, DATA_EXTRACTION_PHRASES):
        return _result("DATA_EXTRACTION_ATTEMPT", "HIGH", True)

    # 5) EXTREMISM
    if contains_any(normalized, EXTREMISM_OPERATIONAL_PHRASES):
        return _result("EXTREMISM", "CRITICAL", True)
    if contains_any(normalized, EXTREMISM_ADVOCACY_PHRASES):
        return _result("EXTREMISM", "HIGH", True)

    # 6) SEXUAL_CONTENT
    if contains_any(normalized, SEXUAL_GRAPHIC_PHRASES):
        return _result("SEXUAL_CONTENT", "CRITICAL", True)
    if contains_any(normalized, SEXUAL_EXPLICIT_PHRASES):
        return _result("SEXUAL_CONTENT", "HIGH", True)

    # 7) ABUSE_HARASSMENT
    if contains_any(normalized, ABUSE_THREAT_PHRASES):
        return _result("ABUSE_HARASSMENT", "HIGH", True)
    if contains_any(normalized, ABUSE_HOSTILITY_PHRASES):
        return _result("ABUSE_HARASSMENT", "MEDIUM", True)

    # 8) MANIPULATION_ATTEMPT
    if contains_any(normalized, MANIPULATION_PHRASES):
        return _result("MANIPULATION_ATTEMPT", "MEDIUM", True)

    # 9) SAFE default
    return _result("SAFE", "LOW", False)
