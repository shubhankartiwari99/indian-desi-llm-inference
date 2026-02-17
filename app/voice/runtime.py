#-*- coding: utf-8 -*-
from dataclasses import dataclass, field
from typing import Optional

from app.voice.state import SessionVoiceState


@dataclass
class EmotionalSignals:
    lang_mode: str
    wants_action: bool
    has_overwhelm: bool
    has_guilt: bool
    has_resignation: bool
    theme: Optional[str]
    family_theme: bool


@dataclass
class EmotionalResolution:
    emotional_skeleton: Optional[str] = None
    emotional_lang: str = "en"
    escalation_state: str = "default"
    latched_theme: Optional[str] = None
    fallback_reason: Optional[str] = None


def resolve_emotional_skeleton(
    intent: str,
    state: SessionVoiceState,
    signals: EmotionalSignals,
) -> EmotionalResolution:
    # This is a simplified version of the logic.
    # In a real system, this would be much more complex.
    if signals.wants_action:
        return EmotionalResolution(emotional_skeleton="D", emotional_lang=signals.lang_mode)
    if signals.has_overwhelm:
        return EmotionalResolution(emotional_skeleton="B", emotional_lang=signals.lang_mode)
    if signals.has_guilt:
        return EmotionalResolution(emotional_skeleton="C", emotional_lang=signals.lang_mode)
    return EmotionalResolution(emotional_skeleton="A", emotional_lang=signals.lang_mode)


def update_session_state(
    state: SessionVoiceState,
    intent: str,
    resolution: EmotionalResolution,
):
    state.emotional_turn_index += 1
    state.last_intent = intent
    state.last_skeleton = resolution.emotional_skeleton
